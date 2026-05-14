from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.system import CloseDueSessionsRead, DashboardMemoRead, DashboardMemoUpdate, ServerTimeRead
from app.services import dashboard_memo_service, session_service


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/server-time", response_model=ServerTimeRead)
def get_server_time(
    current_user: User = Depends(require_roles("coach")),
):
    now = datetime.now().astimezone()
    utc_offset = now.utcoffset()
    return ServerTimeRead(
        server_time=now,
        timezone=now.tzname() or "local",
        utc_offset_minutes=int(utc_offset.total_seconds() // 60) if utc_offset else 0,
    )


@router.get("/dashboard-memo", response_model=DashboardMemoRead)
def get_dashboard_memo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    memo = dashboard_memo_service.get_memo_for_user(db, current_user.id)
    if memo is None:
        return DashboardMemoRead()
    return DashboardMemoRead(content=memo.content, updated_at=memo.updated_at)


@router.put("/dashboard-memo", response_model=DashboardMemoRead)
def update_dashboard_memo(
    payload: DashboardMemoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    memo = dashboard_memo_service.upsert_memo_for_user(db, current_user.id, payload.content)
    return DashboardMemoRead(content=memo.content, updated_at=memo.updated_at)


@router.post("/maintenance/close-due-sessions", response_model=CloseDueSessionsRead)
def close_due_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    _ = current_user
    return CloseDueSessionsRead(closed_count=session_service.close_due_sessions(db))
