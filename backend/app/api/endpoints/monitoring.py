from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.monitoring import MonitoringAthleteDetailRead, MonitoringTodayRead
from app.services import access_control_service, monitoring_service


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/today", response_model=MonitoringTodayRead)
def get_monitoring_today(
    session_date: date = Query(...),
    sport_id: int | None = Query(default=None),
    team_id: int | None = Query(default=None),
    include_unassigned: bool = Query(default=True),
    force_refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    resolved_sport_id = access_control_service.resolve_visible_sport_id(current_user, sport_id)
    resolved_team_id = access_control_service.resolve_visible_team_id(db, current_user, team_id)
    return monitoring_service.get_today_monitoring(
        db,
        session_date=session_date,
        sport_id=resolved_sport_id,
        team_id=resolved_team_id,
        include_unassigned=include_unassigned if access_control_service.is_admin(current_user) else False,
        force_refresh=force_refresh,
    )


@router.get("/athlete-detail", response_model=MonitoringAthleteDetailRead)
def get_monitoring_athlete_detail(
    session_date: date = Query(...),
    athlete_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    return monitoring_service.get_athlete_monitoring_detail(
        db,
        session_date=session_date,
        athlete_id=athlete_id,
    )
