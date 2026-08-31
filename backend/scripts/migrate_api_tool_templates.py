"""Convert legacy API-tool request configuration to template configuration.

Run from ``backend`` with ``uv run python -m scripts.migrate_api_tool_templates``.
The operation is idempotent: only tools without a request template are changed.
"""

import asyncio
import copy
import json
import re

from sqlalchemy import text

from app.core.database import engine


def load_json(value: object, default: object) -> object:
    """Handle JSON values stored by either the MySQL driver or legacy import."""
    if value is None:
        return default
    return json.loads(value) if isinstance(value, str) else value


def set_by_path(target: dict, path: str, value: object) -> None:
    """Set a dot-path value, replacing non-dict intermediate values as needed."""
    parts = path.split(".")
    current = target
    for part in parts[:-1]:
        if not isinstance(current.get(part), dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def migrate_tool(row: dict) -> dict:
    request_template = copy.deepcopy(load_json(row["fixed_params"], {}))
    legacy_url_variables = set(re.findall(r"\{(\w+)\}", row["url"]))
    legacy_params = load_json(row["tool_params"], [])

    for param in legacy_params:
        name = param["name"]
        path = param.get("path", name)
        # The old factory removed a top-level URL parameter from the request.
        if name in legacy_url_variables and path == name:
            continue
        set_by_path(request_template, path, f"{{{{{name}}}}}")

    url = re.sub(r"\{(\w+)\}", r"{{\1}}", row["url"])
    tool_params = [
        {key: value for key, value in param.items() if key != "path"}
        for param in legacy_params
    ]

    extracts = load_json(row["response_extract"], [])
    if len(extracts) > 1:
        raise ValueError(
            f"工具 {row['id']} ({row['name']}) 有多个 response_extract，"
            "无法无损转换为单个响应模板"
        )
    response_template = f"{{{{{extracts[0]['path']}}}}}" if extracts else None

    return {
        "id": row["id"],
        "url": url,
        "request_template": request_template,
        "tool_params": tool_params,
        "response_template": response_template,
    }


async def main() -> None:
    async with engine.begin() as conn:
        columns_result = await conn.execute(text("SHOW COLUMNS FROM api_tools"))
        columns = {row._mapping["Field"] for row in columns_result}
        if "request_template" not in columns:
            await conn.execute(text("ALTER TABLE api_tools ADD COLUMN request_template JSON NULL"))
        if "response_template" not in columns:
            await conn.execute(text("ALTER TABLE api_tools ADD COLUMN response_template TEXT NULL"))

        result = await conn.execute(text("""
            SELECT id, name, url, fixed_params, tool_params, response_extract
            FROM api_tools
            WHERE request_template IS NULL
            ORDER BY id
        """))
        rows = [dict(row._mapping) for row in result]
        migrated = [migrate_tool(row) for row in rows]

        for item in migrated:
            await conn.execute(
                text("""
                    UPDATE api_tools
                    SET url = :url,
                        request_template = :request_template,
                        tool_params = :tool_params,
                        response_template = :response_template
                    WHERE id = :id
                """),
                {
                    **item,
                    "request_template": json.dumps(item["request_template"], ensure_ascii=False),
                    "tool_params": json.dumps(item["tool_params"], ensure_ascii=False),
                },
            )
    print(f"Migrated {len(migrated)} API tool(s).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
