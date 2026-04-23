from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import Athlete, AthletePlanAssignment, SetRecord, TrainingSession, TrainingSessionItem, TrainingSyncConflict
from app.schemas.training_session import (
    SessionFullSyncPayload,
    SessionSetSyncOperation,
    SetRecordCreate,
    SetRecordUpdate,
)
from app.services import athlete_service
from app.services.assignment_service import get_active_assignment_for_date, get_assignment, list_active_assignments_for_date
from app.services.progression_service import compute_next_weight

NOT_STARTED_SESSION_STATUS = "not_started"
FINAL_SESSION_STATUSES = {"completed", "absent", "partial_complete"}


def get_or_create_today_session(db: Session, athlete_id: int, session_date: date) -> TrainingSession:
    close_due_sessions(db)
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise not_found("Athlete not found")

    assignment = get_active_assignment_for_date(db, athlete_id, session_date)
    if not assignment:
        raise not_found("No active plan for the selected date")

    return open_session_for_assignment(db, assignment.id, session_date)


def list_training_athletes(db: Session, session_date: date) -> list[Athlete]:
    close_due_sessions(db)
    athletes = athlete_service.list_athletes(db)
    athlete_ids = [athlete.id for athlete in athletes if athlete.is_active]
    status_map = _get_athlete_training_status_map(db, athlete_ids, session_date)
    assignments_by_athlete = _get_active_assignments_by_athlete(db, athlete_ids, session_date)
    for athlete in athletes:
        athlete.training_status = status_map.get(athlete.id, "no_plan")
        athlete.assignments = assignments_by_athlete.get(athlete.id, [])
    return athletes


def list_training_plans(db: Session, athlete_id: int, session_date: date):
    close_due_sessions(db)
    athlete = athlete_service.get_athlete(db, athlete_id)
    assignments = list_active_assignments_for_date(db, athlete_id, session_date)
    assignment_status_map = _get_assignment_training_status_map(db, [assignment.id for assignment in assignments], session_date)
    for assignment in assignments:
        assignment.training_status = assignment_status_map.get(assignment.id, "not_started")
    return athlete, assignments


def open_session_for_assignment(db: Session, assignment_id: int, session_date: date):
    assignment = get_assignment(db, assignment_id)
    existing = _find_session_by_assignment_and_date(db, assignment.id, session_date)
    if existing:
        _sync_session_state(existing)
        db.commit()
        return existing
    return _build_session_preview(assignment, session_date)


def get_or_create_session_for_assignment(db: Session, assignment_id: int, session_date: date) -> TrainingSession:
    assignment = get_assignment(db, assignment_id)
    return _ensure_session_for_assignment(db, assignment, session_date)


def _find_session_by_assignment_and_date(db: Session, assignment_id: int, session_date: date) -> TrainingSession | None:
    return (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
        )
        .filter(TrainingSession.assignment_id == assignment_id, TrainingSession.session_date == session_date)
        .first()
    )


def _ensure_session_for_assignment(db: Session, assignment, session_date: date) -> TrainingSession:
    existing = _find_session_by_assignment_and_date(db, assignment.id, session_date)
    if existing:
        _sync_session_state(existing)
        db.commit()
        return existing

    session = _prepare_session_for_assignment(db, assignment, session_date)
    db.commit()
    return get_session(db, session.id)


def _prepare_session_for_assignment(db: Session, assignment, session_date: date) -> TrainingSession:
    session = TrainingSession(
        athlete_id=assignment.athlete_id,
        assignment_id=assignment.id,
        template_id=assignment.template_id,
        session_date=session_date,
        status=NOT_STARTED_SESSION_STATUS,
    )
    db.add(session)
    db.flush()

    for session_item in _build_session_items_from_assignment(assignment, session_id=session.id):
        session.items.append(session_item)

    db.flush()
    return session


def _build_session_preview(assignment, session_date: date) -> dict:
    override_map = {override.template_item_id: override.initial_load_override for override in assignment.overrides}
    return {
        "id": None,
        "athlete_id": assignment.athlete_id,
        "assignment_id": assignment.id,
        "template_id": assignment.template_id,
        "session_date": session_date,
        "status": NOT_STARTED_SESSION_STATUS,
        "updated_at": None,
        "started_at": None,
        "completed_at": None,
        "coach_note": None,
        "athlete_note": None,
        "items": [
            {
                "id": template_item.id,
                "template_item_id": template_item.id,
                "sort_order": template_item.sort_order,
                "prescribed_sets": template_item.prescribed_sets,
                "prescribed_reps": template_item.prescribed_reps,
                "target_note": template_item.target_note,
                "is_main_lift": template_item.is_main_lift,
                "enable_auto_load": template_item.enable_auto_load,
                "initial_load": override_map.get(template_item.id, template_item.initial_load_value),
                "status": "pending",
                "exercise": template_item.exercise,
                "records": [],
            }
            for template_item in assignment.template.items
        ],
    }


def _build_session_items_from_assignment(assignment, session_id: int) -> list[TrainingSessionItem]:
    override_map = {override.template_item_id: override.initial_load_override for override in assignment.overrides}
    return [
        TrainingSessionItem(
            session_id=session_id,
            template_item_id=template_item.id,
            exercise_id=template_item.exercise_id,
            sort_order=template_item.sort_order,
            prescribed_sets=template_item.prescribed_sets,
            prescribed_reps=template_item.prescribed_reps,
            target_note=template_item.target_note,
            is_main_lift=template_item.is_main_lift,
            enable_auto_load=template_item.enable_auto_load,
            initial_load=override_map.get(template_item.id, template_item.initial_load_value),
            status="pending",
        )
        for template_item in assignment.template.items
    ]


def get_session(db: Session, session_id: int) -> TrainingSession:
    close_due_sessions(db)
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
    item.session.started_at = item.session.started_at or record.completed_at
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


def sync_session_operation(db: Session, payload: SessionSetSyncOperation):
    if payload.operation_type == "create_set":
        _validate_set_payload(payload)
        session = _resolve_session_for_create_set(db, payload)
        item = _resolve_item_for_create_set(db, session, payload)
        return submit_set_record(
            db,
            item.id,
            SetRecordCreate(
                actual_weight=payload.actual_weight,
                actual_reps=payload.actual_reps,
                actual_rir=payload.actual_rir,
                final_weight=payload.final_weight,
                notes=payload.notes,
            ),
        )

    if payload.operation_type == "update_set":
        _validate_set_payload(payload)
        if payload.record_id is None:
            raise bad_request("record_id is required for update_set")

        record = (
            db.query(SetRecord)
            .options(joinedload(SetRecord.session_item))
            .filter(SetRecord.id == payload.record_id)
            .first()
        )
        if not record:
            raise not_found("Set record not found")
        if payload.session_id is not None and record.session_item.session_id != payload.session_id:
            raise bad_request("Set record does not belong to this session")

        return update_set_record(
            db,
            record.id,
            SetRecordUpdate(
                actual_weight=payload.actual_weight,
                actual_reps=payload.actual_reps,
                actual_rir=payload.actual_rir,
                final_weight=payload.final_weight,
                notes=payload.notes,
            ),
        )

    session = _resolve_session_for_completion(db, payload)
    _finalize_session(session, closure_reason="manual_end")
    db.commit()
    return None, None, None, get_session(db, session.id)


def sync_session_snapshot(db: Session, payload: SessionFullSyncPayload):
    session = _resolve_session_for_full_sync(db, payload)
    conflict_logged = _detect_full_sync_conflict(db, session, payload)
    _overwrite_session_from_snapshot(session, payload)
    db.commit()
    return get_session(db, session.id), conflict_logged


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
    _finalize_session(session, closure_reason="manual_end")
    db.commit()
    return get_session(db, session_id)


def close_due_sessions(db: Session, reference_time: datetime | None = None) -> int:
    now = _resolve_local_now(reference_time)
    local_today = now.date()
    due_sessions = (
        db.query(TrainingSession)
        .options(joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records))
        .filter(~TrainingSession.status.in_(tuple(FINAL_SESSION_STATUSES)), TrainingSession.session_date < local_today)
        .all()
    )
    if not due_sessions:
        return 0

    for session in due_sessions:
        _finalize_session(session, closure_reason="midnight_cutoff")

    db.commit()
    return len(due_sessions)


def _validate_set_payload(payload: SessionSetSyncOperation) -> None:
    if payload.actual_weight is None or payload.actual_reps is None or payload.actual_rir is None:
        raise bad_request("actual_weight, actual_reps and actual_rir are required")


def _resolve_session_for_create_set(db: Session, payload: SessionSetSyncOperation) -> TrainingSession:
    if payload.session_id is not None:
        session = (
            db.query(TrainingSession)
            .options(joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records))
            .filter(TrainingSession.id == payload.session_id)
            .first()
        )
        if not session:
            raise not_found("Training session not found")
        return session

    if payload.assignment_id is None or payload.session_date is None:
        raise bad_request("assignment_id and session_date are required when session_id is missing")

    assignment = get_assignment(db, payload.assignment_id)
    existing = _find_session_by_assignment_and_date(db, assignment.id, payload.session_date)
    if existing:
        return existing
    return _prepare_session_for_assignment(db, assignment, payload.session_date)


def _resolve_item_for_create_set(db: Session, session: TrainingSession, payload: SessionSetSyncOperation) -> TrainingSessionItem:
    if payload.session_item_id is not None:
        item = _get_session_item(db, payload.session_item_id)
        if item.session_id != session.id:
            raise bad_request("Training item does not belong to this session")
        return item

    if payload.template_item_id is None:
        raise bad_request("template_item_id is required when session_item_id is missing")

    item = next((current for current in session.items if current.template_item_id == payload.template_item_id), None)
    if item is None:
        raise not_found("Training item not found for template item")
    return item


def _resolve_session_for_completion(db: Session, payload: SessionSetSyncOperation) -> TrainingSession:
    if payload.session_id is not None:
        session = db.query(TrainingSession).filter(TrainingSession.id == payload.session_id).first()
        if not session:
            raise not_found("Training session not found")
        return session

    if payload.assignment_id is None or payload.session_date is None:
        raise bad_request("assignment_id and session_date are required when session_id is missing")

    assignment = get_assignment(db, payload.assignment_id)
    existing = _find_session_by_assignment_and_date(db, assignment.id, payload.session_date)
    if existing:
        return existing
    return _prepare_session_for_assignment(db, assignment, payload.session_date)


def _resolve_session_for_full_sync(db: Session, payload: SessionFullSyncPayload) -> TrainingSession:
    if payload.session_id is not None:
        session = (
            db.query(TrainingSession)
            .options(joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records))
            .filter(TrainingSession.id == payload.session_id)
            .first()
        )
        if not session:
            raise not_found("Training session not found")
        if session.assignment_id != payload.assignment_id or session.athlete_id != payload.athlete_id:
            raise bad_request("Training session does not match this local draft")
        return session

    assignment = get_assignment(db, payload.assignment_id)
    if assignment.athlete_id != payload.athlete_id:
        raise bad_request("Training assignment does not belong to this athlete")

    existing = _find_session_by_assignment_and_date(db, assignment.id, payload.session_date)
    if existing:
        return existing
    return _prepare_session_for_assignment(db, assignment, payload.session_date)


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
        record.target_weight = target_weight
        record.target_reps = item.prescribed_reps
        if item.enable_auto_load:
            suggestion = compute_next_weight(
                current_weight=record.final_weight,
                target_reps=item.prescribed_reps,
                actual_reps=record.actual_reps,
                actual_rir=record.actual_rir,
                default_increment=item.exercise.default_increment,
                previous_rirs=previous_two_rirs,
            )
            record.suggestion_weight = suggestion.suggestion_weight
            record.suggestion_reason = suggestion.reason_text
        else:
            suggestion = None
            record.suggestion_weight = None
            record.suggestion_reason = None
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
    if session.status in FINAL_SESSION_STATUSES:
        return

    items = list(session.items)
    if not items:
        session.status = NOT_STARTED_SESSION_STATUS
        session.started_at = None
        session.completed_at = None
        return

    total_records = sum(len(item.records or []) for item in items)
    if total_records == 0:
        session.status = NOT_STARTED_SESSION_STATUS
        session.started_at = None
        session.completed_at = None
        return

    if all(item.status == "completed" for item in items):
        session.status = "completed"
        first_record_time = min(
            (record.completed_at for item in items for record in item.records),
            default=datetime.now(timezone.utc),
        )
        session.started_at = session.started_at or first_record_time
        session.completed_at = session.completed_at or datetime.now(timezone.utc)
        return

    session.status = "in_progress"
    if session.started_at is None:
        session.started_at = min(record.completed_at for item in items for record in item.records)
    session.completed_at = None


def _sync_session_state(session: TrainingSession) -> None:
    if session.status in FINAL_SESSION_STATUSES:
        return
    for item in session.items:
        _recompute_item_records(item)
    _recompute_session_status(session)


def _finalize_session(session: TrainingSession, closure_reason: str) -> None:
    items = list(session.items)
    for item in items:
        _recompute_item_records(item)
    total_records = sum(len(item.records or []) for item in items)
    all_completed = bool(items) and all(item.status == "completed" for item in items)

    if all_completed:
        session.status = "completed"
    elif closure_reason == "midnight_cutoff" and total_records == 0:
        session.status = "absent"
    else:
        session.status = "partial_complete"

    session.completed_at = datetime.now(timezone.utc)


def _detect_full_sync_conflict(db: Session, session: TrainingSession, payload: SessionFullSyncPayload) -> bool:
    remote_snapshot = _serialize_session_snapshot(session)
    local_snapshot = _serialize_full_sync_payload(payload)
    if remote_snapshot == local_snapshot:
        return False

    remote_has_data = any(item["records"] for item in remote_snapshot["items"]) or remote_snapshot["status"] in FINAL_SESSION_STATUSES
    remote_updated_at = session.updated_at
    conflict_type: str | None = None
    summary: str | None = None

    if payload.last_server_updated_at is None and remote_has_data:
        conflict_type = "remote_session_exists_before_local_overwrite"
        summary = (
            "The backend session already contained training data before this device had a confirmed sync baseline. "
            "The full-session fallback kept the local draft and replaced the backend snapshot."
        )
    elif (
        payload.last_server_updated_at is not None
        and remote_updated_at is not None
        and remote_updated_at > payload.last_server_updated_at
    ):
        conflict_type = "remote_changed_since_last_sync"
        summary = (
            f"The backend session changed after the last confirmed sync at {payload.last_server_updated_at.isoformat()}. "
            "The full-session fallback kept the local draft and replaced the backend snapshot."
        )

    if not conflict_type or not summary:
        return False

    db.add(
        TrainingSyncConflict(
            athlete_id=payload.athlete_id,
            assignment_id=payload.assignment_id,
            session_id=session.id,
            session_date=payload.session_date,
            trigger_reason=payload.trigger_reason,
            conflict_type=conflict_type,
            summary=summary,
            local_snapshot=local_snapshot,
            remote_snapshot=remote_snapshot,
        )
    )
    db.flush()
    return True


def _overwrite_session_from_snapshot(session: TrainingSession, payload: SessionFullSyncPayload) -> None:
    session.assignment_id = payload.assignment_id
    session.athlete_id = payload.athlete_id
    session.template_id = payload.template_id or session.template_id
    session.session_date = payload.session_date

    session.items.clear()

    for incoming_item in sorted(payload.items, key=lambda current: (current.sort_order, current.template_item_id)):
        item = TrainingSessionItem(
            session_id=session.id,
            template_item_id=incoming_item.template_item_id,
            exercise_id=incoming_item.exercise_id,
            sort_order=incoming_item.sort_order,
            prescribed_sets=incoming_item.prescribed_sets,
            prescribed_reps=incoming_item.prescribed_reps,
            target_note=incoming_item.target_note,
            is_main_lift=incoming_item.is_main_lift,
            enable_auto_load=incoming_item.enable_auto_load,
            initial_load=incoming_item.initial_load,
            status=incoming_item.status,
        )

        for incoming_record in sorted(incoming_item.records, key=lambda current: current.set_number):
            item.records.append(
                SetRecord(
                    set_number=incoming_record.set_number,
                    target_weight=None,
                    target_reps=incoming_item.prescribed_reps,
                    actual_weight=incoming_record.actual_weight,
                    actual_reps=incoming_record.actual_reps,
                    actual_rir=incoming_record.actual_rir,
                    suggestion_weight=None,
                    suggestion_reason=None,
                    user_decision="accepted",
                    final_weight=incoming_record.final_weight,
                    completed_at=incoming_record.completed_at,
                    notes=incoming_record.notes,
                )
            )

        session.items.append(item)

    for item in session.items:
        _recompute_item_records(item)

    _apply_full_sync_session_status(session, payload)


def _apply_full_sync_session_status(session: TrainingSession, payload: SessionFullSyncPayload) -> None:
    if payload.status == "completed":
        session.status = "completed"
        session.started_at = payload.started_at or _resolve_session_started_at(session)
        session.completed_at = payload.completed_at or datetime.now(timezone.utc)
        for item in session.items:
            if len(item.records or []) >= item.prescribed_sets:
                item.status = "completed"
        return

    if payload.status == "absent":
        session.status = "absent"
        session.started_at = None
        session.completed_at = payload.completed_at or datetime.now(timezone.utc)
        return

    if payload.status == "partial_complete":
        session.status = "partial_complete"
        session.started_at = payload.started_at or _resolve_session_started_at(session)
        session.completed_at = payload.completed_at or datetime.now(timezone.utc)
        return

    _recompute_session_status(session)
    if session.status == "not_started":
        session.started_at = None
        session.completed_at = None
        return

    session.started_at = payload.started_at or session.started_at or _resolve_session_started_at(session)
    session.completed_at = payload.completed_at if payload.status in FINAL_SESSION_STATUSES else None


def _serialize_session_snapshot(session: TrainingSession) -> dict:
    return {
        "athlete_id": session.athlete_id,
        "assignment_id": session.assignment_id,
        "session_date": session.session_date.isoformat(),
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "items": [
            {
                "template_item_id": item.template_item_id,
                "exercise_id": item.exercise_id,
                "sort_order": item.sort_order,
                "prescribed_sets": item.prescribed_sets,
                "prescribed_reps": item.prescribed_reps,
                "target_note": item.target_note,
                "is_main_lift": item.is_main_lift,
                "enable_auto_load": item.enable_auto_load,
                "status": item.status,
                "initial_load": item.initial_load,
                "records": [
                    {
                        "set_number": record.set_number,
                        "actual_weight": record.actual_weight,
                        "actual_reps": record.actual_reps,
                        "actual_rir": record.actual_rir,
                        "final_weight": record.final_weight,
                        "notes": record.notes,
                        "completed_at": record.completed_at.isoformat(),
                    }
                    for record in item.records
                ],
            }
            for item in sorted(session.items, key=lambda current: (current.sort_order, current.template_item_id))
        ],
    }


def _serialize_full_sync_payload(payload: SessionFullSyncPayload) -> dict:
    return {
        "athlete_id": payload.athlete_id,
        "assignment_id": payload.assignment_id,
        "session_date": payload.session_date.isoformat(),
        "status": payload.status,
        "started_at": payload.started_at.isoformat() if payload.started_at else None,
        "completed_at": payload.completed_at.isoformat() if payload.completed_at else None,
        "items": [
            {
                "template_item_id": item.template_item_id,
                "exercise_id": item.exercise_id,
                "sort_order": item.sort_order,
                "prescribed_sets": item.prescribed_sets,
                "prescribed_reps": item.prescribed_reps,
                "target_note": item.target_note,
                "is_main_lift": item.is_main_lift,
                "enable_auto_load": item.enable_auto_load,
                "status": item.status,
                "initial_load": item.initial_load,
                "records": [
                    {
                        "set_number": record.set_number,
                        "actual_weight": record.actual_weight,
                        "actual_reps": record.actual_reps,
                        "actual_rir": record.actual_rir,
                        "final_weight": record.final_weight,
                        "notes": record.notes,
                        "completed_at": record.completed_at.isoformat(),
                    }
                    for record in sorted(item.records, key=lambda current: current.set_number)
                ],
            }
            for item in sorted(payload.items, key=lambda current: (current.sort_order, current.template_item_id))
        ],
    }


def _resolve_session_started_at(session: TrainingSession) -> datetime | None:
    completed_ats = [
        record.completed_at
        for item in session.items
        for record in item.records
        if record.completed_at is not None
    ]
    return min(completed_ats) if completed_ats else None


def _resolve_local_now(reference_time: datetime | None = None) -> datetime:
    if reference_time is None:
        return datetime.now().astimezone()
    if reference_time.tzinfo is None:
        return reference_time.replace(tzinfo=timezone.utc).astimezone()
    return reference_time.astimezone()


def _get_next_suggestion(item: TrainingSessionItem):
    if not item.enable_auto_load or item.status == "completed" or not item.records:
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
        if session.status in {"completed", "absent", "partial_complete"}:
            status_map[assignment_id] = session.status
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
        if any(status == "in_progress" for status in statuses):
            athlete_status_map[athlete_id] = "in_progress"
        elif any(status == "partial_complete" for status in statuses):
            athlete_status_map[athlete_id] = "partial_complete"
        elif all(status == "completed" for status in statuses):
            athlete_status_map[athlete_id] = "completed"
        elif all(status == "absent" for status in statuses):
            athlete_status_map[athlete_id] = "absent"
        else:
            athlete_status_map[athlete_id] = "not_started"
    return athlete_status_map
