from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import (
    Athlete,
    AthletePlanAssignment,
    SetRecord,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingSession,
    TrainingSessionItem,
    TrainingSyncIssue,
)
from app.services import session_service


FINAL_SESSION_STATUSES = {"completed", "partial_complete", "absent"}


def get_today_monitoring(
    db: Session,
    session_date: date,
    team_id: int | None = None,
    include_unassigned: bool = True,
) -> dict:
    """Build the first read-only monitoring board payload for one training date."""
    session_service.close_due_sessions(db)

    all_active_athletes = _list_active_athletes(db)
    visible_athletes = _filter_athletes(all_active_athletes, team_id, include_unassigned)
    athlete_ids = [athlete.id for athlete in visible_athletes]
    assignments_by_athlete = _get_active_assignments_by_athlete(db, athlete_ids, session_date)
    sessions_by_assignment = _get_sessions_by_assignment(db, assignments_by_athlete, session_date)
    sync_issues_by_athlete = _get_sync_issues_by_athlete(db, athlete_ids, session_date)

    return {
        "session_date": session_date,
        "updated_at": datetime.now(timezone.utc),
        "teams": _build_team_options(all_active_athletes),
        "athletes": [
            _build_athlete_card(
                athlete=athlete,
                assignments=assignments_by_athlete.get(athlete.id, []),
                sessions_by_assignment=sessions_by_assignment,
                sync_issues=sync_issues_by_athlete.get(athlete.id, []),
            )
            for athlete in visible_athletes
        ],
    }


def get_athlete_monitoring_detail(
    db: Session,
    session_date: date,
    athlete_id: int,
) -> dict:
    """Build a read-only training detail payload for one athlete on one date."""
    session_service.close_due_sessions(db)

    athlete = (
        db.query(Athlete)
        .options(joinedload(Athlete.team))
        .filter(Athlete.id == athlete_id, Athlete.is_active.is_(True))
        .first()
    )
    if not athlete:
        raise not_found("Athlete not found")

    assignments_by_athlete = _get_active_assignments_by_athlete(db, [athlete_id], session_date)
    assignments = assignments_by_athlete.get(athlete_id, [])
    sessions_by_assignment = _get_sessions_by_assignment(db, assignments_by_athlete, session_date)
    sync_issues = _get_sync_issues_by_athlete(db, [athlete_id], session_date).get(athlete_id, [])
    athlete_card = _build_athlete_card(
        athlete=athlete,
        assignments=assignments,
        sessions_by_assignment=sessions_by_assignment,
        sync_issues=sync_issues,
    )

    return {
        "session_date": session_date,
        "updated_at": datetime.now(timezone.utc),
        "athlete_id": athlete.id,
        "athlete_name": athlete.full_name,
        "team_id": athlete.team_id,
        "team_name": athlete.team.name if athlete.team else None,
        "session_status": athlete_card["session_status"],
        "sync_status": athlete_card["sync_status"],
        "has_alert": athlete_card["has_alert"],
        "assignments": [
            _build_assignment_detail(assignment, sessions_by_assignment.get(assignment.id))
            for assignment in assignments
        ],
    }


def _list_active_athletes(db: Session) -> list[Athlete]:
    return (
        db.query(Athlete)
        .options(joinedload(Athlete.team))
        .filter(Athlete.is_active.is_(True))
        .order_by(Athlete.full_name.asc(), Athlete.id.asc())
        .all()
    )


def _filter_athletes(
    athletes: list[Athlete],
    team_id: int | None,
    include_unassigned: bool,
) -> list[Athlete]:
    if team_id is not None:
        return [athlete for athlete in athletes if athlete.team_id == team_id]
    if include_unassigned:
        return athletes
    return [athlete for athlete in athletes if athlete.team_id is not None]


def _build_team_options(athletes: list[Athlete]) -> list[dict]:
    team_counts: dict[int | None, dict] = {}
    for athlete in athletes:
        option = team_counts.setdefault(
            athlete.team_id,
            {
                "team_id": athlete.team_id,
                "team_name": athlete.team.name if athlete.team else "未分队",
                "athlete_count": 0,
            },
        )
        option["athlete_count"] += 1

    return sorted(
        team_counts.values(),
        key=lambda item: (item["team_id"] is None, item["team_name"]),
    )


def _get_active_assignments_by_athlete(
    db: Session,
    athlete_ids: list[int],
    session_date: date,
) -> dict[int, list[AthletePlanAssignment]]:
    if not athlete_ids:
        return {}

    assignments = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.overrides),
            joinedload(AthletePlanAssignment.template)
            .joinedload(TrainingPlanTemplate.items)
            .joinedload(TrainingPlanTemplateItem.exercise),
        )
        .filter(
            AthletePlanAssignment.athlete_id.in_(athlete_ids),
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.start_date <= session_date,
            AthletePlanAssignment.end_date >= session_date,
        )
        .order_by(
            AthletePlanAssignment.athlete_id.asc(),
            AthletePlanAssignment.assigned_date.desc(),
            AthletePlanAssignment.id.desc(),
        )
        .all()
    )

    grouped: dict[int, list[AthletePlanAssignment]] = defaultdict(list)
    for assignment in assignments:
        grouped[assignment.athlete_id].append(assignment)
    return grouped


def _get_sessions_by_assignment(
    db: Session,
    assignments_by_athlete: dict[int, list[AthletePlanAssignment]],
    session_date: date,
) -> dict[int, TrainingSession]:
    assignment_ids = [
        assignment.id
        for assignments in assignments_by_athlete.values()
        for assignment in assignments
    ]
    if not assignment_ids:
        return {}

    sessions = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
        )
        .filter(
            TrainingSession.assignment_id.in_(assignment_ids),
            TrainingSession.session_date == session_date,
        )
        .all()
    )
    return {session.assignment_id: session for session in sessions}


def _get_sync_issues_by_athlete(
    db: Session,
    athlete_ids: list[int],
    session_date: date,
) -> dict[int, list[TrainingSyncIssue]]:
    if not athlete_ids:
        return {}

    issues = (
        db.query(TrainingSyncIssue)
        .filter(
            TrainingSyncIssue.athlete_id.in_(athlete_ids),
            TrainingSyncIssue.session_date == session_date,
            TrainingSyncIssue.issue_status == "manual_retry_required",
        )
        .order_by(TrainingSyncIssue.updated_at.desc(), TrainingSyncIssue.id.desc())
        .all()
    )

    grouped: dict[int, list[TrainingSyncIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.athlete_id].append(issue)
    return grouped


def _build_athlete_card(
    athlete: Athlete,
    assignments: list[AthletePlanAssignment],
    sessions_by_assignment: dict[int, TrainingSession],
    sync_issues: list[TrainingSyncIssue],
) -> dict:
    sessions = [sessions_by_assignment[assignment.id] for assignment in assignments if assignment.id in sessions_by_assignment]
    latest_record = _find_latest_record(sessions)
    totals = _build_progress_totals(assignments, sessions_by_assignment)
    session_status = _resolve_athlete_status(assignments, sessions_by_assignment, totals)
    primary_session = _choose_primary_session(sessions)

    return {
        "athlete_id": athlete.id,
        "athlete_name": athlete.full_name,
        "team_id": athlete.team_id,
        "team_name": athlete.team.name if athlete.team else None,
        "session_id": primary_session.id if primary_session else None,
        "session_status": session_status,
        "sync_status": "manual_retry_required" if sync_issues else "synced",
        "current_exercise_name": _resolve_current_exercise(
            assignments,
            sessions_by_assignment,
            primary_session,
            latest_record,
        ),
        "completed_items": totals["completed_items"],
        "total_items": totals["total_items"],
        "completed_sets": totals["completed_sets"],
        "total_sets": totals["total_sets"],
        "latest_set": _serialize_latest_record(latest_record),
        "has_alert": bool(sync_issues) or session_status in {"partial_complete", "absent"},
    }


def _resolve_athlete_status(
    assignments: list[AthletePlanAssignment],
    sessions_by_assignment: dict[int, TrainingSession],
    totals: dict[str, int],
) -> str:
    if not assignments:
        return "no_plan"

    assignment_ids = {assignment.id for assignment in assignments}
    sessions = [
        sessions_by_assignment[assignment_id]
        for assignment_id in assignment_ids
        if assignment_id in sessions_by_assignment
    ]
    if not sessions:
        return "not_started"

    statuses = [_resolve_single_session_status(session) for session in sessions]

    if len(sessions) == len(assignments) and statuses and all(status == "absent" for status in statuses):
        return "absent"

    if any(status == "partial_complete" for status in statuses):
        return "partial_complete"

    if totals["completed_sets"] == 0:
        return "not_started"

    if _all_assignments_completed(assignments, sessions_by_assignment):
        return "completed"

    return "in_progress"


def _all_assignments_completed(
    assignments: list[AthletePlanAssignment],
    sessions_by_assignment: dict[int, TrainingSession],
) -> bool:
    if not assignments:
        return False

    for assignment in assignments:
        session = sessions_by_assignment.get(assignment.id)
        if not session or not _session_is_fully_completed(session):
            return False
    return True


def _choose_primary_session(sessions: list[TrainingSession]) -> TrainingSession | None:
    if not sessions:
        return None

    priority = {
        "in_progress": 0,
        "partial_complete": 1,
        "not_started": 2,
        "completed": 3,
        "absent": 4,
    }
    return sorted(
        sessions,
        key=lambda session: (
            priority.get(_resolve_single_session_status(session), 9),
            -(session.updated_at.timestamp() if session.updated_at else 0),
            -session.id,
        ),
    )[0]


def _resolve_single_session_status(session: TrainingSession) -> str:
    if session.status in FINAL_SESSION_STATUSES:
        return session.status
    if _session_is_fully_completed(session):
        return "completed"
    if _session_has_recorded_sets(session):
        return "in_progress"
    return "not_started"


def _session_has_recorded_sets(session: TrainingSession) -> bool:
    return any(item.records for item in session.items)


def _session_is_fully_completed(session: TrainingSession) -> bool:
    if not session.items:
        return False
    if sum(item.prescribed_sets for item in session.items) <= 0:
        return False
    return all(len(item.records) >= item.prescribed_sets for item in session.items)


def _build_progress_totals(
    assignments: list[AthletePlanAssignment],
    sessions_by_assignment: dict[int, TrainingSession],
) -> dict[str, int]:
    totals = {
        "completed_items": 0,
        "total_items": 0,
        "completed_sets": 0,
        "total_sets": 0,
    }

    for assignment in assignments:
        session = sessions_by_assignment.get(assignment.id)
        if session:
            items = session.items
            totals["completed_items"] += sum(1 for item in items if len(item.records) >= item.prescribed_sets)
            totals["total_items"] += len(items)
            totals["completed_sets"] += sum(len(item.records) for item in items)
            totals["total_sets"] += sum(item.prescribed_sets for item in items)
            continue

        template_items = assignment.template.items if assignment.template else []
        totals["total_items"] += len(template_items)
        totals["total_sets"] += sum(item.prescribed_sets for item in template_items)

    return totals


def _build_assignment_detail(
    assignment: AthletePlanAssignment,
    session: TrainingSession | None,
) -> dict:
    if session:
        exercises = [_serialize_session_item_detail(item) for item in session.items]
        return {
            "assignment_id": assignment.id,
            "template_id": assignment.template_id,
            "template_name": assignment.template.name if assignment.template else "未命名训练计划",
            "session_id": session.id,
            "session_status": _resolve_single_session_status(session),
            "completed_items": sum(1 for item in session.items if len(item.records) >= item.prescribed_sets),
            "total_items": len(session.items),
            "completed_sets": sum(len(item.records) for item in session.items),
            "total_sets": sum(item.prescribed_sets for item in session.items),
            "exercises": exercises,
        }

    template_items = assignment.template.items if assignment.template else []
    exercises = [_serialize_template_item_detail(assignment, item) for item in template_items]
    return {
        "assignment_id": assignment.id,
        "template_id": assignment.template_id,
        "template_name": assignment.template.name if assignment.template else "未命名训练计划",
        "session_id": None,
        "session_status": "not_started",
        "completed_items": 0,
        "total_items": len(template_items),
        "completed_sets": 0,
        "total_sets": sum(item.prescribed_sets for item in template_items),
        "exercises": exercises,
    }


def _serialize_session_item_detail(item: TrainingSessionItem) -> dict:
    ordered_records = sorted(item.records, key=lambda record: (record.set_number, record.completed_at, record.id))
    return {
        "item_id": item.id,
        "exercise_id": item.exercise_id,
        "exercise_name": item.exercise.name if item.exercise else "未命名动作",
        "sort_order": item.sort_order,
        "prescribed_sets": item.prescribed_sets,
        "prescribed_reps": item.prescribed_reps,
        "target_weight": item.initial_load,
        "target_note": item.target_note,
        "is_main_lift": item.is_main_lift,
        "status": item.status,
        "completed_sets": len(ordered_records),
        "records": [_serialize_set_record_detail(record) for record in ordered_records],
    }


def _serialize_template_item_detail(
    assignment: AthletePlanAssignment,
    item: TrainingPlanTemplateItem,
) -> dict:
    override_map = {override.template_item_id: override.initial_load_override for override in assignment.overrides}
    return {
        "item_id": None,
        "exercise_id": item.exercise_id,
        "exercise_name": item.exercise.name if item.exercise else "未命名动作",
        "sort_order": item.sort_order,
        "prescribed_sets": item.prescribed_sets,
        "prescribed_reps": item.prescribed_reps,
        "target_weight": override_map.get(item.id, item.initial_load_value),
        "target_note": item.target_note,
        "is_main_lift": item.is_main_lift,
        "status": "pending",
        "completed_sets": 0,
        "records": [],
    }


def _serialize_set_record_detail(record: SetRecord) -> dict:
    return {
        "id": record.id,
        "set_number": record.set_number,
        "target_weight": record.target_weight,
        "target_reps": record.target_reps,
        "actual_weight": record.actual_weight,
        "actual_reps": record.actual_reps,
        "actual_rir": record.actual_rir,
        "completed_at": record.completed_at,
        "notes": record.notes,
    }


def _find_latest_record(sessions: list[TrainingSession]) -> SetRecord | None:
    records = [record for session in sessions for item in session.items for record in item.records]
    if not records:
        return None
    return max(records, key=lambda record: (record.completed_at, record.id))


def _resolve_current_exercise(
    assignments: list[AthletePlanAssignment],
    sessions_by_assignment: dict[int, TrainingSession],
    primary_session: TrainingSession | None,
    latest_record: SetRecord | None,
) -> str | None:
    if primary_session:
        pending_item = next((item for item in primary_session.items if item.status != "completed"), None)
        if pending_item:
            return pending_item.exercise.name if pending_item.exercise else "未命名动作"
        if latest_record and latest_record.session_item.exercise:
            return latest_record.session_item.exercise.name
        last_item = primary_session.items[-1] if primary_session.items else None
        return last_item.exercise.name if last_item and last_item.exercise else None

    for assignment in assignments:
        if assignment.id in sessions_by_assignment:
            continue
        template_items = assignment.template.items if assignment.template else []
        first_item = template_items[0] if template_items else None
        if first_item:
            return first_item.exercise.name if first_item.exercise else "未命名动作"
    return None


def _serialize_latest_record(record: SetRecord | None) -> dict | None:
    if not record:
        return None
    return {
        "actual_weight": record.actual_weight,
        "actual_reps": record.actual_reps,
        "actual_rir": record.actual_rir,
        "completed_at": record.completed_at,
    }
