from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import Athlete, AthletePlanAssignment, SetRecord, TrainingSession, TrainingSessionItem
from app.schemas.training_session import SetRecordCreate, SetRecordUpdate
from app.services import athlete_service
from app.services.assignment_service import get_active_assignment_for_date, get_assignment, list_active_assignments_for_date
from app.services.progression_service import compute_next_weight


def get_or_create_today_session(db: Session, athlete_id: int, session_date: date) -> TrainingSession:
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise not_found("Athlete not found")

    assignment = get_active_assignment_for_date(db, athlete_id, session_date)
    if not assignment:
        raise not_found("No active plan for the selected date")

    return get_or_create_session_for_assignment(db, assignment.id, session_date)


def list_training_athletes(db: Session, session_date: date) -> list[Athlete]:
    athletes = athlete_service.list_athletes(db)
    athlete_ids = [athlete.id for athlete in athletes if athlete.is_active]
    status_map = _get_athlete_training_status_map(db, athlete_ids, session_date)
    assignments_by_athlete = _get_active_assignments_by_athlete(db, athlete_ids, session_date)
    for athlete in athletes:
        athlete.training_status = status_map.get(athlete.id, "no_plan")
        athlete.assignments = assignments_by_athlete.get(athlete.id, [])
    return athletes


def list_training_plans(db: Session, athlete_id: int, session_date: date):
    athlete = athlete_service.get_athlete(db, athlete_id)
    assignments = list_active_assignments_for_date(db, athlete_id, session_date)
    assignment_status_map = _get_assignment_training_status_map(db, [assignment.id for assignment in assignments], session_date)
    for assignment in assignments:
        assignment.training_status = assignment_status_map.get(assignment.id, "not_started")
    return athlete, assignments


def get_or_create_session_for_assignment(db: Session, assignment_id: int, session_date: date) -> TrainingSession:
    assignment = get_assignment(db, assignment_id)

    existing = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
        )
        .filter(TrainingSession.assignment_id == assignment.id, TrainingSession.session_date == session_date)
        .first()
    )
    if existing:
        _sync_session_state(existing)
        db.commit()
        return existing

    override_map = {override.template_item_id: override.initial_load_override for override in assignment.overrides}
    session = TrainingSession(
        athlete_id=assignment.athlete_id,
        assignment_id=assignment.id,
        template_id=assignment.template_id,
        session_date=session_date,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()

    for template_item in assignment.template.items:
        initial_load = override_map.get(template_item.id, template_item.initial_load_value)
        db.add(
            TrainingSessionItem(
                session_id=session.id,
                template_item_id=template_item.id,
                exercise_id=template_item.exercise_id,
                sort_order=template_item.sort_order,
                prescribed_sets=template_item.prescribed_sets,
                prescribed_reps=template_item.prescribed_reps,
                target_note=template_item.target_note,
                is_main_lift=template_item.is_main_lift,
                enable_auto_load=template_item.enable_auto_load,
                initial_load=initial_load,
                status="pending",
            )
        )

    db.commit()
    return get_session(db, session.id)


def get_session(db: Session, session_id: int) -> TrainingSession:
    session = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
        )
        .filter(TrainingSession.id == session_id)
        .first()
    )
    if not session:
        raise not_found("Training session not found")
    _sync_session_state(session)
    db.commit()
    return session


def submit_set_record(db: Session, item_id: int, payload: SetRecordCreate):
    item = _get_session_item(db, item_id)
    next_set_number = len(item.records) + 1
    if next_set_number > item.prescribed_sets:
        raise bad_request("All prescribed sets are already completed")

    final_weight = payload.final_weight if payload.final_weight is not None else payload.actual_weight
    record = SetRecord(
        set_number=next_set_number,
        target_weight=item.initial_load if next_set_number == 1 else item.records[-1].final_weight,
        target_reps=item.prescribed_reps,
        actual_weight=payload.actual_weight,
        actual_reps=payload.actual_reps,
        actual_rir=payload.actual_rir,
        suggestion_weight=None,
        suggestion_reason=None,
        user_decision="accepted",
        final_weight=final_weight,
        completed_at=datetime.now(timezone.utc),
        notes=payload.notes,
    )
    item.records.append(record)
    db.flush()
    _recompute_item_records(item)
    _recompute_session_status(item.session)
    db.commit()

    refreshed_item = _get_session_item(db, item_id)
    refreshed_record = db.query(SetRecord).filter(SetRecord.id == record.id).first()
    refreshed_session = get_session(db, item.session_id)
    return refreshed_record, _get_next_suggestion(refreshed_item), refreshed_item, refreshed_session


def update_set_record(db: Session, record_id: int, payload: SetRecordUpdate):
    record = (
        db.query(SetRecord)
        .options(
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.exercise),
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.records),
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.session),
        )
        .filter(SetRecord.id == record_id)
        .first()
    )
    if not record:
        raise not_found("Set record not found")

    record.actual_weight = payload.actual_weight
    record.actual_reps = payload.actual_reps
    record.actual_rir = payload.actual_rir
    record.final_weight = payload.final_weight if payload.final_weight is not None else payload.actual_weight
    record.notes = payload.notes
    _recompute_item_records(record.session_item)
    _recompute_session_status(record.session_item.session)
    db.commit()

    refreshed_item = _get_session_item(db, record.session_item_id)
    refreshed_record = db.query(SetRecord).filter(SetRecord.id == record_id).first()
    refreshed_session = get_session(db, record.session_item.session_id)
    return refreshed_record, _get_next_suggestion(refreshed_item), refreshed_item, refreshed_session


def complete_session_item(db: Session, item_id: int) -> TrainingSessionItem:
    item = _get_session_item(db, item_id)
    item.status = "completed"
    _recompute_session_status(item.session)
    db.commit()
    return _get_session_item(db, item_id)


def complete_session(db: Session, session_id: int) -> TrainingSession:
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise not_found("Training session not found")
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    return get_session(db, session_id)


def _get_session_item(db: Session, item_id: int) -> TrainingSessionItem:
    item = (
        db.query(TrainingSessionItem)
        .options(
            joinedload(TrainingSessionItem.exercise),
            joinedload(TrainingSessionItem.records),
            joinedload(TrainingSessionItem.session),
        )
        .filter(TrainingSessionItem.id == item_id)
        .first()
    )
    if not item:
        raise not_found("Training item not found")
    return item


def _recompute_item_records(item: TrainingSessionItem) -> None:
    ordered_records = sorted(item.records, key=lambda current: current.set_number)
    for index, record in enumerate(ordered_records):
        previous_records = ordered_records[:index]
        previous_two_rirs = [previous.actual_rir for previous in previous_records[-2:]]
        expected_weight = item.initial_load if not previous_records else previous_records[-1].suggestion_weight
        target_weight = item.initial_load if index == 0 else previous_records[-1].final_weight
        suggestion = compute_next_weight(
            current_weight=record.final_weight,
            target_reps=item.prescribed_reps,
            actual_reps=record.actual_reps,
            actual_rir=record.actual_rir,
            load_profile=item.exercise.load_profile,
            default_increment=item.exercise.default_increment,
            previous_rirs=previous_two_rirs,
        )
        record.target_weight = target_weight
        record.target_reps = item.prescribed_reps
        record.suggestion_weight = suggestion.suggestion_weight
        record.suggestion_reason = suggestion.reason_text
        if expected_weight is None:
            record.user_decision = "modified"
        else:
            record.user_decision = "accepted" if abs(record.final_weight - expected_weight) < 0.001 else "modified"

    if not ordered_records:
        item.status = "pending"
    elif len(ordered_records) >= item.prescribed_sets:
        item.status = "completed"
    else:
        item.status = "in_progress"


def _recompute_session_status(session: TrainingSession) -> None:
    items = list(session.items)
    if not items:
        session.status = "pending"
        session.completed_at = None
        return

    if all(item.status == "completed" for item in items):
        session.status = "completed"
        session.completed_at = session.completed_at or datetime.now(timezone.utc)
        return

    session.status = "in_progress"
    session.completed_at = None


def _sync_session_state(session: TrainingSession) -> None:
    for item in session.items:
        _recompute_item_records(item)
    _recompute_session_status(session)


def _get_next_suggestion(item: TrainingSessionItem):
    if item.status == "completed" or not item.records:
        return None

    latest_record = item.records[-1]
    return {
        "suggestion_weight": latest_record.suggestion_weight,
        "decision_hint": latest_record.user_decision,
        "reason_code": "updated_record",
        "reason_text": latest_record.suggestion_reason or "Continue with the latest training response.",
        "should_deload": False,
        "should_stop_progression": False,
    }


def _get_assignment_training_status_map(db: Session, assignment_ids: list[int], session_date: date) -> dict[int, str]:
    if not assignment_ids:
        return {}

    sessions = (
        db.query(TrainingSession)
        .options(joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records))
        .filter(TrainingSession.assignment_id.in_(assignment_ids), TrainingSession.session_date == session_date)
        .all()
    )
    session_map = {session.assignment_id: session for session in sessions}
    status_map: dict[int, str] = {}
    for assignment_id in assignment_ids:
        session = session_map.get(assignment_id)
        if not session:
            status_map[assignment_id] = "not_started"
            continue

        completed_sets = sum(len(item.records) for item in session.items)
        if session.status == "completed":
            status_map[assignment_id] = "completed"
        elif completed_sets > 0:
            status_map[assignment_id] = "in_progress"
        else:
            status_map[assignment_id] = "not_started"
    return status_map


def _get_active_assignments_by_athlete(db: Session, athlete_ids: list[int], session_date: date) -> dict[int, list[AthletePlanAssignment]]:
    if not athlete_ids:
        return {}

    assignments = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.template),
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(
            AthletePlanAssignment.athlete_id.in_(athlete_ids),
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.start_date <= session_date,
            AthletePlanAssignment.end_date >= session_date,
        )
        .order_by(AthletePlanAssignment.athlete_id.asc(), AthletePlanAssignment.assigned_date.desc(), AthletePlanAssignment.id.desc())
        .all()
    )

    assignment_status_map = _get_assignment_training_status_map(db, [assignment.id for assignment in assignments], session_date)
    assignments_by_athlete: dict[int, list[AthletePlanAssignment]] = {athlete_id: [] for athlete_id in athlete_ids}
    for assignment in assignments:
        assignment.training_status = assignment_status_map.get(assignment.id, "not_started")
        assignments_by_athlete.setdefault(assignment.athlete_id, []).append(assignment)
    return assignments_by_athlete


def _get_athlete_training_status_map(db: Session, athlete_ids: list[int], session_date: date) -> dict[int, str]:
    if not athlete_ids:
        return {}

    assignments = (
        db.query(AthletePlanAssignment)
        .filter(
            AthletePlanAssignment.athlete_id.in_(athlete_ids),
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.start_date <= session_date,
            AthletePlanAssignment.end_date >= session_date,
        )
        .all()
    )
    assignments_by_athlete: dict[int, list[int]] = {athlete_id: [] for athlete_id in athlete_ids}
    for assignment in assignments:
        assignments_by_athlete.setdefault(assignment.athlete_id, []).append(assignment.id)

    assignment_status_map = _get_assignment_training_status_map(db, [assignment.id for assignment in assignments], session_date)
    athlete_status_map: dict[int, str] = {}
    for athlete_id in athlete_ids:
        assignment_ids = assignments_by_athlete.get(athlete_id, [])
        if not assignment_ids:
            athlete_status_map[athlete_id] = "no_plan"
            continue

        statuses = [assignment_status_map.get(assignment_id, "not_started") for assignment_id in assignment_ids]
        if all(status == "completed" for status in statuses):
            athlete_status_map[athlete_id] = "completed"
        elif any(status in {"completed", "in_progress"} for status in statuses):
            athlete_status_map[athlete_id] = "in_progress"
        else:
            athlete_status_map[athlete_id] = "not_started"
    return athlete_status_map
