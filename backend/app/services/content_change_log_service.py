from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ContentChangeLog


DEFAULT_CONTENT_ACTOR = "管理端"


def resolve_actor_name(actor_name: str | None) -> str:
    normalized = (actor_name or "").strip()
    return normalized or DEFAULT_CONTENT_ACTOR


def log_content_change(
    db: Session,
    *,
    action_type: str,
    object_type: str,
    summary: str,
    actor_name: str | None = None,
    object_id: int | None = None,
    object_label: str | None = None,
    team_id: int | None = None,
    before_snapshot: dict | None = None,
    after_snapshot: dict | None = None,
    extra_context: dict | None = None,
) -> ContentChangeLog:
    log = ContentChangeLog(
        action_type=action_type,
        object_type=object_type,
        object_id=object_id,
        object_label=object_label,
        actor_name=resolve_actor_name(actor_name),
        team_id=team_id,
        summary=summary,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        extra_context=extra_context,
    )
    db.add(log)
    db.flush()
    return log
