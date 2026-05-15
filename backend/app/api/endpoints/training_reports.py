from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.training_report import TrainingReportRead, TrainingReportSessionRead
from app.schemas.training_session import (
    CoachSetRecordCreate,
    CoachSetRecordDeleteResponse,
    CoachSetRecordUpdate,
    SessionRead,
    SetRecordUpdateResponse,
    SetSubmissionResponse,
)
from app.services import access_control_service, dangerous_operation_service, session_service, training_report_service


router = APIRouter(prefix="/training-reports", tags=["training-reports"])


def _commit_or_rollback(db: Session, operation):
    try:
        result = operation()
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=TrainingReportRead)
def get_training_report(
    athlete_id: int = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    include_details: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    end_date = date_to or date.today()
    start_date = date_from or (end_date - timedelta(days=29))
    return training_report_service.get_training_report(
        db,
        athlete_id,
        start_date,
        end_date,
        include_details=include_details,
    )


@router.get("/sessions/{session_id}", response_model=TrainingReportSessionRead)
def get_training_report_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_session(db, current_user, session_id)
    return training_report_service.get_training_report_session_detail(db, session_id)


@router.patch("/set-records/{record_id}", response_model=SetRecordUpdateResponse)
def coach_update_set_record(
    record_id: int,
    payload: CoachSetRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_set_record(db, current_user, record_id)
        return session_service.coach_update_set_record(db, record_id, payload)

    record, next_suggestion, item, session = _commit_or_rollback(db, operation)
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
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_session_item(db, current_user, item_id)
        return session_service.coach_add_set_record(db, item_id, payload)

    record, next_suggestion, item, session = _commit_or_rollback(db, operation)
    return {
        "record": record,
        "next_suggestion": next_suggestion,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
    }


@router.delete("/set-records/{record_id}", response_model=CoachSetRecordDeleteResponse)
def coach_delete_set_record(
    record_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        dangerous_operation_service.require_confirmation(payload, action_label="删除训练记录")
        access_control_service.get_accessible_set_record(db, current_user, record_id)
        return session_service.coach_delete_set_record(
            db,
            record_id,
            actor_name=payload.actor_name or current_user.display_name,
        )

    item, session = _commit_or_rollback(db, operation)
    return {
        "deleted_record_id": record_id,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
    }


@router.post("/sessions/{session_id}/void", response_model=SessionRead)
def coach_void_training_session(
    session_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        dangerous_operation_service.require_confirmation(payload, action_label="作废训练课")
        access_control_service.get_accessible_session(db, current_user, session_id)
        return session_service.void_training_session(
            db,
            session_id,
            actor_name=payload.actor_name or current_user.display_name,
        )

    return _commit_or_rollback(db, operation)
