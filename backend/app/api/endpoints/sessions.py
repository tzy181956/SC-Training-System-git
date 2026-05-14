from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.exceptions import bad_request
from app.models import User
from app.schemas.training_session import (
    SessionFinishFeedbackUpdate,
    SessionFullSyncPayload,
    SessionFullSyncResponse,
    SessionRead,
    SessionSetSyncOperation,
    SessionSetSyncResponse,
    SessionSnapshotRead,
    SetRecordCreate,
    SetRecordUpdate,
    SetRecordUpdateResponse,
    SetSubmissionResponse,
    TrainingAthleteRead,
    TrainingModePlanListRead,
    TrainingSyncIssueRead,
    TrainingSyncIssueReportPayload,
    TrainingSyncIssueRetryResponse,
)
from app.services import access_control_service, session_service, training_sync_service


router = APIRouter(prefix="/training", tags=["training"])


def _commit_or_rollback(
    db: Session,
    operation,
    *,
    commit_on_http_statuses: set[int] | None = None,
):
    try:
        result = operation()
        db.commit()
        return result
    except HTTPException as exc:
        if commit_on_http_statuses and exc.status_code in commit_on_http_statuses:
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
        else:
            db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def _ensure_sync_operation_access(db: Session, current_user: User, payload: SessionSetSyncOperation) -> None:
    if payload.operation_type == "update_set" and payload.record_id is not None:
        access_control_service.get_accessible_set_record(db, current_user, payload.record_id)
    elif payload.operation_type == "create_set":
        if payload.session_item_id is not None:
            access_control_service.get_accessible_session_item(db, current_user, payload.session_item_id)
        elif payload.session_id is not None:
            access_control_service.get_accessible_session(db, current_user, payload.session_id)
        elif payload.assignment_id is not None:
            access_control_service.get_accessible_assignment(db, current_user, payload.assignment_id)
        else:
            raise bad_request("create_set requires session_item_id, session_id or assignment_id")
    else:
        if payload.session_id is not None:
            access_control_service.get_accessible_session(db, current_user, payload.session_id)
        else:
            access_control_service.get_accessible_assignment(db, current_user, payload.assignment_id)


@router.get("/athletes", response_model=list[TrainingAthleteRead])
def list_training_athletes(
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    target_date = session_date or date.today()
    visible_sport_id = access_control_service.resolve_visible_sport_id(current_user)
    return session_service.list_training_athletes(db, target_date, sport_id=visible_sport_id)


@router.get("/plans", response_model=TrainingModePlanListRead)
def list_training_plans(
    athlete_id: int = Query(...),
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    athlete, assignments = session_service.list_training_plans(db, athlete_id, session_date or date.today())
    return {"athlete": athlete, "session_date": session_date or date.today(), "assignments": assignments}


@router.post("/plans/{assignment_id}/session", response_model=SessionSnapshotRead)
def open_plan_session(
    assignment_id: int,
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_assignment(db, current_user, assignment_id)
        return session_service.open_session_for_assignment(db, assignment_id, session_date or date.today())

    return _commit_or_rollback(db, operation)


@router.get("/today", response_model=SessionSnapshotRead)
def get_today_session(
    athlete_id: int = Query(...),
    session_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    return session_service.get_today_session_preview(db, athlete_id, session_date or date.today())


@router.get("/sessions/{session_id}", response_model=SessionRead)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_session(db, current_user, session_id)
    return session_service.get_session_readonly(db, session_id)


@router.post("/sessions/{session_id}/recompute", response_model=SessionRead)
def recompute_session_state(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_session(db, current_user, session_id)
        return session_service.recompute_session_state(db, session_id)

    return _commit_or_rollback(db, operation)


@router.post("/session-items/{item_id}/sets", response_model=SetSubmissionResponse)
def submit_set(
    item_id: int,
    payload: SetRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_session_item(db, current_user, item_id)
        return session_service.submit_set_record(db, item_id, payload)

    record, next_suggestion, item, session = _commit_or_rollback(db, operation)
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
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_set_record(db, current_user, record_id)
        return session_service.update_set_record(db, record_id, payload)

    record, next_suggestion, item, session = _commit_or_rollback(db, operation)
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
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        _ensure_sync_operation_access(db, current_user, payload)
        return session_service.sync_session_operation(db, payload)

    record, next_suggestion, item, session = _commit_or_rollback(db, operation)
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
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_athlete(db, current_user, payload.athlete_id)
        access_control_service.get_accessible_assignment(db, current_user, payload.assignment_id)
        if payload.session_id is not None:
            access_control_service.get_accessible_session(db, current_user, payload.session_id)
        return session_service.sync_session_snapshot(db, payload)

    session, conflict_logged = _commit_or_rollback(db, operation, commit_on_http_statuses={409})
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
    current_user: User = Depends(require_roles("coach")),
):
    if athlete_id is not None:
        access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    return training_sync_service.list_sync_issues(
        db,
        athlete_id=athlete_id,
        sport_id=access_control_service.resolve_visible_sport_id(current_user),
        date_from=date_from,
        date_to=date_to,
        issue_status=issue_status,
    )


@router.post("/session-sync/issues/report", response_model=TrainingSyncIssueRead)
def report_sync_issue(
    payload: TrainingSyncIssueReportPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, payload.athlete_id)
    return training_sync_service.report_sync_issue(db, payload)


@router.post("/session-sync/issues/{issue_id}/resolve", response_model=TrainingSyncIssueRead)
def resolve_sync_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_sync_issue(db, current_user, issue_id)
    return training_sync_service.resolve_sync_issue(db, issue_id)


@router.post("/session-sync/issues/{issue_id}/retry", response_model=TrainingSyncIssueRetryResponse)
def retry_sync_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_sync_issue(db, current_user, issue_id)
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
    current_user: User = Depends(require_roles("coach")),
):
    payload.session_id = session_id
    return sync_session_operation(payload, db, current_user)


@router.post("/session-items/{item_id}/complete", response_model=SessionRead)
def complete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_session_item(db, current_user, item_id)
        item = session_service.complete_session_item(db, item_id)
        return session_service.get_session_readonly(db, item.session_id)

    return _commit_or_rollback(db, operation)


@router.post("/sessions/{session_id}/complete", response_model=SessionRead)
def complete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_session(db, current_user, session_id)
        return session_service.complete_session(db, session_id)

    return _commit_or_rollback(db, operation)


@router.post("/sessions/{session_id}/finish-feedback", response_model=SessionRead)
def submit_session_finish_feedback(
    session_id: int,
    payload: SessionFinishFeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    def operation():
        access_control_service.get_accessible_session(db, current_user, session_id)
        return session_service.submit_session_finish_feedback(db, session_id, payload)

    return _commit_or_rollback(db, operation)
