from datetime import datetime

from app.models.scheduled_task import ScheduledTask
from app.services.scheduled_task_service import (
    compute_next_run,
    get_due_task_window,
    get_latest_scheduled_run_at,
    get_next_scheduled_run_at,
)


def build_task(**overrides) -> ScheduledTask:
    defaults = {
        "id": 1,
        "user_id": 1,
        "agent_id": 1,
        "name": "daily-report",
        "instruction": "run",
        "schedule_type": "daily",
        "schedule_time": "09:00",
        "schedule_day": None,
        "timezone": "Asia/Shanghai",
        "is_enabled": True,
        "created_at": datetime(2026, 5, 30, 0, 0, 0),
        "updated_at": datetime(2026, 5, 30, 0, 0, 0),
        "last_run_at": None,
        "next_run_at": None,
    }
    defaults.update(overrides)
    return ScheduledTask(**defaults)


def test_daily_schedule_previous_and_next_run_are_utc_naive():
    reference = datetime(2026, 6, 1, 1, 30, 0)

    latest = get_latest_scheduled_run_at("daily", "09:00", None, "Asia/Shanghai", reference)
    next_run = get_next_scheduled_run_at("daily", "09:00", None, "Asia/Shanghai", reference)

    assert latest == datetime(2026, 6, 1, 1, 0, 0)
    assert next_run == datetime(2026, 6, 2, 1, 0, 0)


def test_weekly_schedule_handles_python_weekday_convention():
    reference = datetime(2026, 6, 3, 4, 0, 0)  # Wednesday 12:00 Asia/Shanghai

    latest = get_latest_scheduled_run_at("weekly", "09:00", 0, "Asia/Shanghai", reference)
    next_run = get_next_scheduled_run_at("weekly", "09:00", 0, "Asia/Shanghai", reference)

    assert latest == datetime(2026, 6, 1, 1, 0, 0)
    assert next_run == datetime(2026, 6, 8, 1, 0, 0)


def test_monthly_schedule_skips_invalid_month_days():
    reference = datetime(2026, 4, 30, 15, 0, 0)

    latest = get_latest_scheduled_run_at("monthly", "09:00", 31, "Asia/Shanghai", reference)
    next_run = get_next_scheduled_run_at("monthly", "09:00", 31, "Asia/Shanghai", reference)

    assert latest == datetime(2026, 3, 31, 1, 0, 0)
    assert next_run == datetime(2026, 5, 31, 1, 0, 0)


def test_due_window_uses_latest_missed_point_without_full_catch_up():
    task = build_task(
        last_run_at=datetime(2026, 5, 29, 1, 0, 0),
        updated_at=datetime(2026, 5, 29, 1, 0, 5),
    )

    due_window = get_due_task_window(task, datetime(2026, 6, 1, 3, 0, 0))

    assert due_window is not None
    assert due_window.scheduled_for == datetime(2026, 6, 1, 1, 0, 0)
    assert due_window.next_run_at == datetime(2026, 6, 2, 1, 0, 0)


def test_due_window_skips_runs_before_task_activation_boundary():
    task = build_task(
        created_at=datetime(2026, 6, 1, 1, 30, 0),
        updated_at=datetime(2026, 6, 1, 1, 30, 0),
    )

    due_window = get_due_task_window(task, datetime(2026, 6, 1, 1, 35, 0))

    assert due_window is None


def test_compute_next_run_reuses_rule_engine_from_reference_time():
    next_run = compute_next_run(
        "daily",
        "09:00",
        None,
        "Asia/Shanghai",
        reference_utc=datetime(2026, 6, 1, 1, 0, 0),
    )

    assert next_run == datetime(2026, 6, 2, 1, 0, 0)
