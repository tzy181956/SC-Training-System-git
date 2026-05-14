from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any


def test_startup_does_not_run_in_process_backup_loop_by_default(monkeypatch: Any) -> None:
    from app import main

    monkeypatch.setattr(main.settings, "enable_in_process_backup_loop", False)
    monkeypatch.setattr(main, "_apply_startup_schema_strategy", lambda: None)
    monkeypatch.setattr(main, "_close_due_sessions_on_startup", lambda: None)
    monkeypatch.setattr(main, "_daily_backup_task", None)

    def fail_if_called() -> None:
        raise AssertionError("ensure_daily_backup should not run when in-process loop is disabled")

    monkeypatch.setattr(main.backup_service, "ensure_daily_backup", fail_if_called)

    main.startup_sync_schema()

    assert main._daily_backup_task is None


def test_startup_runs_backup_loop_only_when_enabled(monkeypatch: Any) -> None:
    from app import main

    calls = {"ensure_daily_backup": 0, "loop_started": 0}

    def fake_ensure_daily_backup() -> SimpleNamespace:
        calls["ensure_daily_backup"] += 1
        return SimpleNamespace(created=False, backup_path=None)

    async def fake_daily_backup_loop() -> None:
        calls["loop_started"] += 1
        await asyncio.Event().wait()

    async def run_startup_and_shutdown() -> None:
        monkeypatch.setattr(main.settings, "enable_in_process_backup_loop", True)
        monkeypatch.setattr(main, "_apply_startup_schema_strategy", lambda: None)
        monkeypatch.setattr(main, "_close_due_sessions_on_startup", lambda: None)
        monkeypatch.setattr(main.backup_service, "ensure_daily_backup", fake_ensure_daily_backup)
        monkeypatch.setattr(main, "_daily_backup_loop", fake_daily_backup_loop)
        monkeypatch.setattr(main, "_daily_backup_task", None)

        main.startup_sync_schema()
        await asyncio.sleep(0)

        assert calls == {"ensure_daily_backup": 1, "loop_started": 1}
        assert main._daily_backup_task is not None

        await main.shutdown_background_tasks()
        assert main._daily_backup_task is None

    asyncio.run(run_startup_and_shutdown())
