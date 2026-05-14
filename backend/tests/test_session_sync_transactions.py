from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import sessions as sessions_endpoint
from app.core.database import Base
from app.models import (
    Athlete,
    AthletePlanAssignment,
    Exercise,
    SetRecord,
    Sport,
    Team,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
    TrainingSession,
    TrainingSessionItem,
    TrainingSyncConflict,
    TrainingSyncIssue,
)
from app.schemas.training_session import (
    SessionFinishFeedbackUpdate,
    SessionFullSyncPayload,
    SessionSetSyncOperation,
    SetRecordCreate,
)
from app.services import session_service


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'training-sync-tx.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_create_set_commits_one_record(db_session) -> None:
    ids = _seed_training_session(db_session)
    payload = _create_set_payload(ids.session_id, ids.session_item_id, local_record_id=101)

    response = sessions_endpoint.sync_session_operation(payload, db_session, _admin_user())

    record = response["record"]
    assert record.id is not None
    assert record.local_record_id == 101
    assert db_session.query(SetRecord).count() == 1


def test_duplicate_local_record_id_returns_existing_record(db_session) -> None:
    ids = _seed_training_session(db_session)
    payload = _create_set_payload(ids.session_id, ids.session_item_id, local_record_id=202)

    first_response = sessions_endpoint.sync_session_operation(payload, db_session, _admin_user())
    second_response = sessions_endpoint.sync_session_operation(payload, db_session, _admin_user())

    assert second_response["record"].id == first_response["record"].id
    assert db_session.query(SetRecord).count() == 1


def test_zero_local_record_id_is_treated_as_absent(db_session) -> None:
    ids = _seed_training_session(db_session)
    payload = _create_set_payload(ids.session_id, ids.session_item_id, local_record_id=0)

    first_response = sessions_endpoint.sync_session_operation(payload, db_session, _admin_user())
    second_response = sessions_endpoint.sync_session_operation(payload, db_session, _admin_user())

    assert first_response["record"].id != second_response["record"].id
    assert first_response["record"].set_number == 1
    assert second_response["record"].set_number == 2
    assert first_response["record"].local_record_id is None
    assert second_response["record"].local_record_id is None
    assert db_session.query(SetRecord).count() == 2


def test_local_record_id_conflict_keeps_outer_staged_change(db_session) -> None:
    ids = _seed_training_session(db_session)
    original_payload = _create_set_payload(ids.session_id, ids.session_item_id, local_record_id=203)
    first_response = sessions_endpoint.sync_session_operation(original_payload, db_session, _admin_user())
    existing_record_id = first_response["record"].id

    athlete = db_session.get(Athlete, ids.athlete_id)
    athlete.full_name = "Staged Athlete Rename"

    original_find = session_service._find_set_record_by_local_record_id
    find_calls = {"count": 0}

    def miss_existing_record_once(db, item_id: int, local_record_id: int):
        find_calls["count"] += 1
        if find_calls["count"] == 1:
            return None
        return original_find(db, item_id, local_record_id)

    duplicate_payload = SetRecordCreate(
        actual_weight=50.0,
        actual_reps=5,
        actual_rir=2,
        final_weight=50.0,
        local_record_id=203,
    )

    with patch.object(session_service, "_find_set_record_by_local_record_id", side_effect=miss_existing_record_once):
        record, _, _, _ = session_service.submit_set_record(db_session, ids.session_item_id, duplicate_payload)

    assert record.id == existing_record_id
    assert db_session.query(SetRecord).count() == 1

    db_session.commit()
    db_session.expire_all()
    assert db_session.get(Athlete, ids.athlete_id).full_name == "Staged Athlete Rename"
    assert db_session.query(SetRecord).count() == 1


def test_full_sync_conflict_persists_issue_when_automatic_overwrite_rejected(db_session) -> None:
    ids = _seed_training_session(db_session)
    payload = SessionFullSyncPayload(
        assignment_id=ids.assignment_id,
        athlete_id=ids.athlete_id,
        template_id=ids.template_id,
        session_date=ids.session_date,
        session_id=ids.session_id,
        status="in_progress",
        last_server_signature="stale-server-signature",
        trigger_reason="fallback",
        items=[
            {
                "template_item_id": ids.template_item_id,
                "exercise_id": ids.exercise_id,
                "sort_order": 1,
                "prescribed_sets": 3,
                "prescribed_reps": 5,
                "target_note": None,
                "is_main_lift": True,
                "enable_auto_load": False,
                "status": "in_progress",
                "initial_load": 50.0,
                "records": [
                    {
                        "set_number": 1,
                        "actual_weight": 52.5,
                        "actual_reps": 5,
                        "actual_rir": 2,
                        "final_weight": 52.5,
                        "notes": None,
                        "completed_at": datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
                    }
                ],
            }
        ],
    )

    with pytest.raises(HTTPException) as raised:
        sessions_endpoint.sync_session_snapshot(payload, db_session, _admin_user())

    assert raised.value.status_code == 409
    db_session.expire_all()
    assert db_session.query(SetRecord).count() == 0

    issue = db_session.query(TrainingSyncIssue).one()
    assert issue.session_id == ids.session_id
    assert issue.issue_status == "manual_retry_required"
    assert issue.failure_count == 1
    assert issue.sync_payload["session_id"] == ids.session_id

    conflict = db_session.query(TrainingSyncConflict).one()
    assert conflict.session_id == ids.session_id
    assert conflict.conflict_type == "remote_changed_since_last_sync"


def test_create_set_exception_rolls_back_new_record(db_session) -> None:
    ids = _seed_training_session(db_session)
    payload = _create_set_payload(ids.session_id, ids.session_item_id, local_record_id=303)

    with (
        patch.object(session_service, "_build_set_record_result", side_effect=RuntimeError("simulated failure")),
        pytest.raises(RuntimeError, match="simulated failure"),
    ):
        sessions_endpoint.sync_session_operation(payload, db_session, _admin_user())

    assert db_session.query(SetRecord).count() == 0


def test_complete_item_commits_successfully(db_session) -> None:
    ids = _seed_training_session(db_session)
    _add_completed_records(db_session, ids.session_item_id, count=3)

    response = sessions_endpoint.complete_item(ids.session_item_id, db_session, _admin_user())

    assert response.status == "completed"
    db_session.expire_all()
    item = db_session.get(TrainingSessionItem, ids.session_item_id)
    session = db_session.get(TrainingSession, ids.session_id)
    assert item.status == "completed"
    assert session.status == "completed"


def test_complete_session_exception_rolls_back_status_change(db_session) -> None:
    ids = _seed_training_session(db_session)

    with (
        patch.object(session_service, "_refresh_training_loads", side_effect=RuntimeError("simulated failure")),
        pytest.raises(RuntimeError, match="simulated failure"),
    ):
        sessions_endpoint.complete_session(ids.session_id, db_session, _admin_user())

    db_session.expire_all()
    session = db_session.get(TrainingSession, ids.session_id)
    assert session.status == "not_started"
    assert session.completed_at is None


def test_finish_feedback_exception_rolls_back_feedback_change(db_session) -> None:
    ids = _seed_training_session(db_session)
    session = db_session.get(TrainingSession, ids.session_id)
    session.status = "completed"
    session.completed_at = datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc)
    db_session.commit()

    payload = SessionFinishFeedbackUpdate(session_rpe=8, session_feedback="整体强度偏高")

    with (
        patch.object(session_service, "_refresh_training_loads", side_effect=RuntimeError("simulated failure")),
        pytest.raises(RuntimeError, match="simulated failure"),
    ):
        sessions_endpoint.submit_session_finish_feedback(ids.session_id, payload, db_session, _admin_user())

    db_session.expire_all()
    session = db_session.get(TrainingSession, ids.session_id)
    assert session.status == "completed"
    assert session.session_rpe is None
    assert session.session_feedback is None


def _create_set_payload(session_id: int, session_item_id: int, *, local_record_id: int) -> SessionSetSyncOperation:
    return SessionSetSyncOperation(
        operation_type="create_set",
        session_id=session_id,
        session_item_id=session_item_id,
        local_record_id=local_record_id,
        actual_weight=50.0,
        actual_reps=5,
        actual_rir=2,
        final_weight=50.0,
    )


def _admin_user():
    return SimpleNamespace(role_code="admin")


def _seed_training_session(db):
    session_date = date(2026, 5, 14)
    sport = Sport(name="Test Sport", code="test-sport")
    team = Team(name="Test Team", code="test-team", sport=sport)
    athlete = Athlete(code="A001", full_name="Test Athlete", sport=sport, team=team)
    exercise = Exercise(name="Back Squat", code="back-squat", default_increment=2.5)
    template = TrainingPlanTemplate(name="Strength Template", sport=sport, visibility="public")
    module = TrainingPlanTemplateModule(template=template, sort_order=1, title="Main")
    template_item = TrainingPlanTemplateItem(
        template=template,
        module=module,
        exercise=exercise,
        sort_order=1,
        prescribed_sets=3,
        prescribed_reps=5,
        is_main_lift=True,
        enable_auto_load=False,
        initial_load_mode="fixed_weight",
        initial_load_value=50.0,
    )
    assignment = AthletePlanAssignment(
        athlete=athlete,
        template=template,
        assigned_date=session_date,
        start_date=session_date,
        end_date=session_date,
        repeat_weekdays=[session_date.isoweekday()],
        status="active",
    )
    session = TrainingSession(
        athlete=athlete,
        assignment=assignment,
        template=template,
        session_date=session_date,
        status="not_started",
    )
    session_item = TrainingSessionItem(
        session=session,
        template_item=template_item,
        exercise=exercise,
        sort_order=1,
        prescribed_sets=3,
        prescribed_reps=5,
        is_main_lift=True,
        enable_auto_load=False,
        initial_load=50.0,
        status="pending",
    )
    db.add(session_item)
    db.commit()
    return SimpleNamespace(
        athlete_id=athlete.id,
        assignment_id=assignment.id,
        template_id=template.id,
        template_item_id=template_item.id,
        exercise_id=exercise.id,
        session_date=session_date,
        session_id=session.id,
        session_item_id=session_item.id,
    )


def _add_completed_records(db, session_item_id: int, *, count: int) -> None:
    item = db.get(TrainingSessionItem, session_item_id)
    for set_number in range(1, count + 1):
        item.records.append(
            SetRecord(
                set_number=set_number,
                target_weight=50.0,
                target_reps=5,
                actual_weight=50.0,
                actual_reps=5,
                actual_rir=2,
                suggestion_weight=None,
                suggestion_reason=None,
                user_decision="accepted",
                final_weight=50.0,
                completed_at=datetime(2026, 5, 14, 9, set_number, tzinfo=timezone.utc),
            )
        )
    db.commit()
