from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentOverviewRead,
    AssignmentOverrideCreate,
    AssignmentOverrideRead,
    AssignmentOverrideUpdate,
    AssignmentRead,
    AssignmentUpdate,
    BatchAssignmentCancel,
    BatchAssignmentCreate,
    BatchAssignmentPreviewRead,
)
from app.services import access_control_service, assignment_service


router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentRead])
def list_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    sport_id = access_control_service.resolve_visible_sport_id(current_user)
    return assignment_service.list_assignments(db, sport_id=sport_id)


@router.post("", response_model=AssignmentRead)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    athlete = access_control_service.get_accessible_athlete(db, current_user, payload.athlete_id)
    access_control_service.ensure_template_assignable_to_athlete(db, current_user, payload.template_id, athlete)
    return assignment_service.create_assignment(db, payload)


@router.post("/preview", response_model=BatchAssignmentPreviewRead)
def preview_assignments(
    payload: BatchAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    athletes = [access_control_service.get_accessible_athlete(db, current_user, athlete_id) for athlete_id in payload.athlete_ids]
    if athletes:
        access_control_service.ensure_template_assignable_to_athlete(db, current_user, payload.template_id, athletes[0])
    return assignment_service.preview_batch_assignments(db, payload)


@router.post("/batch", response_model=list[AssignmentRead])
def create_batch_assignments(
    payload: BatchAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    athletes = [access_control_service.get_accessible_athlete(db, current_user, athlete_id) for athlete_id in payload.athlete_ids]
    if athletes:
        access_control_service.ensure_template_assignable_to_athlete(db, current_user, payload.template_id, athletes[0])
    return assignment_service.create_batch_assignments(db, payload)


@router.post("/cancel-batch", response_model=list[AssignmentRead])
def cancel_batch_assignments(
    payload: BatchAssignmentCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    for assignment_id in payload.assignment_ids:
        access_control_service.get_accessible_assignment(db, current_user, assignment_id)
    return assignment_service.cancel_batch_assignments(db, payload)


@router.get("/overview", response_model=AssignmentOverviewRead)
def get_assignment_overview(
    target_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return assignment_service.assignment_overview(
        db,
        target_date,
        sport_id=access_control_service.resolve_visible_sport_id(current_user),
    )


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_assignment(db, current_user, assignment_id)
    return assignment_service.get_assignment(db, assignment_id)


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    assignment = access_control_service.get_accessible_assignment(db, current_user, assignment_id)
    athlete = assignment.athlete or access_control_service.get_accessible_athlete(db, current_user, assignment.athlete_id)
    next_template_id = payload.template_id if payload.template_id is not None else assignment.template_id
    access_control_service.ensure_template_assignable_to_athlete(db, current_user, next_template_id, athlete)
    return assignment_service.update_assignment(db, assignment_id, payload)


@router.post("/{assignment_id}/overrides", response_model=AssignmentRead)
def create_override(
    assignment_id: int,
    payload: AssignmentOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_assignment(db, current_user, assignment_id)
    return assignment_service.create_override(db, assignment_id, payload)


@router.patch("/overrides/{override_id}", response_model=AssignmentOverrideRead)
def update_override(
    override_id: int,
    payload: AssignmentOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_override(db, current_user, override_id)
    return assignment_service.update_override(db, override_id, payload)
