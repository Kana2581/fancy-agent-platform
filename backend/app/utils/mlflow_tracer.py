"""
MLflow tracing facade.

All mlflow imports are lazy and conditional. When MLFLOW_ENABLED=false (the default),
every function here is a no-op and mlflow is never imported, so there is zero memory,
CPU, or network overhead regardless of whether the package is installed.

To enable: set MLFLOW_ENABLED=true and MLFLOW_TRACKING_URI in the environment,
and install the optional dependency group:  uv sync --extra observability
"""
from __future__ import annotations

from typing import Any

_mlflow: Any = None  # None = uninitialised; False = import failed


def _get_mlflow() -> Any:
    global _mlflow
    if _mlflow is None:
        try:
            import mlflow as _m
            _mlflow = _m
        except ImportError:
            _mlflow = False
    return _mlflow if _mlflow is not False else None


def setup_mlflow(tracking_uri: str, experiment_name: str) -> bool:
    """Initialise MLflow autolog at application startup. Returns True if active."""
    m = _get_mlflow()
    if m is None:
        return False
    if tracking_uri:
        m.set_tracking_uri(tracking_uri)
    m.set_experiment(experiment_name)
    m.config.enable_async_logging()
    m.langchain.autolog()
    return True


def chat_tracing_context(session_id: str, user_id: str) -> Any:
    """Return a context manager that tags all MLflow traces with session_id and user_id.

    Uses mlflow.tracing.context() — the correct API for autolog apps.
    Falls back to a no-op if mlflow is not installed or the API is unavailable.
    """
    from contextlib import nullcontext
    m = _get_mlflow()
    if m is None:
        return nullcontext()
    try:
        return m.tracing.context(session_id=session_id, user=user_id)
    except (AttributeError, TypeError):
        return nullcontext()
