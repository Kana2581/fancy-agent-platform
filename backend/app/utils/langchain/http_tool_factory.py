"""
HTTP API Tool Factory
将数据库中存储的 ApiTool 配置构建为 LangChain StructuredTool。
支持：
  - dot-path 请求体嵌套（tool_params[i].path = "filter.date_range.start"）
  - URL 路径参数（url 里写 {var}）
  - fixed_params 深度合并
  - 响应 dot-path / [*] 列表提取
  - 响应截断防爆上下文
"""

import json
import re
from typing import Any, Optional


def _sanitize_tool_name(name: str, fallback: str = "api_tool") -> str:
    """Sanitize tool name to meet OpenAI requirements: ^[a-zA-Z0-9_-]{1,64}$"""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized[:64] if sanitized else fallback

import httpx
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import StructuredTool


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _build_nested_dict(flat: dict[str, Any]) -> dict:
    """
    {"user.address.city": "北京", "page": 1}
    → {"user": {"address": {"city": "北京"}}, "page": 1}
    """
    result: dict = {}
    for dotpath, value in flat.items():
        keys = dotpath.split(".")
        node = result
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """override 优先；两者都是 dict 时递归合并。"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _get_by_path(data: Any, path: str) -> Any:
    """
    支持：
      "data.total"        → 普通层级
      "data.items[0]"     → 列表索引
      "data.items[*]"     → 返回整个列表
    """
    # 按点分割，但忽略方括号内的点
    parts = re.split(r'\.(?![^\[]*\])', path)
    for part in parts:
        if data is None:
            return None
        m = re.match(r'^(\w+)\[(\d+|\*)\]$', part)
        if m:
            key, idx = m.group(1), m.group(2)
            data = data.get(key) if isinstance(data, dict) else None
            if data is None:
                return None
            if idx == '*':
                return data  # 返回整个列表
            data = data[int(idx)] if isinstance(data, list) and int(idx) < len(data) else None
        else:
            data = data.get(part) if isinstance(data, dict) else None
    return data


def _extract_response(raw: Any, extracts: list) -> Any:
    """按 response_extract 配置提取字段；为空则返回原始响应。"""
    if not extracts:
        return raw
    result = {}
    for ex in extracts:
        result[ex["alias"]] = _get_by_path(raw, ex["path"])
    return result


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------

def build_tool_from_config(config: dict) -> StructuredTool:
    """
    config 为 ApiTool ORM 对象序列化后的 dict（或直接传 dict）。
    字段说明见 ApiTool 模型。
    """
    name: str = _sanitize_tool_name(config["name"])
    description: str = config.get("description") or config["name"]
    url: str = config["url"]
    method: str = (config.get("method") or "GET").upper()
    headers: dict = config.get("headers") or {}
    param_location: str = config.get("param_location") or "query"
    fixed_params: dict = config.get("fixed_params") or {}
    tool_params: list = config.get("tool_params") or []
    response_extract: list = config.get("response_extract") or []
    response_max_chars: int = config.get("response_max_chars") or 2000

    # 1. 构建动态 Pydantic Schema
    type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
    fields: dict = {}
    for p in tool_params:
        py_type = type_map.get(p["type"], str)
        if not p.get("required", True):
            fields[p["name"]] = (
                Optional[py_type],
                Field(default=p.get("default"), description=p.get("description", "")),
            )
        else:
            fields[p["name"]] = (
                py_type,
                Field(description=p.get("description", "")),
            )

    DynamicSchema = create_model(f"{name}_args", **fields) if fields else None

    # 2. 执行闭包（捕获所有配置避免晚绑定问题）
    def make_run_fn(
        _url, _method, _headers, _param_location,
        _fixed_params, _tool_params, _response_extract, _response_max_chars,
    ):
        def run_fn(**kwargs) -> str:
            # 2-a. 将 tool_params 的值按 path 构建嵌套 dict
            path_value_map: dict = {}
            for p_cfg in _tool_params:
                val = kwargs.get(p_cfg["name"])
                if val is not None:
                    path_value_map[p_cfg["path"]] = val

            tool_nested = _build_nested_dict(path_value_map)

            # 2-b. 与 fixed_params 深度合并（tool 参数优先）
            merged = _deep_merge(_fixed_params, tool_nested)

            # 2-c. 替换 URL 路径变量 {var}
            request_url = _url
            for var in re.findall(r'\{(\w+)\}', _url):
                val = merged.pop(var, kwargs.get(var, ""))
                request_url = request_url.replace(f"{{{var}}}", str(val))

            # 2-d. 发送 HTTP 请求
            loc = _param_location
            with httpx.Client(timeout=30) as client:
                if loc in ("query", "path_and_query"):
                    resp = client.request(_method, request_url, params=merged, headers=_headers)
                elif loc in ("body", "path_and_body"):
                    resp = client.request(_method, request_url, json=merged, headers=_headers)
                else:
                    resp = client.request(_method, request_url, params=merged, headers=_headers)

            # 2-e. 提取响应 + 截断
            try:
                raw = resp.json()
            except Exception:
                return resp.text[:_response_max_chars]

            extracted = _extract_response(raw, _response_extract)
            result_str = json.dumps(extracted, ensure_ascii=False)
            return result_str[:_response_max_chars]

        return run_fn

    run_fn = make_run_fn(
        url, method, headers, param_location,
        fixed_params, tool_params, response_extract, response_max_chars,
    )

    return StructuredTool.from_function(
        func=run_fn,
        name=name,
        description=description,
        args_schema=DynamicSchema,
    )
