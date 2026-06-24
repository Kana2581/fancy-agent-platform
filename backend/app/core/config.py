import os
from datetime import timedelta

from dotenv import load_dotenv
from typing import List

# 加载 .env 文件
load_dotenv(".env")


# 邮箱服务商预设：管理员只需设 EMAIL_PROVIDER + 凭据，主机/端口/安全模式自动带出。
# smtp_security: "ssl"(隐式 SSL, 通常 465) 或 "starttls"(通常 587)。
# imap_id: 163/QQ 收信前必须发送 IMAP ID 命令，Gmail/Outlook 不需要。
EMAIL_PROVIDER_PRESETS = {
    "gmail":   {"imap_host": "imap.gmail.com",        "imap_port": 993, "smtp_host": "smtp.gmail.com",     "smtp_port": 587, "smtp_security": "starttls", "imap_id": False},
    "163":     {"imap_host": "imap.163.com",          "imap_port": 993, "smtp_host": "smtp.163.com",       "smtp_port": 465, "smtp_security": "ssl",      "imap_id": True},
    "qq":      {"imap_host": "imap.qq.com",           "imap_port": 993, "smtp_host": "smtp.qq.com",        "smtp_port": 465, "smtp_security": "ssl",      "imap_id": True},
    "outlook": {"imap_host": "outlook.office365.com", "imap_port": 993, "smtp_host": "smtp.office365.com", "smtp_port": 587, "smtp_security": "starttls", "imap_id": False},
}


class Settings:
    def __init__(self):
        # 从环境变量读取，设置默认值
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "sqlite+aiosqlite:///./fancy_agent.db"
        )
        self.OSS_URL = os.getenv(
            "OSS_URL",
            "http://localhost:8000"
        )
        self.ALGORITHM = "HS256"
        self.SECRET_KEY = os.getenv("SECRET_KEY","super-secret-key")
        # 敏感字段（API Key）落库加密密钥，可选；留空则复用 SECRET_KEY 派生
        self.APP_ENCRYPTION_KEY = os.getenv("APP_ENCRYPTION_KEY", "")
        self.ACCESS_TOKEN_EXPIRE = timedelta( days=30
                                              )
        self.REFRESH_TOKEN_EXPIRE = timedelta(days=365)

        self.REFRESH_COOKIE_NAME = "refresh_token"

        # 邮件服务配置
        self.EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.EMAIL_ADDRESS: str = os.getenv("EMAIL_ADDRESS", "")
        self.EMAIL_USERNAME: str = os.getenv("EMAIL_USERNAME", "")
        self.EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
        # 服务商预设：env 显式值 > 预设值 > 推断/硬编码兜底
        # 默认留空（不套预设），以保证已有"显式主机+端口"配置完全向后兼容。
        self.EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "").lower().strip()
        _email_preset = EMAIL_PROVIDER_PRESETS.get(self.EMAIL_PROVIDER, {})
        self.EMAIL_IMAP_HOST: str = os.getenv("EMAIL_IMAP_HOST") or _email_preset.get("imap_host", "imap.gmail.com")
        self.EMAIL_IMAP_PORT: int = int(os.getenv("EMAIL_IMAP_PORT") or _email_preset.get("imap_port", 993))
        self.EMAIL_SMTP_HOST: str = os.getenv("EMAIL_SMTP_HOST") or _email_preset.get("smtp_host", "smtp.gmail.com")
        self.EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT") or _email_preset.get("smtp_port", 587))
        # SMTP 安全模式：显式 env > 预设 > 按端口推断(465=ssl, 其余=starttls)
        _smtp_security = (
            os.getenv("EMAIL_SMTP_SECURITY")
            or _email_preset.get("smtp_security")
            or ("ssl" if self.EMAIL_SMTP_PORT == 465 else "starttls")
        )
        self.EMAIL_SMTP_SECURITY: str = _smtp_security.lower().strip()
        # IMAP ID 命令（163/QQ 收信必需）：显式 env > 预设 > 按主机名推断
        _imap_id_env = os.getenv("EMAIL_IMAP_ID")
        if _imap_id_env is not None:
            self.EMAIL_IMAP_ID: bool = _imap_id_env.lower() == "true"
        elif "imap_id" in _email_preset:
            self.EMAIL_IMAP_ID = bool(_email_preset["imap_id"])
        else:
            _host = self.EMAIL_IMAP_HOST.lower()
            self.EMAIL_IMAP_ID = "163" in _host or "qq" in _host
        self.EMAIL_CHECK_INTERVAL: int = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))
        # 定时任务检查间隔（秒），同时决定任务扫描窗口大小
        self.SCHEDULED_TASK_CHECK_INTERVAL: int = int(os.getenv("SCHEDULED_TASK_CHECK_INTERVAL", "60"))

        # Agent 执行限制
        self.AGENT_TOOL_CALL_LIMIT: int = int(os.getenv("AGENT_TOOL_CALL_LIMIT", "15"))
        self.AGENT_MODEL_CALL_LIMIT: int = int(os.getenv("AGENT_MODEL_CALL_LIMIT", "15"))

        # 内置工具配置
        self.SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "duckduckgo")  # "tavily" | "duckduckgo"
        self.TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
        self.WEB_FETCH_MAX_CHARS: int = int(os.getenv("WEB_FETCH_MAX_CHARS", "5000"))
        self.WEB_SEARCH_MAX_RESULTS: int = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))

        # 代码执行沙箱服务地址。留空 = 本地进程内子进程沙箱（开发）；
        # 生产/Docker 设为常驻 sandbox 容器内网地址，如 http://sandbox:9000
        self.SANDBOX_EXEC_URL: str = os.getenv("SANDBOX_EXEC_URL", "")

        # 上传文件根目录（图片、附件、生图产物都落在这里）
        self.UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/data/uploads")

        # Session 工作区（agent 可写文件）
        self.WORKSPACE_DIR: str = os.getenv("WORKSPACE_DIR", "/data/workspaces")
        self.WORKSPACE_MAX_FILE_SIZE_MB: int = int(os.getenv("WORKSPACE_MAX_FILE_SIZE_MB", "50"))
        self.WORKSPACE_MAX_SESSION_MB: int = int(os.getenv("WORKSPACE_MAX_SESSION_MB", "500"))
        self.WORKSPACE_MAX_USER_GB: int = int(os.getenv("WORKSPACE_MAX_USER_GB", "5"))
        self.WORKSPACE_MAX_FILES_PER_DIR: int = int(os.getenv("WORKSPACE_MAX_FILES_PER_DIR", "1000"))
        self.WORKSPACE_READ_MAX_CHARS: int = int(os.getenv("WORKSPACE_READ_MAX_CHARS", "20000"))
        # 打包下载总大小上限（MB），防止小服务器被一次性压垮
        self.WORKSPACE_ZIP_MAX_MB: int = int(os.getenv("WORKSPACE_ZIP_MAX_MB", "200"))

        # 应用配置
        self.app_name: str = "my_fastapi_app"
        self.app_host: str = "0.0.0.0"
        self.app_port: int = 8000
        self.app_env: str = "development"
        
        # 日志配置
        self.log_dir: str = "logs"
        self.log_level: str = "INFO"
        self.log_json_format: bool = False
        self.log_console_output: bool = True
        self.log_request_body: bool = True
        self.log_response_body: bool = False
        
        # 日志轮转
        self.log_retention_days: int = 30
        self.log_error_retention_days: int = 90
        
        # 跳过日志的路径
        self.log_skip_paths: List[str] = ["/health", "/metrics", "/docs", "/openapi.json"]

        # MLflow 可观测性（默认关闭；启用需先 uv sync --extra observability）
        self.MLFLOW_ENABLED: bool = os.getenv("MLFLOW_ENABLED", "false").lower() == "true"
        self.MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "")
        self.MLFLOW_EXPERIMENT_NAME: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "fancy_agent")

        # CORS 配置（逗号分隔）
        cors_origins_raw = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
        )
        self.cors_origins: List[str] = [x.strip() for x in cors_origins_raw.split(",") if x.strip()]
    

# 实例化配置
settings = Settings()
