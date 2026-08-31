"""Build LangChain HTTP tools from ``{{variable}}`` request templates."""

import json
import re
from typing import Any, Optional
from urllib.parse import quote

import httpx
from langchain_core.tools import StructuredTool
from pydantic import Field, create_model

VARIABLE_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
FULL_VARIABLE_RE = re.compile(r"^{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}$")
PATH_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")


def _sanitize_tool_name(name: str, fallback: str = "api_tool") -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:64] if sanitized else fallback


def _walk_template(value: Any) -> list[str]:
    if isinstance(value, str):
        return VARIABLE_RE.findall(value)
    if isinstance(value, dict):
        names: list[str] = []
        for key, item in value.items():
            names.extend(_walk_template(key))
            names.extend(_walk_template(item))
        return names
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_walk_template(item))
        return names
    return []


def extract_template_variables(*templates: Any) -> list[str]:
    """Extract unique variables in first-seen order."""
    result: list[str] = []
    seen: set[str] = set()
    for template in templates:
        for name in _walk_template(template):
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


def _validate_request_placeholders(*templates: Any) -> None:
    for template in templates:
        if isinstance(template, str):
            for match in PATH_RE.finditer(template):
                if not VARIABLE_RE.fullmatch(match.group(0)):
                    raise ValueError(f"非法模板变量: {match.group(1).strip()}")
        elif isinstance(template, dict):
            _validate_request_placeholders(*template.keys(), *template.values())
        elif isinstance(template, list):
            _validate_request_placeholders(*template)


def _coerce_value(value: Any, value_type: str) -> Any:
    if value is None:
        return None
    if value_type == "string":
        return str(value)
    if value_type == "integer":
        if isinstance(value, bool):
            raise ValueError("boolean cannot be used as an integer")
        return int(value)
    if value_type == "number":
        if isinstance(value, bool):
            raise ValueError("boolean cannot be used as a number")
        return float(value)
    if value_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            return value.strip().lower() == "true"
        raise ValueError(f"{value!r} is not a boolean")
    return value


def _render_template(value: Any, variables: dict[str, Any]) -> Any:
    """Render nested templates while preserving types for full placeholders."""
    if isinstance(value, str):
        full_match = FULL_VARIABLE_RE.fullmatch(value)
        if full_match:
            return variables.get(full_match.group(1))

        def replace(match: re.Match[str]) -> str:
            item = variables.get(match.group(1))
            if item is None:
                return ""
            if isinstance(item, (dict, list)):
                return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            return str(item)

        return PATH_RE.sub(replace, value)
    if isinstance(value, dict):
        return {
            _render_template(key, variables): _render_template(item, variables)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_render_template(item, variables) for item in value]
    return value


def _get_by_path(data: Any, path: str) -> Any:
    """Resolve dot paths, numeric indexes, and ``[*]`` list selectors."""
    parts = re.split(r"\.(?![^\[]*\])", path.strip())
    for part in parts:
        if data is None:
            return None
        match = re.match(r"^(\w+)\[(\d+|\*)\]$", part)
        if match:
            key, index = match.groups()
            data = data.get(key) if isinstance(data, dict) else None
            if data is None:
                return None
            if index == "*":
                return data
            data = data[int(index)] if isinstance(data, list) and int(index) < len(data) else None
        else:
            data = data.get(part) if isinstance(data, dict) else None
    return data


def _render_response_template(template: str, raw: Any) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value = _get_by_path(raw, path)
        if value is None:
            return f"<missing:{path}>"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return PATH_RE.sub(replace, template)


def _build_schema(name: str, params: list[dict[str, Any]], template_names: list[str]):
    type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
    configs = {item["name"]: item for item in params}
    missing = [item for item in template_names if item not in configs]
    if missing:
        raise ValueError(f"模板变量未声明: {', '.join(missing)}")

    fields: dict[str, Any] = {}
    for variable_name in template_names:
        config = configs[variable_name]
        py_type = type_map.get(config.get("type", "string"), str)
        description = config.get("description", "")
        if config.get("required", True):
            fields[variable_name] = (py_type, Field(description=description))
        else:
            fields[variable_name] = (
                Optional[py_type],
                Field(default=config.get("default"), description=description),
            )
    return create_model(f"{name}_args", **fields) if fields else None


def build_tool_from_config(config: dict) -> StructuredTool:
    name = _sanitize_tool_name(config["name"])
    description = config.get("description") or config["name"]
    url = config["url"]
    method = (config.get("method") or "GET").upper()
    headers = config.get("headers") or {}
    param_location = config.get("param_location") or "query"
    request_template = config.get("request_template")
    tool_params = config.get("tool_params") or []
    response_template = config.get("response_template")
    response_max_chars = config.get("response_max_chars") or 2000

    _validate_request_placeholders(url, headers, request_template)
    template_names = extract_template_variables(url, headers, request_template)
    DynamicSchema = _build_schema(name, tool_params, template_names)
    configs = {item["name"]: item for item in tool_params}

    def run_fn(**kwargs) -> str:
        values: dict[str, Any] = {}
        for variable_name in template_names:
            config_item = configs[variable_name]
            raw_value = kwargs.get(variable_name, config_item.get("default"))
            if raw_value is None and config_item.get("required", True):
                raise ValueError(f"缺少必填参数: {variable_name}")
            values[variable_name] = _coerce_value(raw_value, config_item.get("type", "string"))

        request_url = url
        for variable_name, value in values.items():
            encoded = quote(str(value), safe="") if value is not None else ""
            request_url = re.sub(
                rf"{{{{\s*{re.escape(variable_name)}\s*}}}}", encoded, request_url
            )

        rendered_headers = {
            str(_render_template(key, values)): str(_render_template(value, values))
            for key, value in headers.items()
        }
        rendered_request = _render_template(request_template, values)

        with httpx.Client(timeout=30) as client:
            if param_location in ("query", "path_and_query"):
                response = client.request(
                    method, request_url, params=rendered_request or {}, headers=rendered_headers
                )
            else:
                response = client.request(
                    method, request_url, json=rendered_request, headers=rendered_headers
                )
            response.raise_for_status()

        try:
            raw = response.json()
        except Exception:
            return response.text[:response_max_chars]

        result = (
            _render_response_template(response_template, raw)
            if response_template
            else json.dumps(raw, ensure_ascii=False)
        )
        return result[:response_max_chars]

    return StructuredTool.from_function(
        func=run_fn,
        name=name,
        description=description,
        args_schema=DynamicSchema,
    )
