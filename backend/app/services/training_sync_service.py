from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Athlete, TrainingSyncIssue
from app.schemas.training_session import SessionFullSyncPayload, TrainingSyncIssueReportPayload
from app.services import session_service


def list_sync_issues(
    db: Session,
    *,
    athlete_id: int | None = None,
    team_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    issue_status: str = "manual_retry_required",
    limit: int = 50,
) -> list[dict]:
    query = db.query(TrainingSyncIssue).filter(TrainingSyncIssue.issue_status == issue_status)
    if athlete_id is not None:
        query = query.filter(TrainingSyncIssue.athlete_id == athlete_id)
    if team_id is not None:
        query = query.join(Athlete, Athlete.id == TrainingSyncIssue.athlete_id).filter(Athlete.team_id == team_id)
    if date_from is not None:
        query = query.filter(TrainingSyncIssue.session_date >= date_from)
    if date_to is not None:
        query = query.filter(TrainingSyncIssue.session_date <= date_to)

    issues = query.order_by(TrainingSyncIssue.updated_at.desc(), TrainingSyncIssue.id.desc()).limit(limit).all()
    return [_serialize_issue(db, issue) for issue in issues]


def report_sync_issue(db: Session, payload: TrainingSyncIssueReportPayload) -> dict:
    issue = db.query(TrainingSyncIssue).filter(TrainingSyncIssue.session_key == payload.session_key).first()
    if issue is None:
        issue = TrainingSyncIssue(
            athlete_id=payload.athlete_id,
            assignment_id=payload.assignment_id,
            session_id=payload.session_id,
            session_date=payload.session_date,
            session_key=payload.session_key,
            issue_status="manual_retry_required",
            summary=payload.summary,
            failure_count=max(payload.failure_count, 0),
            last_error=payload.last_error,
            sync_payload=payload.sync_payload.model_dump(mode="json"),
            resolved_at=None,
        )
        db.add(issue)
    else:
        issue.athlete_id = payload.athlete_id
        issue.assignment_id = payload.assignment_id
        issue.session_id = payload.session_id
        issue.session_date = payload.session_date
        issue.issue_status = "manual_retry_required"
        issue.summary = payload.summary
        issue.failure_count = max(payload.failure_count, issue.failure_count, 0)
        issue.last_error = payload.last_error
        issue.sync_payload = payload.sync_payload.model_dump(mode="json")
        issue.resolved_at = None

    db.commit()
    db.refresh(issue)
    return _serialize_issue(db, issue)


def resolve_sync_issue(db: Session, issue_id: int) -> dict:
    issue = db.get(TrainingSyncIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="未找到同步异常记录")

    issue.issue_status = "resolved"
    issue.resolved_at = datetime.now(timezone.utc)
    issue.last_error = None
    db.commit()
    db.refresh(issue)
    return _serialize_issue(db, issue)


def retry_sync_issue(db: Session, issue_id: int) -> tuple[dict, object, bool]:
    issue = db.get(TrainingSyncIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="未找到同步异常记录")
    if not issue.sync_payload:
        raise HTTPException(status_code=400, detail="同步异常记录中缺少可重试的本地快照")

    try:
        payload = SessionFullSyncPayload.model_validate(issue.sync_payload)
        session, conflict_logged = session_service.sync_session_snapshot(db, payload)
    except Exception as exc:
        detail = getattr(exc, "detail", None)
        issue.issue_status = "manual_retry_required"
        issue.failure_count = max(issue.failure_count, 0) + 1
        issue.last_error = str(detail or exc)
        issue.summary = "手动重试失败，本地草稿仍需教练或管理员继续处理。"
        issue.resolved_at = None
        db.commit()
        raise

    issue.session_id = session.id
    issue.issue_status = "resolved"
    issue.resolved_at = datetime.now(timezone.utc)
    issue.last_error = None
    issue.summary = "手动重试已完成，后端训练课已按最新本地草稿更新。"
    db.commit()
    db.refresh(issue)
    return _serialize_issue(db, issue), session, conflict_logged


def _serialize_issue(db: Session, issue: TrainingSyncIssue) -> dict:
    athlete = db.get(Athlete, issue.athlete_id)
    return {
        "id": issue.id,
        "athlete_id": issue.athlete_id,
        "athlete_name": athlete.full_name if athlete else None,
        "assignment_id": issue.assignment_id,
        "session_id": issue.session_id,
        "session_date": issue.session_date,
        "session_key": issue.session_key,
        "issue_status": issue.issue_status,
        "summary": issue.summary,
        "failure_count": issue.failure_count,
        "last_error": issue.last_error,
        "updated_at": issue.updated_at,
        "resolved_at": issue.resolved_at,
    }
