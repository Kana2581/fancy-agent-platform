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
    m.langchain.autolog()
    return True


def start_chat_run(run_name: str, params: dict) -> Any:
    """Open an MLflow run for one chat request. Returns the run object or None."""
    m = _get_mlflow()
    if m is None:
        return None
    run = m.start_run(run_name=run_name)
    m.log_params(params)
    return run


def end_chat_run(run: Any, metrics: dict | None = None) -> None:
    """Close a chat run and optionally log final metrics."""
    m = _get_mlflow()
    if m is None or run is None:
        return
    if metrics:
        m.log_metrics(metrics)
    m.end_run()
