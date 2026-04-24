from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.training_report import TrainingReportRead
from app.schemas.training_session import CoachSetRecordCreate, CoachSetRecordUpdate, SetRecordUpdateResponse, SetSubmissionResponse
from app.services import training_report_service
from app.services import session_service


router = APIRouter(prefix="/training-reports", tags=["training-reports"])


@router.get("", response_model=TrainingReportRead)
def get_training_report(
    athlete_id: int = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    end_date = date_to or date.today()
    start_date = date_from or (end_date - timedelta(days=29))
    return training_report_service.get_training_report(db, athlete_id, start_date, end_date)


@router.patch("/set-records/{record_id}", response_model=SetRecordUpdateResponse)
def coach_update_set_record(
    record_id: int,
    payload: CoachSetRecordUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    record, next_suggestion, item, session = session_service.coach_update_set_record(db, record_id, payload)
    return {
        "record": record,
        "next_suggestion": next_suggestion,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
    }


@router.post("/session-items/{item_id}/sets", response_model=SetSubmissionResponse)
def coach_add_set_record(
    item_id: int,
    payload: CoachSetRecordCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    record, next_suggestion, item, session = session_service.coach_add_set_record(db, item_id, payload)
    return {
        "record": record,
        "next_suggestion": next_suggestion,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
    }
