"""HTTP client for the session sandbox runtime."""
from typing import Any, Optional

import httpx

from app.core.config import settings


class SandboxUnavailableError(RuntimeError):
    pass


class SandboxClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url if base_url is not None else settings.SANDBOX_EXEC_URL).rstrip("/")

    async def request(self, endpoint: str, payload: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
        if not self.base_url:
            raise SandboxUnavailableError("sandbox 服务未配置")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"{self.base_url}{endpoint}", json=payload)
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SandboxUnavailableError(f"sandbox 服务不可用: {exc}") from exc
        if not isinstance(result, dict):
            raise SandboxUnavailableError("sandbox 返回了无效响应")
        return result

    async def execute(
        self,
        *,
        runtime: str,
        rel_dir: str,
        code: Optional[str] = None,
        command: Optional[str] = None,
        script_path: Optional[str] = None,
        timeout: int = 30,
        cwd: Optional[str] = None,
    ) -> dict[str, Any]:
        return await self.request("/exec", {
            "runtime": runtime,
            "rel_dir": rel_dir,
            "code": code,
            "command": command,
            "script_path": script_path,
            "timeout": timeout,
            "cwd": cwd,
            "max_file_bytes": settings.WORKSPACE_MAX_FILE_SIZE_MB * 1024 * 1024,
            "max_session_bytes": settings.WORKSPACE_MAX_SESSION_MB * 1024 * 1024,
            "max_user_bytes": settings.WORKSPACE_MAX_USER_GB * 1024 * 1024 * 1024,
            "max_files": settings.WORKSPACE_MAX_FILES_PER_DIR,
        }, timeout=timeout + 15)

    async def workspace(self, operation: str, rel_dir: str, **payload: Any) -> dict[str, Any]:
        return await self.request(f"/workspace/{operation}", {"rel_dir": rel_dir, **payload})


def sandbox_client() -> SandboxClient:
    return SandboxClient()
