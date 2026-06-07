from typing import Union, List, Dict, Any


def clean_and_truncate_content(content: Union[str, List, Dict], max_length: int = 20000) -> Union[str, List, Dict]:
    """
    通用方法：处理搜索工具返回的content
    - 如果是str：去除无用信息并截断
    - 如果是list/dict：递归遍历，截断过长的字符串

    Args:
        content: 可能是str、list或dict
        max_length: 字符串最大长度，默认4000

    Returns:
        处理后的content
    """

    def clean_html_text(text: str) -> str:
        """简单清理HTML和多余空白"""
        import re
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 去除特殊字符
        text = re.sub(r'[\r\n\t]', ' ', text)
        return text.strip()

    def truncate_string(text: str, max_len: int = 4000) -> str:
        """截断字符串"""
        text = clean_html_text(text)
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    def process_value(value: Any) -> Any:
        """递归处理各种类型的值"""
        if isinstance(value, str):
            # 字符串类型：清理并截断
            if len(value) > max_length:
                return truncate_string(value, max_length)
            return clean_html_text(value)

        elif isinstance(value, list):
            # 列表类型：递归处理每个元素
            return [process_value(item) for item in value]

        elif isinstance(value, dict):
            # 字典类型：递归处理每个value
            return {k: process_value(v) for k, v in value.items()}

        else:
            # 其他类型（数字、布尔等）：直接返回
            return value

    # 主处理逻辑
    return process_value(content)