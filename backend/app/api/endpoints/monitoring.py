from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.monitoring import MonitoringTodayRead
from app.services import monitoring_service


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/today", response_model=MonitoringTodayRead)
def get_monitoring_today(
    session_date: date = Query(...),
    team_id: int | None = Query(default=None),
    include_unassigned: bool = Query(default=True),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return monitoring_service.get_today_monitoring(
        db,
        session_date=session_date,
        team_id=team_id,
        include_unassigned=include_unassigned,
    )
