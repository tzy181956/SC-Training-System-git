from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.score_profile import (
    ScoreCalculationRequest,
    ScoreCalculationResponse,
    ScoreProfileCreate,
    ScoreProfileRead,
    ScoreProfileUpdate,
)
from app.services import dangerous_operation_service, score_profile_service


router = APIRouter(prefix="/test-scores", tags=["test-scores"])


@router.get("/profiles", response_model=list[ScoreProfileRead])
def list_score_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return score_profile_service.list_score_profiles(db, current_user)


@router.get("/profiles/{profile_id}", response_model=ScoreProfileRead)
def get_score_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return score_profile_service.get_score_profile(db, current_user, profile_id)


@router.post("/profiles", response_model=ScoreProfileRead)
def create_score_profile(
    payload: ScoreProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return score_profile_service.create_score_profile(db, payload, current_user)


@router.patch("/profiles/{profile_id}", response_model=ScoreProfileRead)
def update_score_profile(
    profile_id: int,
    payload: ScoreProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return score_profile_service.update_score_profile(db, profile_id, payload, current_user)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_score_profile(
    profile_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除评分模板")
    score_profile_service.delete_score_profile(
        db,
        profile_id,
        current_user,
        actor_name=payload.actor_name or current_user.display_name,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/calculate", response_model=ScoreCalculationResponse)
def calculate_scores(
    payload: ScoreCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return score_profile_service.calculate_scores(db, payload, current_user)
