import asyncio
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.schema_sync import ensure_runtime_schema
from app.services import backup_service
from app.services.session_service import close_due_sessions


settings = get_settings()
app = FastAPI(title=settings.app_name)
AUTO_BACKUP_INTERVAL_SECONDS = 3600
_daily_backup_task: asyncio.Task | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup_sync_schema() -> None:
    global _daily_backup_task
    ensure_runtime_schema()
    registered_paths = {route.path for route in app.routes}
    expected_paths = {
        f"{settings.api_prefix}/exercise-categories",
        f"{settings.api_prefix}/exercise-categories/tree",
    }
    missing_paths = sorted(expected_paths - registered_paths)
    if missing_paths:
        print(f"[STARTUP] Missing exercise category routes: {', '.join(missing_paths)}")
    else:
        print(f"[STARTUP] Exercise category routes registered: {', '.join(sorted(expected_paths))}")
    _close_due_sessions_on_startup()
    try:
        daily_backup_result = backup_service.ensure_daily_backup()
        if daily_backup_result.created and daily_backup_result.backup_path:
            print(f"[BACKUP] Daily backup created: {daily_backup_result.backup_path}")
    except Exception as exc:
        print(f"[BACKUP] Failed to create daily backup during startup: {exc}")
    if _daily_backup_task is None:
        _daily_backup_task = asyncio.create_task(_daily_backup_loop())


@app.on_event("shutdown")
async def shutdown_background_tasks() -> None:
    global _daily_backup_task
    if _daily_backup_task is None:
        return
    _daily_backup_task.cancel()
    with suppress(asyncio.CancelledError):
        await _daily_backup_task
    _daily_backup_task = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _close_due_sessions_on_startup() -> None:
    db = SessionLocal()
    try:
        closed_count = close_due_sessions(db)
        if closed_count:
            print(f"[STARTUP] Closed {closed_count} overdue training sessions before serving requests.")
    except Exception as exc:
        print(f"[STARTUP] Failed to close overdue training sessions: {exc}")
        raise
    finally:
        db.close()


async def _daily_backup_loop() -> None:
    while True:
        try:
            result = backup_service.ensure_daily_backup()
            if result.created and result.backup_path:
                print(f"[BACKUP] Daily backup created: {result.backup_path}")
        except Exception as exc:
            print(f"[BACKUP] Daily backup loop failed: {exc}")

        await asyncio.sleep(AUTO_BACKUP_INTERVAL_SECONDS)
