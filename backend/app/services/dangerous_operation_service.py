from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models import DangerousOperationLog
from app.schemas.dangerous_action import DangerousActionConfirm


DEFAULT_API_ACTOR = "管理端"
DEFAULT_SCRIPT_ACTOR = "系统脚本"
RESTORE_BACKUP_CONFIRMATION = "RESTORE_BACKUP"
CLEAR_REIMPORT_CONFIRMATION = "DELETE REAL DATA"


def require_confirmation(
    payload: DangerousActionConfirm | None,
    *,
    action_label: str,
    confirmation_phrase: str | None = None,
) -> None:
    if payload is None or not payload.confirmed:
        raise bad_request(f"{action_label} 需要二次确认后才能执行")
    if confirmation_phrase and (payload.confirmation_text or "").strip() != confirmation_phrase:
        raise bad_request(f"{action_label} 需要输入确认词：{confirmation_phrase}")


def resolve_actor_name(actor_name: str | None, *, source: str = "api") -> str:
    fallback = DEFAULT_SCRIPT_ACTOR if source == "script" else DEFAULT_API_ACTOR
    normalized = (actor_name or "").strip()
    return normalized or fallback


def log_dangerous_operation(
    db: Session,
    *,
    operation_key: str,
    object_type: str,
    summary: str,
    actor_name: str | None = None,
    object_id: int | None = None,
    impact_scope: dict | None = None,
    confirmation_required: bool = True,
    confirmation_phrase: str | None = None,
    backup_path: str | Path | None = None,
    source: str = "api",
    status: str = "completed",
    extra_data: dict | None = None,
) -> DangerousOperationLog:
    log = DangerousOperationLog(
        operation_key=operation_key,
        object_type=object_type,
        object_id=object_id,
        actor_name=resolve_actor_name(actor_name, source=source),
        source=source,
        status=status,
        summary=summary,
        impact_scope=impact_scope,
        confirmation_required=confirmation_required,
        confirmation_phrase=confirmation_phrase,
        backup_path=str(backup_path) if backup_path else None,
        extra_data=extra_data,
    )
    db.add(log)
    db.flush()
    return log
