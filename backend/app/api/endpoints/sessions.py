from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.training_session import (
    SessionFinishFeedbackUpdate,
    SessionFullSyncPayload,
    SessionFullSyncResponse,
    SessionRead,
    SessionSnapshotRead,
    SessionSetSyncOperation,
    SessionSetSyncResponse,
    SetRecordCreate,
    SetRecordUpdate,
    SetRecordUpdateResponse,
    SetSubmissionResponse,
    TrainingSyncIssueRead,
    TrainingSyncIssueReportPayload,
    TrainingSyncIssueRetryResponse,
    TrainingAthleteRead,
    TrainingModePlanListRead,
)
from app.services import session_service, training_sync_service


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


@router.post("/plans/{assignment_id}/session", response_model=SessionSnapshotRead)
def open_plan_session(
    assignment_id: int,
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return session_service.open_session_for_assignment(db, assignment_id, session_date or date.today())


@router.get("/today", response_model=SessionSnapshotRead)
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


@router.post("/session-sync", response_model=SessionSetSyncResponse)
def sync_session_operation(
    payload: SessionSetSyncOperation,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    record, next_suggestion, item, session = session_service.sync_session_operation(db, payload)
    return {
        "record": record,
        "next_suggestion": next_suggestion,
        "item": item,
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
        "operation_type": payload.operation_type,
        "local_record_id": payload.local_record_id,
        "sync_status": "synced",
    }


@router.post("/session-sync/full", response_model=SessionFullSyncResponse)
def sync_session_snapshot(
    payload: SessionFullSyncPayload,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    session, conflict_logged = session_service.sync_session_snapshot(db, payload)
    return {
        "session": session,
        "session_status": session.status,
        "session_completed_at": session.completed_at,
        "sync_status": "synced",
        "sync_mode": "full",
        "conflict_logged": conflict_logged,
    }


@router.get("/session-sync/issues", response_model=list[TrainingSyncIssueRead])
def list_sync_issues(
    athlete_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    issue_status: str = Query(default="manual_retry_required"),
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return training_sync_service.list_sync_issues(
        db,
        athlete_id=athlete_id,
        date_from=date_from,
        date_to=date_to,
        issue_status=issue_status,
    )


@router.post("/session-sync/issues/report", response_model=TrainingSyncIssueRead)
def report_sync_issue(
    payload: TrainingSyncIssueReportPayload,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return training_sync_service.report_sync_issue(db, payload)


@router.post("/session-sync/issues/{issue_id}/resolve", response_model=TrainingSyncIssueRead)
def resolve_sync_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return training_sync_service.resolve_sync_issue(db, issue_id)


@router.post("/session-sync/issues/{issue_id}/retry", response_model=TrainingSyncIssueRetryResponse)
def retry_sync_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    issue, session, conflict_logged = training_sync_service.retry_sync_issue(db, issue_id)
    return {
        "issue": issue,
        "session": session,
        "conflict_logged": conflict_logged,
    }


@router.post("/sessions/{session_id}/sync-set", response_model=SessionSetSyncResponse)
def sync_session_set(
    session_id: int,
    payload: SessionSetSyncOperation,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    payload.session_id = session_id
    return sync_session_operation(payload, db, _)


@router.post("/session-items/{item_id}/complete", response_model=SessionRead)
def complete_item(item_id: int, db: Session = Depends(get_db), _=Depends(require_roles("training", "coach"))):
    item = session_service.complete_session_item(db, item_id)
    return session_service.get_session(db, item.session_id)


@router.post("/sessions/{session_id}/complete", response_model=SessionRead)
def complete_session(session_id: int, db: Session = Depends(get_db), _=Depends(require_roles("training", "coach"))):
    return session_service.complete_session(db, session_id)


@router.post("/sessions/{session_id}/finish-feedback", response_model=SessionRead)
def submit_session_finish_feedback(
    session_id: int,
    payload: SessionFinishFeedbackUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("training", "coach")),
):
    return session_service.submit_session_finish_feedback(db, session_id, payload)
