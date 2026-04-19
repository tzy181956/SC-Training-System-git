from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
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
from app.services import assignment_service


router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentRead])
def list_assignments(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.list_assignments(db)


@router.post("", response_model=AssignmentRead)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.create_assignment(db, payload)


@router.post("/preview", response_model=BatchAssignmentPreviewRead)
def preview_assignments(payload: BatchAssignmentCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.preview_batch_assignments(db, payload)


@router.post("/batch", response_model=list[AssignmentRead])
def create_batch_assignments(payload: BatchAssignmentCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.create_batch_assignments(db, payload)


@router.post("/cancel-batch", response_model=list[AssignmentRead])
def cancel_batch_assignments(payload: BatchAssignmentCancel, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.cancel_batch_assignments(db, payload)


@router.get("/overview", response_model=AssignmentOverviewRead)
def get_assignment_overview(
    target_date: date = Query(...),
    db: Session = Depends(get_db),
    _=Depends(require_roles("coach")),
):
    return assignment_service.assignment_overview(db, target_date)


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(assignment_id: int, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.get_assignment(db, assignment_id)


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(assignment_id: int, payload: AssignmentUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.update_assignment(db, assignment_id, payload)


@router.post("/{assignment_id}/overrides", response_model=AssignmentRead)
def create_override(assignment_id: int, payload: AssignmentOverrideCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.create_override(db, assignment_id, payload)


@router.patch("/overrides/{override_id}", response_model=AssignmentOverrideRead)
def update_override(override_id: int, payload: AssignmentOverrideUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return assignment_service.update_override(db, override_id, payload)
