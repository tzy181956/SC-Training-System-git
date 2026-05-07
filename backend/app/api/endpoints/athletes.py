from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.athlete import AthleteCreate, AthleteRead, AthleteUpdate, SportCreate, SportRead, TeamCreate, TeamRead
from app.schemas.dangerous_action import DangerousActionConfirm
from app.services import access_control_service, athlete_service, dangerous_operation_service


router = APIRouter(tags=["athletes"])


@router.get("/sports", response_model=list[SportRead])
def list_sports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    _ = current_user
    return athlete_service.list_sports(db)


@router.post("/sports", response_model=SportRead)
def create_sport(
    payload: SportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    return athlete_service.create_sport(db, payload)


@router.delete("/sports/{sport_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sport(
    sport_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除项目")
    athlete_service.delete_sport(db, sport_id, actor_name=payload.actor_name or current_user.display_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/teams", response_model=list[TeamRead])
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return athlete_service.list_teams(db, sport_id=access_control_service.resolve_visible_sport_id(current_user))


@router.post("/teams", response_model=TeamRead)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    if not access_control_service.is_admin(current_user):
        payload = payload.model_copy(update={"sport_id": access_control_service.ensure_sport_bound_user(current_user)})
    return athlete_service.create_team(db, payload)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除队伍")
    access_control_service.get_accessible_team(db, current_user, team_id)
    athlete_service.delete_team(db, team_id, actor_name=payload.actor_name or current_user.display_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/athletes", response_model=list[AthleteRead])
def list_athletes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return athlete_service.list_athletes(db, sport_id=access_control_service.resolve_visible_sport_id(current_user))


@router.post("/athletes", response_model=AthleteRead)
def create_athlete(
    payload: AthleteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    if not access_control_service.is_admin(current_user):
        if payload.team_id is not None:
            access_control_service.get_accessible_team(db, current_user, payload.team_id)
        payload = payload.model_copy(update={"sport_id": access_control_service.ensure_sport_bound_user(current_user)})
    return athlete_service.create_athlete(db, payload)


@router.get("/athletes/{athlete_id}", response_model=AthleteRead)
def get_athlete(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    return athlete_service.get_athlete(db, athlete_id)


@router.patch("/athletes/{athlete_id}", response_model=AthleteRead)
def update_athlete(
    athlete_id: int,
    payload: AthleteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    if not access_control_service.is_admin(current_user):
        if payload.team_id is not None:
            access_control_service.get_accessible_team(db, current_user, payload.team_id)
        payload = payload.model_copy(update={"sport_id": access_control_service.ensure_sport_bound_user(current_user)})
    return athlete_service.update_athlete(db, athlete_id, payload)


@router.delete("/athletes/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_athlete(
    athlete_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除运动员")
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    athlete_service.delete_athlete(db, athlete_id, actor_name=payload.actor_name or current_user.display_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
