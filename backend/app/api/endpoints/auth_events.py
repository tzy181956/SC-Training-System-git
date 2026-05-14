from datetime import date, datetime, time, timedelta
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import AuthEventLog, User
from app.schemas.auth_event import AuthEventLogListRead


router = APIRouter(prefix="/auth-events", tags=["auth-events"])


@router.get("", response_model=AuthEventLogListRead)
def list_auth_events(
    username: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    failure_reason: str | None = Query(default=None),
    ip: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
) -> AuthEventLogListRead:
    _ = current_user
    query = db.query(AuthEventLog)

    normalized_username = _normalize_filter_value(username)
    if normalized_username:
        query = query.filter(AuthEventLog.username.ilike(f"%{normalized_username}%"))

    if success is not None:
        query = query.filter(AuthEventLog.success.is_(success))

    normalized_failure_reason = _normalize_filter_value(failure_reason)
    if normalized_failure_reason:
        query = query.filter(AuthEventLog.failure_reason == normalized_failure_reason)

    normalized_ip = _normalize_filter_value(ip)
    if normalized_ip:
        query = query.filter(AuthEventLog.ip.ilike(f"%{normalized_ip}%"))

    if date_from is not None:
        query = query.filter(AuthEventLog.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        query = query.filter(AuthEventLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    total = query.with_entities(func.count(AuthEventLog.id)).scalar() or 0
    total_pages = ceil(total / page_size) if total else 0
    items = (
        query.order_by(AuthEventLog.created_at.desc(), AuthEventLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return AuthEventLogListRead(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def _normalize_filter_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
