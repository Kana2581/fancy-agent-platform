from fastapi import UploadFile
from pathlib import Path

CODE_EXTENSIONS = {
    ".py", ".cpp", ".c", ".h", ".hpp",
    ".java", ".js", ".ts",
    ".go", ".rs",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".html", ".css",
    ".xml", ".json", ".yaml", ".yml",
    ".sql",
    ".md",
}

async def read_code_for_llm(upload_file: UploadFile) -> dict:
    data = await upload_file.read()

    filename = upload_file.filename or "unknown"
    suffix = Path(filename).suffix.lower()

    # 1️⃣ 必须是代码文件
    if suffix not in CODE_EXTENSIONS:
        return {
            "ok": False,
            "reason": "not_code_file",
            "filename": filename,
        }

    # 2️⃣ 解码（LLM 不在乎非法字符，直接 ignore）
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return {
            "ok": False,
            "reason": "decode_failed",
            "filename": filename,
        }

    # 3️⃣ 空文件 / 近似二进制保护
    if not text.strip():
        return {
            "ok": False,
            "reason": "empty_or_binary",
            "filename": filename,
        }

    return {
        "ok": True,
        "filename": filename,
        "language": suffix.lstrip("."),  # py / cpp / js
        "content": text,
        "line_count": text.count("\n") + 1,
        "char_count": len(text),
    }
