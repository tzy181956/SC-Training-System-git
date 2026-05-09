from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import (
    Athlete,
    AthletePlanAssignment,
    SetRecord,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
    TrainingSession,
    TrainingSessionEditLog,
    TrainingSessionItem,
    TrainingSyncConflict,
)
from app.schemas.training_session import (
    CoachSetRecordCreate,
    CoachSetRecordUpdate,
    SessionFinishFeedbackUpdate,
    SessionFullSyncPayload,
    SessionSetSyncOperation,
    SetRecordCreate,
    SetRecordUpdate,
)
from app.services import athlete_service, backup_service, dangerous_operation_service
from app.services.assignment_service import (
    ensure_assignment_scheduled_for_date,
    get_active_assignment_for_date,
    get_assignment,
    is_assignment_scheduled_for_date,
    list_active_assignments_for_date,
)
from app.services.progression_service import compute_next_weight
from app.services.session_state_utils import (
    FINAL_SESSION_STATUSES,
    NOT_STARTED_SESSION_STATUS,
    build_snapshot_signature,
    resolve_finalized_session_status,
    resolve_session_item_status,
    resolve_session_status,
    serialize_full_sync_payload,
    serialize_session_snapshot,
)
DEFAULT_POST_CLASS_ACTOR = "管理端"

SESSION_DETAIL_OPTIONS = (
    joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
    joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
    joinedload(TrainingSession.items)
    .joinedload(TrainingSessionItem.template_item)
    .joinedload(TrainingPlanTemplateItem.module)
    .joinedload(TrainingPlanTemplateModule.items),
)


def get_or_create_today_session(db: Session, athlete_id: int, session_date: date) -> TrainingSession:
    close_due_sessions(db)
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise not_found("Athlete not found")

    assignment = get_active_assignment_for_date(db, athlete_id, session_date)
    if not assignment:
        raise not_found("No active plan for the selected date")

    return open_session_for_assignment(db, assignment.id, session_date)


def list_training_athletes(db: Session, session_date: date, sport_id: int | None = None) -> list[Athlete]:
    close_due_sessions(db)
    athletes = athlete_service.list_athletes(db, sport_id=sport_id)
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
    ensure_assignment_scheduled_for_date(assignment, session_date)
    existing = _find_session_by_assignment_and_date(db, assignment.id, session_date)
    if existing:
        _sync_session_state(existing)
        db.commit()
        return _attach_session_signature(existing)
    return _build_session_preview(assignment, session_date)


def get_or_create_session_for_assignment(db: Session, assignment_id: int, session_date: date) -> TrainingSession:
    assignment = get_assignment(db, assignment_id)
    return _ensure_session_for_assignment(db, assignment, session_date)


def _find_session_by_assignment_and_date(db: Session, assignment_id: int, session_date: date) -> TrainingSession | None:
    return (
        db.query(TrainingSession)
        .options(*SESSION_DETAIL_OPTIONS)
        .filter(TrainingSession.assignment_id == assignment_id, TrainingSession.session_date == session_date)
        .first()
    )


def _ensure_session_for_assignment(db: Session, assignment, session_date: date) -> TrainingSession:
    ensure_assignment_scheduled_for_date(assignment, session_date)
    existing = _find_session_by_assignment_and_date(db, assignment.id, session_date)
    if existing:
        _sync_session_state(existing)
        db.commit()
        return existing

    session = _prepare_session_for_assignment(db, assignment, session_date)
    db.commit()
    return get_session(db, session.id)


def _prepare_session_for_assignment(db: Session, assignment, session_date: date) -> TrainingSession:
    ensure_assignment_scheduled_for_date(assignment, session_date)
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
    items = [
        {
            "id": template_item.id,
            "template_item_id": template_item.id,
            "module_id": template_item.module_id,
            "module_code": template_item.module_code,
            "module_title": template_item.module_title,
            "module_note": template_item.module.note if template_item.module else None,
            "display_index": template_item.display_index,
            "display_code": template_item.display_code,
            "sort_order": template_item.sort_order,
            "prescribed_sets": template_item.prescribed_sets,
            "prescribed_reps": template_item.prescribed_reps,
            "target_note": template_item.target_note,
            "is_main_lift": template_item.is_main_lift,
            "enable_auto_load": template_item.enable_auto_load,
            "initial_load_mode": template_item.initial_load_mode,
            "initial_load_value": template_item.initial_load_value,
            "initial_load": _resolve_assignment_initial_load(template_item, override_map),
            "status": "pending",
            "exercise": template_item.exercise,
            "records": [],
        }
        for template_item in assignment.template.items
    ]
    return {
        "id": None,
        "athlete_id": assignment.athlete_id,
        "assignment_id": assignment.id,
        "template_id": assignment.template_id,
        "session_date": session_date,
        "status": NOT_STARTED_SESSION_STATUS,
        "updated_at": None,
        "server_signature": None,
        "started_at": None,
        "completed_at": None,
        "session_rpe": None,
        "session_feedback": None,
        "coach_note": None,
        "athlete_note": None,
        "modules": _build_session_module_payloads(items),
        "items": items,
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
            initial_load=_resolve_assignment_initial_load(template_item, override_map),
            status="pending",
        )
        for template_item in assignment.template.items
    ]


def _resolve_assignment_initial_load(template_item, override_map: dict[int, float]) -> float | None:
    if template_item.id in override_map:
        return override_map[template_item.id]
    if template_item.initial_load_mode == "fixed_weight":
        return template_item.initial_load_value
    return None


def _build_session_module_payloads(items: list[dict]) -> list[dict]:
    grouped: dict[int | str, dict] = {}
    ordered_modules: list[dict] = []
    for item in sorted(items, key=lambda current: (current["sort_order"], current["template_item_id"])):
        module_key: int | str = item.get("module_id") or f"ungrouped-{item['template_item_id']}"
        if module_key not in grouped:
            module_code = item.get("module_code") or "A"
            grouped[module_key] = {
                "id": item.get("module_id"),
                "sort_order": len(ordered_modules) + 1,
                "module_code": module_code,
                "title": item.get("module_title"),
                "note": item.get("module_note"),
                "display_label": f"模块 {module_code}",
                "items": [],
            }
            ordered_modules.append(grouped[module_key])
        grouped[module_key]["items"].append(item)
    return ordered_modules


def get_session(db: Session, session_id: int) -> TrainingSession:
    close_due_sessions(db)
    session = (
        db.query(TrainingSession)
        .options(*SESSION_DETAIL_OPTIONS)
        .filter(TrainingSession.id == session_id)
        .first()
    )
    if not session:
        raise not_found("Training session not found")
    _sync_session_state(session)
    db.commit()
    return _attach_session_signature(session)


def submit_set_record(db: Session, item_id: int, payload: SetRecordCreate):
    item = _get_session_item(db, item_id)
    record = _append_set_record(item, payload)
    db.flush()
    _recompute_item_records(item)
    _recompute_session_status(item.session)
    item.session.started_at = item.session.started_at or record.completed_at
    _refresh_training_loads(db, item.session)
    db.commit()

    refreshed_item = _get_session_item(db, item_id)
    refreshed_record = db.query(SetRecord).filter(SetRecord.id == record.id).first()
    refreshed_session = get_session(db, item.session_id)
    return refreshed_record, _get_next_suggestion(refreshed_item), refreshed_item, refreshed_session


def update_set_record(db: Session, record_id: int, payload: SetRecordUpdate):
    record = _get_set_record(db, record_id)
    _apply_set_record_update(record, payload)
    _recompute_item_records(record.session_item)
    _recompute_session_status(record.session_item.session)
    _refresh_training_loads(db, record.session_item.session)
    db.commit()

    refreshed_item = _get_session_item(db, record.session_item_id)
    refreshed_record = db.query(SetRecord).filter(SetRecord.id == record_id).first()
    refreshed_session = get_session(db, record.session_item.session_id)
    return refreshed_record, _get_next_suggestion(refreshed_item), refreshed_item, refreshed_session


def coach_add_set_record(db: Session, item_id: int, payload: CoachSetRecordCreate):
    item = _get_session_item(db, item_id)
    session_before_status = item.session.status
    record = _append_set_record(item, payload)
    db.flush()
    _recompute_item_records(item)
    _recompute_session_status(item.session, allow_final_reopen=True)
    item.session.started_at = item.session.started_at or record.completed_at
    _create_training_edit_log(
        db=db,
        session=item.session,
        item=item,
        record=record,
        action_type="add_set",
        actor_name=payload.actor_name,
        before_snapshot={
            "session_status": session_before_status,
            "completed_sets": max(len(item.records) - 1, 0),
        },
        after_snapshot={
            **_serialize_record_for_edit_log(record),
            "session_status": item.session.status,
            "completed_sets": len(item.records),
        },
        summary=_build_add_set_log_summary(record, session_before_status, item.session.status),
    )
    _refresh_training_loads(db, item.session)
    db.commit()

    refreshed_item = _get_session_item(db, item_id)
    refreshed_record = db.query(SetRecord).filter(SetRecord.id == record.id).first()
    refreshed_session = get_session(db, item.session_id)
    return refreshed_record, _get_next_suggestion(refreshed_item), refreshed_item, refreshed_session


def coach_update_set_record(db: Session, record_id: int, payload: CoachSetRecordUpdate):
    record = _get_set_record(db, record_id)
    session_before_status = record.session_item.session.status
    before_snapshot = {
        **_serialize_record_for_edit_log(record),
        "session_status": session_before_status,
    }

    _apply_set_record_update(record, payload)
    _recompute_item_records(record.session_item)
    _recompute_session_status(record.session_item.session, allow_final_reopen=True)

    after_snapshot = {
        **_serialize_record_for_edit_log(record),
        "session_status": record.session_item.session.status,
    }
    _create_training_edit_log(
        db=db,
        session=record.session_item.session,
        item=record.session_item,
        record=record,
        action_type="update_set",
        actor_name=payload.actor_name,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        summary=_build_update_set_log_summary(before_snapshot, after_snapshot),
    )
    _refresh_training_loads(db, record.session_item.session)
    db.commit()

    refreshed_item = _get_session_item(db, record.session_item_id)
    refreshed_record = db.query(SetRecord).filter(SetRecord.id == record_id).first()
    refreshed_session = get_session(db, record.session_item.session_id)
    return refreshed_record, _get_next_suggestion(refreshed_item), refreshed_item, refreshed_session


def coach_delete_set_record(db: Session, record_id: int, *, actor_name: str | None = None):
    record = _get_set_record(db, record_id)
    item = record.session_item
    session = item.session
    session_before_status = session.status
    deleted_snapshot = _serialize_record_for_edit_log(record)
    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_set_record_{record_id}")

    db.delete(record)
    db.flush()

    for index, current_record in enumerate(sorted(item.records, key=lambda current: (current.set_number, current.id)), start=1):
        current_record.set_number = index

    _recompute_item_records(item)
    _recompute_session_status(session, allow_final_reopen=True)

    _create_training_edit_log(
        db=db,
        session=session,
        item=item,
        record=None,
        action_type="delete_set",
        actor_name=actor_name,
        before_snapshot={**deleted_snapshot, "session_status": session_before_status},
        after_snapshot={"remaining_sets": len(item.records), "session_status": session.status},
        summary=_build_delete_set_log_summary(
            deleted_snapshot,
            session_before_status=session_before_status,
            session_after_status=session.status,
        ),
        object_type="set_record",
        object_id=record_id,
    )
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_training_set_record",
        object_type="set_record",
        object_id=record_id,
        actor_name=actor_name,
        summary=f"删除训练组记录：第 {deleted_snapshot['set_number']} 组",
        impact_scope={
            "athlete_id": session.athlete_id,
            "athlete_name": item.session.athlete.full_name if getattr(item.session, "athlete", None) else None,
            "team_id": item.session.athlete.team_id if getattr(item.session, "athlete", None) else None,
            "team_name": (
                item.session.athlete.team.name
                if getattr(getattr(item.session, "athlete", None), "team", None)
                else None
            ),
            "session_id": session.id,
            "session_item_id": item.id,
            "exercise_name": item.exercise.name if item.exercise else None,
            "deleted_set_number": deleted_snapshot["set_number"],
            "session_status_before": session_before_status,
            "session_status_after": session.status,
        },
        backup_path=backup_result.backup_path,
    )
    _refresh_training_loads(db, session)
    db.commit()

    refreshed_item = _get_session_item(db, item.id)
    refreshed_session = get_session(db, session.id)
    return refreshed_item, refreshed_session


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
    _refresh_training_loads(db, session)
    db.commit()
    return None, None, None, get_session(db, session.id)


def sync_session_snapshot(db: Session, payload: SessionFullSyncPayload):
    session = _resolve_session_for_full_sync(db, payload)
    previous_athlete_id = session.athlete_id
    previous_session_date = session.session_date
    conflict_logged = _detect_full_sync_conflict(db, session, payload)
    _overwrite_session_from_snapshot(session, payload)
    _refresh_training_loads(
        db,
        session,
        previous_athlete_id=previous_athlete_id,
        previous_session_date=previous_session_date,
    )
    db.commit()
    return get_session(db, session.id), conflict_logged


def complete_session_item(db: Session, item_id: int) -> TrainingSessionItem:
    item = _get_session_item(db, item_id)
    item.status = "completed"
    _recompute_session_status(item.session)
    _refresh_training_loads(db, item.session)
    db.commit()
    return _get_session_item(db, item_id)


def complete_session(db: Session, session_id: int) -> TrainingSession:
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise not_found("Training session not found")
    _finalize_session(session, closure_reason="manual_end")
    _refresh_training_loads(db, session)
    db.commit()
    return get_session(db, session_id)


def submit_session_finish_feedback(
    db: Session,
    session_id: int,
    payload: SessionFinishFeedbackUpdate,
) -> TrainingSession:
    session = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
        )
        .filter(TrainingSession.id == session_id)
        .first()
    )
    if not session:
        raise not_found("Training session not found")

    _sync_session_state(session)
    if session.status != "completed":
        raise bad_request("仅已完成的训练课可以提交整体 RPE 反馈")

    is_first_finish_feedback = session.session_rpe is None

    session.session_rpe = payload.session_rpe
    session.session_feedback = payload.session_feedback
    if is_first_finish_feedback:
        session.completed_at = datetime.now(timezone.utc)
    _refresh_training_loads(db, session)
    db.commit()
    return get_session(db, session_id)


def close_due_sessions(db: Session, reference_time: datetime | None = None) -> int:
    """Finalize sessions dated before today.

    This function is intentionally idempotent and is used in two places:
    - once during backend startup as the primary cross-day close trigger
    - again inside training-related entry points as a fallback safety net
    """
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
        _refresh_training_loads(db, session)

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
    ensure_assignment_scheduled_for_date(assignment, payload.session_date)
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
    ensure_assignment_scheduled_for_date(assignment, payload.session_date)
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
    ensure_assignment_scheduled_for_date(assignment, payload.session_date)

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
            joinedload(TrainingSessionItem.template_item)
            .joinedload(TrainingPlanTemplateItem.module)
            .joinedload(TrainingPlanTemplateModule.items),
        )
        .filter(TrainingSessionItem.id == item_id)
        .first()
    )
    if not item:
        raise not_found("Training item not found")
    return item


def _get_set_record(db: Session, record_id: int) -> SetRecord:
    record = (
        db.query(SetRecord)
        .options(
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.exercise),
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.records),
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.session),
            joinedload(SetRecord.session_item)
            .joinedload(TrainingSessionItem.template_item)
            .joinedload(TrainingPlanTemplateItem.module)
            .joinedload(TrainingPlanTemplateModule.items),
        )
        .filter(SetRecord.id == record_id)
        .first()
    )
    if not record:
        raise not_found("Set record not found")
    return record


def _append_set_record(item: TrainingSessionItem, payload: SetRecordCreate | CoachSetRecordCreate) -> SetRecord:
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
    return record


def _apply_set_record_update(record: SetRecord, payload: SetRecordUpdate | CoachSetRecordUpdate) -> None:
    record.actual_weight = payload.actual_weight
    record.actual_reps = payload.actual_reps
    record.actual_rir = payload.actual_rir
    record.final_weight = payload.final_weight if payload.final_weight is not None else payload.actual_weight
    record.notes = payload.notes


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
        item.status = resolve_session_item_status(0, item.prescribed_sets)
    else:
        item.status = resolve_session_item_status(len(ordered_records), item.prescribed_sets)


def _recompute_session_status(session: TrainingSession, allow_final_reopen: bool = False) -> None:
    if session.status in FINAL_SESSION_STATUSES and not allow_final_reopen:
        return

    items = list(session.items)
    is_final_context = allow_final_reopen and (session.status in FINAL_SESSION_STATUSES or session.completed_at is not None)
    next_status = resolve_session_status(
        has_items=bool(items),
        total_records=sum(len(item.records or []) for item in items),
        all_items_completed=bool(items) and all(item.status == "completed" for item in items),
        is_final_context=is_final_context,
    )
    session.status = next_status
    if next_status in {"absent", NOT_STARTED_SESSION_STATUS}:
        session.started_at = None
        session.completed_at = session.completed_at or datetime.now(timezone.utc) if is_final_context else None
        return

    first_record_time = min(
        (_ensure_utc_datetime(record.completed_at) for item in items for record in item.records),
        default=datetime.now(timezone.utc),
    )
    if next_status == "completed":
        session.started_at = session.started_at or first_record_time
        session.completed_at = session.completed_at or datetime.now(timezone.utc)
        return

    if next_status == "partial_complete":
        session.started_at = session.started_at or first_record_time
        session.completed_at = session.completed_at or datetime.now(timezone.utc)
        return

    session.started_at = session.started_at or first_record_time
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

    session.status = resolve_finalized_session_status(
        total_records=total_records,
        all_items_completed=all_completed,
        closure_reason=closure_reason,
    )
    session.completed_at = datetime.now(timezone.utc)


def _serialize_record_for_edit_log(record: SetRecord) -> dict:
    return {
        "record_id": record.id,
        "set_number": record.set_number,
        "actual_weight": record.actual_weight,
        "actual_reps": record.actual_reps,
        "actual_rir": record.actual_rir,
        "final_weight": record.final_weight,
        "notes": record.notes,
    }


def _create_training_edit_log(
    db: Session,
    session: TrainingSession,
    item: TrainingSessionItem,
    record: SetRecord | None,
    action_type: str,
    actor_name: str | None,
    before_snapshot: dict | None,
    after_snapshot: dict | None,
    summary: str,
    object_type: str | None = None,
    object_id: int | None = None,
) -> None:
    db.add(
        TrainingSessionEditLog(
            session_id=session.id,
            session_item_id=item.id,
            set_record_id=record.id if record else None,
            action_type=action_type,
            actor_name=(actor_name or DEFAULT_POST_CLASS_ACTOR).strip() or DEFAULT_POST_CLASS_ACTOR,
            object_type=object_type or ("set_record" if record else "session_item"),
            object_id=object_id if object_id is not None else (record.id if record else item.id),
            summary=summary,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            edited_at=datetime.now(timezone.utc),
        )
    )


def _build_update_set_log_summary(before_snapshot: dict, after_snapshot: dict) -> str:
    changes: list[str] = []
    if before_snapshot["actual_weight"] != after_snapshot["actual_weight"]:
        changes.append(f"重量 {before_snapshot['actual_weight']}→{after_snapshot['actual_weight']}")
    if before_snapshot["actual_reps"] != after_snapshot["actual_reps"]:
        changes.append(f"次数 {before_snapshot['actual_reps']}→{after_snapshot['actual_reps']}")
    if before_snapshot["actual_rir"] != after_snapshot["actual_rir"]:
        changes.append(f"RIR {before_snapshot['actual_rir']}→{after_snapshot['actual_rir']}")
    if before_snapshot.get("notes") != after_snapshot.get("notes"):
        changes.append("备注已更新")

    summary = f"课后修改第 {after_snapshot['set_number']} 组"
    if changes:
        summary = f"{summary}：{'，'.join(changes)}"
    if before_snapshot["session_status"] != after_snapshot["session_status"]:
        summary = f"{summary}；课状态 {_format_session_status_label(before_snapshot['session_status'])}→{_format_session_status_label(after_snapshot['session_status'])}"
    return summary


def _build_add_set_log_summary(record: SetRecord, session_before_status: str, session_after_status: str) -> str:
    summary = (
        f"课后补录第 {record.set_number} 组："
        f"重量 {record.actual_weight}，次数 {record.actual_reps}，RIR {record.actual_rir}"
    )
    if session_before_status != session_after_status:
        summary = f"{summary}；课状态 {_format_session_status_label(session_before_status)}→{_format_session_status_label(session_after_status)}"
    return summary


def _build_delete_set_log_summary(snapshot: dict, *, session_before_status: str, session_after_status: str) -> str:
    summary = (
        f"课后删除第 {snapshot['set_number']} 组："
        f"重量 {snapshot['actual_weight']}，次数 {snapshot['actual_reps']}，RIR {snapshot['actual_rir']}"
    )
    if session_before_status != session_after_status:
        summary = f"{summary}；课状态 {_format_session_status_label(session_before_status)}→{_format_session_status_label(session_after_status)}"
    return summary


def _format_session_status_label(status: str) -> str:
    return {
        "not_started": "未开始",
        "in_progress": "进行中",
        "completed": "完成",
        "absent": "缺席",
        "partial_complete": "未完全按计划完成",
    }.get(status, status)


def _detect_full_sync_conflict(db: Session, session: TrainingSession, payload: SessionFullSyncPayload) -> bool:
    remote_snapshot = serialize_session_snapshot(session)
    local_snapshot = serialize_full_sync_payload(payload)
    if remote_snapshot == local_snapshot:
        return False

    remote_has_data = any(item["records"] for item in remote_snapshot["items"]) or remote_snapshot["status"] in FINAL_SESSION_STATUSES
    remote_signature = build_snapshot_signature(remote_snapshot)
    remote_updated_at = session.updated_at
    conflict_type: str | None = None
    summary: str | None = None

    if payload.last_server_signature is None and payload.last_server_updated_at is None and remote_has_data:
        conflict_type = "remote_session_exists_before_local_overwrite"
        summary = (
            "当前设备在没有已确认同步基线的情况下发起了整课覆盖补传，但后端训练课已存在训练数据。"
            "系统已保留本地草稿，并用本地快照覆盖了后端记录。"
        )
    elif payload.last_server_signature is not None and payload.last_server_signature != remote_signature:
        conflict_type = "remote_changed_since_last_sync"
        summary = (
            "后端训练课在最近一次确认同步签名之后发生了变化。"
            "系统已保留本地草稿，并用本地快照覆盖了后端记录。"
        )
    elif (
        payload.last_server_signature is None
        and payload.last_server_updated_at is not None
        and remote_updated_at is not None
        and remote_updated_at > payload.last_server_updated_at
    ):
        conflict_type = "remote_changed_since_last_sync"
        summary = (
            f"后端训练课在最近一次确认同步时间 {payload.last_server_updated_at.isoformat()} 之后发生了变化。"
            "系统已保留本地草稿，并用本地快照覆盖了后端记录。"
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
    session.session_rpe = payload.session_rpe
    session.session_feedback = payload.session_feedback

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


def _attach_session_signature(session: TrainingSession) -> TrainingSession:
    session.server_signature = build_snapshot_signature(serialize_session_snapshot(session))
    return session


def _resolve_session_started_at(session: TrainingSession) -> datetime | None:
    completed_ats = [
        _ensure_utc_datetime(record.completed_at)
        for item in session.items
        for record in item.records
        if record.completed_at is not None
    ]
    return min(completed_ats) if completed_ats else None


def _ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _refresh_training_loads(
    db: Session,
    session: TrainingSession,
    *,
    previous_athlete_id: int | None = None,
    previous_session_date: date | None = None,
) -> None:
    from app.services import training_load_service

    training_load_service.refresh_session_load_metrics(
        db,
        session,
        previous_athlete_id=previous_athlete_id,
        previous_load_date=previous_session_date,
    )


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
        "reason_text": latest_record.suggestion_reason or "按最新一组训练反馈继续下一组。",
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
            joinedload(AthletePlanAssignment.template)
            .joinedload(TrainingPlanTemplate.modules)
            .joinedload(TrainingPlanTemplateModule.items)
            .joinedload(TrainingPlanTemplateItem.exercise),
            joinedload(AthletePlanAssignment.template)
            .joinedload(TrainingPlanTemplate.items)
            .joinedload(TrainingPlanTemplateItem.exercise),
            joinedload(AthletePlanAssignment.template)
            .joinedload(TrainingPlanTemplate.items)
            .joinedload(TrainingPlanTemplateItem.module)
            .joinedload(TrainingPlanTemplateModule.items),
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
    assignments = [assignment for assignment in assignments if is_assignment_scheduled_for_date(assignment, session_date)]

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
    assignments = [assignment for assignment in assignments if is_assignment_scheduled_for_date(assignment, session_date)]
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
