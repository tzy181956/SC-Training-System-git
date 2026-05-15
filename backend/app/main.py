import asyncio
from contextlib import suppress
from pathlib import Path
import uuid

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import RequestIDMiddleware, get_logger
from app.core.project_meta import PROJECT_AUTHOR_HANDLE
from app.core.schema_sync import ensure_runtime_schema
from app.services import backup_service
from app.services.session_service import close_due_sessions


settings = get_settings()
logger = get_logger(__name__)
app = FastAPI(title=settings.app_name, contact={"name": PROJECT_AUTHOR_HANDLE})
AUTO_BACKUP_INTERVAL_SECONDS = 3600
BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALLOWED_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_CORS_HEADERS = ["Authorization", "Content-Type", "X-Request-ID"]
_daily_backup_task: asyncio.Task | None = None
_alembic_head_revision: str | None = None
_alembic_head_error: str | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=ALLOWED_CORS_METHODS,
    allow_headers=ALLOWED_CORS_HEADERS,
)
app.add_middleware(RequestIDMiddleware)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup_sync_schema() -> None:
    global _daily_backup_task
    _cache_alembic_head_revision()
    _apply_startup_schema_strategy()
    registered_paths = {route.path for route in app.routes}
    expected_paths = {
        f"{settings.api_prefix}/exercise-categories",
        f"{settings.api_prefix}/exercise-categories/tree",
    }
    missing_paths = sorted(expected_paths - registered_paths)
    if missing_paths:
        logger.warning(
            "missing_expected_routes",
            extra={"event": "startup", "path": ",".join(missing_paths)},
        )
    else:
        logger.info(
            "expected_routes_registered",
            extra={"event": "startup", "path": ",".join(sorted(expected_paths))},
        )
    _close_due_sessions_on_startup()
    if settings.enable_in_process_backup_loop:
        try:
            daily_backup_result = backup_service.ensure_daily_backup()
            if daily_backup_result.created and daily_backup_result.backup_path:
                logger.info(
                    "daily_backup_created",
                    extra={
                        "event": "backup",
                        "backup_path": str(daily_backup_result.backup_path),
                    },
                )
        except Exception:
            logger.exception(
                "startup_daily_backup_failed",
                extra={"event": "backup", "check": "startup_daily_backup"},
            )
        if _daily_backup_task is None:
            _daily_backup_task = asyncio.create_task(_daily_backup_loop())
    else:
        logger.info("in_process_backup_loop_disabled", extra={"event": "backup"})


@app.on_event("shutdown")
async def shutdown_background_tasks() -> None:
    global _daily_backup_task
    if _daily_backup_task is None:
        return
    _daily_backup_task.cancel()
    with suppress(asyncio.CancelledError):
        await _daily_backup_task
    _daily_backup_task = None
    logger.info("background_tasks_shutdown", extra={"event": "shutdown"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response) -> dict:
    checks = {
        "database": _check_database_ready(),
    }
    is_ready = all(check["status"] == "ok" for check in checks.values())
    if not is_ready:
        response.status_code = 503
    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }


@app.get("/ready/deep")
def ready_deep(response: Response) -> dict:
    checks = {
        "database": _check_database_ready(),
        "backup_directory": _check_backup_directory_ready(),
        "alembic_revision": _check_alembic_revision_ready(),
    }
    is_ready = all(check["status"] == "ok" for check in checks.values())
    if not is_ready:
        response.status_code = 503
    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }


def _close_due_sessions_on_startup() -> None:
    db = SessionLocal()
    try:
        closed_count = close_due_sessions(db)
        if closed_count:
            logger.info(
                "overdue_training_sessions_closed",
                extra={"event": "startup", "closed_count": closed_count},
            )
    except Exception:
        logger.exception(
            "close_due_sessions_failed",
            extra={"event": "startup", "check": "close_due_sessions"},
        )
        raise
    finally:
        db.close()


def _apply_startup_schema_strategy() -> None:
    if settings.is_production:
        logger.info(
            "runtime_schema_sync_disabled",
            extra={"event": "startup", "check": "schema"},
        )
        return

    logger.info(
        "runtime_schema_fallback_enabled",
        extra={"event": "startup", "check": "schema"},
    )
    ensure_runtime_schema()


def _check_database_ready() -> dict[str, str]:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.exception("readiness_database_failed", extra={"event": "ready", "check": "database"})
        return {"status": "error", "detail": "database check failed"}
    finally:
        db.close()


def _check_backup_directory_ready() -> dict[str, str]:
    marker_path = None
    try:
        backup_dir = backup_service.get_backup_directory()
        backup_dir.mkdir(parents=True, exist_ok=True)
        marker_path = backup_dir / f".ready-check-{uuid.uuid4().hex}.tmp"
        marker_path.write_text("ok", encoding="utf-8")
        return {"status": "ok"}
    except Exception:
        logger.exception(
            "readiness_backup_directory_failed",
            extra={"event": "ready", "check": "backup_directory"},
        )
        return {"status": "error", "detail": "backup directory is not writable"}
    finally:
        if marker_path is not None:
            marker_path.unlink(missing_ok=True)


def _cache_alembic_head_revision() -> None:
    global _alembic_head_error, _alembic_head_revision
    try:
        config = Config(str(ALEMBIC_INI))
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()
        if not head_revision:
            raise RuntimeError("alembic head revision is empty")
        _alembic_head_revision = head_revision
        _alembic_head_error = None
    except Exception as exc:  # noqa: BLE001
        _alembic_head_revision = None
        _alembic_head_error = str(exc)
        logger.exception("alembic_head_revision_cache_failed", extra={"event": "ready", "check": "alembic"})


def _check_alembic_revision_ready() -> dict[str, str | None]:
    if _alembic_head_revision is None and _alembic_head_error is None:
        _cache_alembic_head_revision()

    if _alembic_head_revision is None:
        return {
            "status": "error",
            "detail": "alembic head revision unavailable",
            "current_revision": None,
            "head_revision": None,
        }

    current_revision = _get_database_alembic_revision()
    if current_revision is None:
        return {
            "status": "error",
            "detail": "database alembic revision is missing",
            "current_revision": None,
            "head_revision": _alembic_head_revision,
        }
    if current_revision != _alembic_head_revision:
        return {
            "status": "error",
            "detail": "database alembic revision is not at head",
            "current_revision": current_revision,
            "head_revision": _alembic_head_revision,
        }
    return {
        "status": "ok",
        "current_revision": current_revision,
        "head_revision": _alembic_head_revision,
    }


def _get_database_alembic_revision() -> str | None:
    db = SessionLocal()
    try:
        return db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()
    except SQLAlchemyError:
        return None
    finally:
        db.close()


async def _daily_backup_loop() -> None:
    while True:
        try:
            result = backup_service.ensure_daily_backup()
            if result.created and result.backup_path:
                logger.info(
                    "daily_backup_created",
                    extra={
                        "event": "backup",
                        "backup_path": str(result.backup_path),
                    },
                )
        except Exception:
            logger.exception("daily_backup_loop_failed", extra={"event": "backup"})

        await asyncio.sleep(AUTO_BACKUP_INTERVAL_SECONDS)
