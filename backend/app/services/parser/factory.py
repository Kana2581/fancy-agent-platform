from pathlib import Path

from app.services.parser.docx_parser import DocxParser
from app.services.parser.pdf_parser import PDFParser
from app.services.parser.text_parser import TextParser


class FileParserFactory:

    @staticmethod
    def get_parser(file_ext: str):
        if not file_ext:
            raise ValueError("文件后缀不能为空")

        # 统一格式：去空格 + 小写
        file_ext = file_ext.strip().lower()

        # 支持的纯文本类型（含代码文件）
        text_extensions = {
            ".txt",
            ".md",
            ".markdown",
            ".log",
            ".csv",
            ".ini",
            ".conf",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".xml",
            ".html",
            ".htm",
            ".css",
            ".sql",
            ".sh",
            ".bash",
            ".zsh",
            # 编程语言
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
            ".cs",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".r",
            ".m",
            ".vue",
            ".svelte",
            ".lua",
            ".pl",
            ".ex",
            ".exs",
            ".dart",
            ".tf",
            ".env",
        }

        if file_ext in text_extensions:
            return TextParser()

        # 后续可扩展
        if file_ext == ".pdf":
            return PDFParser()

        if file_ext == ".docx":
            return DocxParser()

        return None