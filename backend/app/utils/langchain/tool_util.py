from langchain_core.tools import BaseTool
from pydantic import BaseModel
from typing import List, Dict, Any, Union

def parse_tools(tools: List[BaseTool]) -> List[Dict[str, Any]]:
    """
    解析 BaseTool 对象，返回每个工具的 name、description 和参数 schema
    """
    result = []
    for tool in tools:
        tool_info: Dict[str, Any] = {
            "name": getattr(tool, "name", None),
            "description": getattr(tool, "description", None),
        }

        # args_schema 可能是 BaseModel 类，也可能是 None
        args_schema = getattr(tool, "args_schema", None)
        if args_schema is None:
            tool_info["parameters"] = None
        elif isinstance(args_schema, type) and issubclass(args_schema, BaseModel):
            # 将 BaseModel 的字段解析成字典
            tool_info["parameters"] = {
                field: str(field_info.type_)
                for field, field_info in args_schema.model_fields.items()
            }
        elif isinstance(args_schema, dict):
            # 如果是 JSON schema dict
            tool_info["parameters"] = args_schema
        else:
            tool_info["parameters"] = str(args_schema)

        result.append(tool_info)
    return result
