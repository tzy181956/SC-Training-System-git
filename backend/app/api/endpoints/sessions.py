from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.training_session import (
    SessionRead,
    SetRecordCreate,
    SetRecordUpdate,
    SetRecordUpdateResponse,
    SetSubmissionResponse,
    TrainingAthleteRead,
    TrainingModePlanListRead,
)
from app.services import session_service


router = APIRouter(prefix="/training", tags=["training"])


@router.get("/athletes", response_model=list[TrainingAthleteRead])
def list_training_athletes(
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return session_service.list_training_athletes(db, session_date or date.today())


@router.get("/plans", response_model=TrainingModePlanListRead)
def list_training_plans(
    athlete_id: int = Query(...),
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    athlete, assignments = session_service.list_training_plans(db, athlete_id, session_date or date.today())
    return {"athlete": athlete, "session_date": session_date or date.today(), "assignments": assignments}


@router.post("/plans/{assignment_id}/session", response_model=SessionRead)
def start_plan_session(
    assignment_id: int,
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return session_service.get_or_create_session_for_assignment(db, assignment_id, session_date or date.today())


@router.get("/today", response_model=SessionRead)
def get_today_session(
    athlete_id: int = Query(...),
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return session_service.get_or_create_today_session(db, athlete_id, session_date or date.today())


@router.get("/sessions/{session_id}", response_model=SessionRead)
def get_session(session_id: int, db: Session = Depends(get_db), _=Depends(require_roles("training", "coach"))):
    return session_service.get_session(db, session_id)


@router.post("/session-items/{item_id}/sets", response_model=SetSubmissionResponse)
def submit_set(item_id: int, payload: SetRecordCreate, db: Session = Depends(get_db), _=Depends(require_roles("training", "coach"))):
    record, next_suggestion, item, session = session_service.submit_set_record(db, item_id, payload)
    return {
        "record": record,
        "next_suggestion": next_suggestion,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
    }


@router.patch("/set-records/{record_id}", response_model=SetRecordUpdateResponse)
def update_set_record(
    record_id: int,
    payload: SetRecordUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    record, next_suggestion, item, session = session_service.update_set_record(db, record_id, payload)
    return {
        "record": record,
        "next_suggestion": next_suggestion,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
    }


@router.post("/session-items/{item_id}/complete", response_model=SessionRead)
def complete_item(item_id: int, db: Session = Depends(get_db), _=Depends(require_roles("training", "coach"))):
    item = session_service.complete_session_item(db, item_id)
    return session_service.get_session(db, item.session_id)


@router.post("/sessions/{session_id}/complete", response_model=SessionRead)
def complete_session(session_id: int, db: Session = Depends(get_db), _=Depends(require_roles("training", "coach"))):
    return session_service.complete_session(db, session_id)
