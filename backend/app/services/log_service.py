from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.models import (
    Athlete,
    ContentChangeLog,
    DangerousOperationLog,
    Exercise,
    Team,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingSession,
    TrainingSessionEditLog,
    TrainingSessionItem,
    TrainingSyncConflict,
    TrainingSyncIssue,
    User,
)
from app.schemas.logs import LogItemRead


SYSTEM_ACTOR_NAME = "系统"
MAX_LOG_LIMIT = 500


def list_logs(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    actor_name: str | None = None,
    object_type: str | None = None,
    limit: int = 200,
    current_user: User | None = None,
) -> dict:
    normalized_limit = max(1, min(limit, MAX_LOG_LIMIT))
    start_at, end_at = _build_datetime_range(date_from, date_to)

    items: list[LogItemRead] = []
    items.extend(_list_content_change_logs(db, start_at=start_at, end_at=end_at))
    items.extend(_list_training_edit_logs(db, start_at=start_at, end_at=end_at))
    items.extend(_list_sync_issue_logs(db, start_at=start_at, end_at=end_at))
    items.extend(_list_sync_conflict_logs(db, start_at=start_at, end_at=end_at))
    items.extend(_list_dangerous_operation_logs(db, start_at=start_at, end_at=end_at))

    items = _apply_visibility(db, items, current_user)

    actor_filter = (actor_name or "").strip().lower()
    if actor_filter:
        items = [item for item in items if actor_filter in item.actor_name.lower()]

    if object_type:
        items = [item for item in items if item.object_type == object_type]

    items.sort(key=lambda item: (item.occurred_at, item.id), reverse=True)
    available_object_types = sorted({item.object_type for item in items if item.object_type})
    return {
        "items": items[:normalized_limit],
        "available_object_types": available_object_types,
    }


def _list_content_change_logs(db: Session, *, start_at: datetime | None, end_at: datetime | None) -> list[LogItemRead]:
    query = (
        db.query(ContentChangeLog, Team)
        .outerjoin(Team, Team.id == ContentChangeLog.team_id)
        .order_by(ContentChangeLog.created_at.desc(), ContentChangeLog.id.desc())
    )
    if start_at is not None:
        query = query.filter(ContentChangeLog.created_at >= start_at)
    if end_at is not None:
        query = query.filter(ContentChangeLog.created_at <= end_at)

    return [
        LogItemRead(
            id=log.id,
            source_type="content_change",
            action_type=log.action_type,
            object_type=log.object_type,
            object_id=log.object_id,
            object_label=log.object_label,
            summary=log.summary,
            actor_name=log.actor_name,
            occurred_at=log.created_at,
            team_id=log.team_id,
            team_name=team.name if team else None,
            before_snapshot=log.before_snapshot,
            after_snapshot=log.after_snapshot,
            extra_context=log.extra_context,
        )
        for log, team in query.all()
    ]


def _list_training_edit_logs(db: Session, *, start_at: datetime | None, end_at: datetime | None) -> list[LogItemRead]:
    query = (
        db.query(
            TrainingSessionEditLog,
            TrainingSession,
            Athlete,
            Team,
            TrainingSessionItem,
            Exercise,
        )
        .join(TrainingSession, TrainingSession.id == TrainingSessionEditLog.session_id)
        .join(Athlete, Athlete.id == TrainingSession.athlete_id)
        .outerjoin(Team, Team.id == Athlete.team_id)
        .outerjoin(TrainingSessionItem, TrainingSessionItem.id == TrainingSessionEditLog.session_item_id)
        .outerjoin(Exercise, Exercise.id == TrainingSessionItem.exercise_id)
        .order_by(TrainingSessionEditLog.created_at.desc(), TrainingSessionEditLog.id.desc())
    )
    if start_at is not None:
        query = query.filter(TrainingSessionEditLog.created_at >= start_at)
    if end_at is not None:
        query = query.filter(TrainingSessionEditLog.created_at <= end_at)

    items: list[LogItemRead] = []
    for log, session, athlete, team, session_item, exercise in query.all():
        items.append(
            LogItemRead(
                id=log.id,
                source_type="training_edit",
                action_type=log.action_type,
                object_type=log.object_type,
                object_id=log.object_id,
                object_label=_coalesce(
                    exercise.name if exercise else None,
                    athlete.full_name if athlete else None,
                    f"训练课 {session.id}" if session else None,
                ),
                summary=log.summary,
                actor_name=log.actor_name,
                occurred_at=log.edited_at or log.created_at,
                team_id=team.id if team else None,
                team_name=team.name if team else None,
                athlete_id=athlete.id if athlete else None,
                athlete_name=athlete.full_name if athlete else None,
                session_id=session.id if session else None,
                session_date=session.session_date if session else None,
                before_snapshot=log.before_snapshot,
                after_snapshot=log.after_snapshot,
                extra_context={
                    "session_item_id": session_item.id if session_item else None,
                    "exercise_name": exercise.name if exercise else None,
                },
            )
        )
    return items


def _list_sync_issue_logs(db: Session, *, start_at: datetime | None, end_at: datetime | None) -> list[LogItemRead]:
    query = (
        db.query(TrainingSyncIssue, Athlete, Team)
        .join(Athlete, Athlete.id == TrainingSyncIssue.athlete_id)
        .outerjoin(Team, Team.id == Athlete.team_id)
        .order_by(TrainingSyncIssue.created_at.desc(), TrainingSyncIssue.id.desc())
    )
    if start_at is not None:
        query = query.filter(TrainingSyncIssue.created_at >= start_at)
    if end_at is not None:
        query = query.filter(TrainingSyncIssue.created_at <= end_at)

    items: list[LogItemRead] = []
    for issue, athlete, team in query.all():
        items.append(
            LogItemRead(
                id=issue.id,
                source_type="sync_issue",
                action_type="sync_issue",
                object_type="sync_issue",
                object_id=issue.session_id or issue.id,
                object_label=athlete.full_name,
                summary=issue.summary,
                actor_name=SYSTEM_ACTOR_NAME,
                occurred_at=issue.updated_at or issue.created_at,
                team_id=team.id if team else None,
                team_name=team.name if team else None,
                athlete_id=athlete.id,
                athlete_name=athlete.full_name,
                session_id=issue.session_id,
                session_date=issue.session_date,
                status=issue.issue_status,
                after_snapshot=issue.sync_payload if isinstance(issue.sync_payload, dict) else None,
                extra_context={
                    "failure_count": issue.failure_count,
                    "last_error": issue.last_error,
                    "session_key": issue.session_key,
                },
            )
        )
    return items


def _list_sync_conflict_logs(db: Session, *, start_at: datetime | None, end_at: datetime | None) -> list[LogItemRead]:
    query = (
        db.query(TrainingSyncConflict, Athlete, Team)
        .join(Athlete, Athlete.id == TrainingSyncConflict.athlete_id)
        .outerjoin(Team, Team.id == Athlete.team_id)
        .order_by(TrainingSyncConflict.created_at.desc(), TrainingSyncConflict.id.desc())
    )
    if start_at is not None:
        query = query.filter(TrainingSyncConflict.created_at >= start_at)
    if end_at is not None:
        query = query.filter(TrainingSyncConflict.created_at <= end_at)

    items: list[LogItemRead] = []
    for conflict, athlete, team in query.all():
        items.append(
            LogItemRead(
                id=conflict.id,
                source_type="sync_conflict",
                action_type=conflict.trigger_reason,
                object_type="sync_conflict",
                object_id=conflict.session_id or conflict.id,
                object_label=athlete.full_name,
                summary=conflict.summary,
                actor_name=SYSTEM_ACTOR_NAME,
                occurred_at=conflict.created_at,
                team_id=team.id if team else None,
                team_name=team.name if team else None,
                athlete_id=athlete.id,
                athlete_name=athlete.full_name,
                session_id=conflict.session_id,
                session_date=conflict.session_date,
                status=conflict.conflict_type,
                before_snapshot=conflict.remote_snapshot if isinstance(conflict.remote_snapshot, dict) else None,
                after_snapshot=conflict.local_snapshot if isinstance(conflict.local_snapshot, dict) else None,
                extra_context={"trigger_reason": conflict.trigger_reason},
            )
        )
    return items


def _list_dangerous_operation_logs(db: Session, *, start_at: datetime | None, end_at: datetime | None) -> list[LogItemRead]:
    query = db.query(DangerousOperationLog).order_by(DangerousOperationLog.created_at.desc(), DangerousOperationLog.id.desc())
    if start_at is not None:
        query = query.filter(DangerousOperationLog.created_at >= start_at)
    if end_at is not None:
        query = query.filter(DangerousOperationLog.created_at <= end_at)

    items: list[LogItemRead] = []
    for log in query.all():
        context = _resolve_dangerous_operation_context(db, log)
        items.append(
            LogItemRead(
                id=log.id,
                source_type="dangerous_operation",
                action_type=log.operation_key,
                object_type=log.object_type,
                object_id=log.object_id,
                object_label=_coalesce(
                    context.get("object_label"),
                    _extract_object_label_from_scope(log),
                    f"{log.object_type}#{log.object_id}" if log.object_id else log.object_type,
                ),
                summary=log.summary,
                actor_name=log.actor_name,
                occurred_at=log.created_at,
                team_id=context.get("team_id"),
                team_name=context.get("team_name"),
                athlete_id=context.get("athlete_id"),
                athlete_name=context.get("athlete_name"),
                session_id=context.get("session_id"),
                session_date=context.get("session_date"),
                status=log.status,
                after_snapshot=log.impact_scope if isinstance(log.impact_scope, dict) else None,
                extra_context=log.extra_data if isinstance(log.extra_data, dict) else None,
            )
        )
    return items


def _apply_visibility(db: Session, items: list[LogItemRead], current_user: User | None) -> list[LogItemRead]:
    if current_user is None:
        return items

    role_code = (current_user.role_code or "").strip().lower()
    if role_code == "admin":
        return items

    if role_code == "coach":
        sport_id = current_user.sport_id
        if sport_id is None:
            return [item for item in items if not _extract_item_team_ids(item)]

        team_ids = {
            team_id
            for (team_id,) in db.query(Team.id).filter(Team.sport_id == sport_id).all()
            if team_id is not None
        }

        def is_visible(item: LogItemRead) -> bool:
            scoped_team_ids = _extract_item_team_ids(item)
            if not scoped_team_ids:
                return True
            return bool(scoped_team_ids & team_ids)

        return [item for item in items if is_visible(item)]

    return [item for item in items if item.team_id is None]


def _extract_item_team_ids(item: LogItemRead) -> set[int]:
    scoped_team_ids: set[int] = set()
    if item.team_id is not None:
        scoped_team_ids.add(item.team_id)

    for payload in (item.before_snapshot, item.after_snapshot, item.extra_context):
        if not isinstance(payload, dict):
            continue
        _collect_team_ids(scoped_team_ids, payload.get("team_id"))
        _collect_team_ids(scoped_team_ids, payload.get("team_ids"))

    return scoped_team_ids


def _collect_team_ids(target: set[int], value) -> None:
    if value is None:
        return
    if isinstance(value, list):
        for entry in value:
            _collect_team_ids(target, entry)
        return
    if isinstance(value, bool):
        return
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return
    if normalized > 0:
        target.add(normalized)


def _resolve_dangerous_operation_context(db: Session, log: DangerousOperationLog) -> dict:
    impact_scope = log.impact_scope if isinstance(log.impact_scope, dict) else {}
    context = {
        "team_id": impact_scope.get("team_id"),
        "team_name": impact_scope.get("team_name"),
        "athlete_id": impact_scope.get("athlete_id"),
        "athlete_name": impact_scope.get("athlete_name"),
        "session_id": impact_scope.get("session_id"),
        "session_date": impact_scope.get("session_date"),
        "object_label": impact_scope.get("template_name")
        or impact_scope.get("exercise_name")
        or impact_scope.get("batch_name"),
    }
    if context["team_name"] is None and isinstance(impact_scope.get("team_names"), list):
        context["team_name"] = "、".join(str(value) for value in impact_scope["team_names"] if value) or None
    if context["athlete_name"] is None and isinstance(impact_scope.get("athletes"), list):
        context["athlete_name"] = "、".join(str(value) for value in impact_scope["athletes"][:3] if value) or None

    if context["team_id"] is not None and not context["team_name"]:
        team = db.query(Team).filter(Team.id == context["team_id"]).first()
        context["team_name"] = team.name if team else None

    if log.object_type == "set_record":
        session_id = impact_scope.get("session_id")
        if session_id:
            row = (
                db.query(TrainingSession, Athlete, Team)
                .join(Athlete, Athlete.id == TrainingSession.athlete_id)
                .outerjoin(Team, Team.id == Athlete.team_id)
                .filter(TrainingSession.id == session_id)
                .first()
            )
            if row:
                session, athlete, team = row
                context.update(
                    {
                        "team_id": team.id if team else context["team_id"],
                        "team_name": team.name if team else context["team_name"],
                        "athlete_id": athlete.id,
                        "athlete_name": athlete.full_name,
                        "session_id": session.id,
                        "session_date": session.session_date,
                    }
                )
        return context

    if log.object_type == "training_plan_template":
        if log.object_id is None:
            return context
        row = (
            db.query(TrainingPlanTemplate, Team)
            .outerjoin(Team, Team.id == TrainingPlanTemplate.team_id)
            .filter(TrainingPlanTemplate.id == log.object_id)
            .first()
        )
        if row:
            template, team = row
            context.update(
                {
                    "team_id": team.id if team else context["team_id"],
                    "team_name": team.name if team else context["team_name"],
                    "object_label": template.name,
                }
            )
        return context

    if log.object_type == "training_plan_template_item":
        item_id = log.object_id
        if item_id:
            row = (
                db.query(TrainingPlanTemplateItem, TrainingPlanTemplate, Team, Exercise)
                .join(TrainingPlanTemplate, TrainingPlanTemplate.id == TrainingPlanTemplateItem.template_id)
                .outerjoin(Team, Team.id == TrainingPlanTemplate.team_id)
                .outerjoin(Exercise, Exercise.id == TrainingPlanTemplateItem.exercise_id)
                .filter(TrainingPlanTemplateItem.id == item_id)
                .first()
            )
            if row:
                item, template, team, exercise = row
                context.update(
                    {
                        "team_id": team.id if team else context["team_id"],
                        "team_name": team.name if team else context["team_name"],
                        "object_label": f"{template.name} / {exercise.name if exercise else item.exercise_id}",
                    }
                )
                return context

        template_id = impact_scope.get("template_id")
        if template_id:
            row = (
                db.query(TrainingPlanTemplate, Team)
                .outerjoin(Team, Team.id == TrainingPlanTemplate.team_id)
                .filter(TrainingPlanTemplate.id == template_id)
                .first()
            )
            if row:
                template, team = row
                context.update(
                    {
                        "team_id": team.id if team else context["team_id"],
                        "team_name": team.name if team else context["team_name"],
                        "object_label": context["object_label"] or template.name,
                    }
                )
        return context

    return context


def _extract_object_label_from_scope(log: DangerousOperationLog) -> str | None:
    if not isinstance(log.impact_scope, dict):
        return None
    for key in ("restore_scope_label", "template_name", "exercise_name", "restored_from", "backup_name", "batch_name"):
        value = log.impact_scope.get(key)
        if value:
            return str(value)
    if isinstance(log.impact_scope.get("athletes"), list) and log.impact_scope["athletes"]:
        return "、".join(str(value) for value in log.impact_scope["athletes"][:3] if value)
    return None


def _build_datetime_range(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    start_at = datetime.combine(date_from, time.min) if date_from is not None else None
    end_at = datetime.combine(date_to, time.max) if date_to is not None else None
    return start_at, end_at


def _coalesce(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None
