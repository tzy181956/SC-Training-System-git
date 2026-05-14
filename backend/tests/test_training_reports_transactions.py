from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import training_reports as training_reports_endpoint
from app.core.database import Base
from app.models import (
    Athlete,
    AthletePlanAssignment,
    DangerousOperationLog,
    Exercise,
    SetRecord,
    Sport,
    Team,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
    TrainingSession,
    TrainingSessionEditLog,
    TrainingSessionItem,
)
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.training_session import CoachSetRecordCreate
from app.services import session_service


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'training-reports-tx.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_coach_add_set_record_commits_post_class_record(db_session) -> None:
    ids = _seed_training_session(db_session, record_count=0, status="not_started")

    response = training_reports_endpoint.coach_add_set_record(
        ids.session_item_id,
        CoachSetRecordCreate(
            actual_weight=82.5,
            actual_reps=5,
            actual_rir=2,
            final_weight=82.5,
            notes="post class add",
            actor_name="Coach A",
        ),
        db_session,
        _admin_user(),
    )

    assert set(response) == {"record", "next_suggestion", "item", "session", "session_status", "session_completed_at"}
    assert response["record"].id is not None
    assert response["record"].actual_weight == 82.5
    assert response["session_status"] == "in_progress"

    db_session.expire_all()
    assert db_session.query(SetRecord).count() == 1
    assert db_session.query(TrainingSessionEditLog).filter_by(action_type="add_set").count() == 1
    assert db_session.get(TrainingSession, ids.session_id).status == "in_progress"


def test_coach_delete_set_record_failure_rolls_back(db_session) -> None:
    ids = _seed_training_session(db_session, record_count=2, status="in_progress")
    original_record_ids = [record.id for record in db_session.query(SetRecord).order_by(SetRecord.set_number).all()]

    with (
        patch.object(
            session_service.backup_service,
            "create_pre_dangerous_operation_backup",
            return_value=SimpleNamespace(backup_path="test-backup.db"),
        ),
        patch.object(session_service, "_refresh_training_loads", side_effect=RuntimeError("simulated delete failure")),
        pytest.raises(RuntimeError, match="simulated delete failure"),
    ):
        training_reports_endpoint.coach_delete_set_record(
            original_record_ids[0],
            DangerousActionConfirm(confirmed=True, actor_name="Coach A"),
            db_session,
            _admin_user(),
        )

    db_session.expire_all()
    records = db_session.query(SetRecord).order_by(SetRecord.set_number).all()
    assert [record.id for record in records] == original_record_ids
    assert [record.set_number for record in records] == [1, 2]
    assert db_session.get(TrainingSession, ids.session_id).status == "in_progress"
    assert db_session.query(TrainingSessionEditLog).count() == 0
    assert db_session.query(DangerousOperationLog).count() == 0


def test_void_training_session_failure_does_not_write_dangerous_operation_log(db_session) -> None:
    ids = _seed_training_session(db_session, record_count=0, status="not_started")

    with (
        patch.object(
            session_service.backup_service,
            "create_pre_dangerous_operation_backup",
            return_value=SimpleNamespace(backup_path="test-backup.db"),
        ),
        patch.object(session_service, "_refresh_training_loads", side_effect=RuntimeError("simulated void failure")),
        pytest.raises(RuntimeError, match="simulated void failure"),
    ):
        training_reports_endpoint.coach_void_training_session(
            ids.session_id,
            DangerousActionConfirm(confirmed=True, actor_name="Coach A"),
            db_session,
            _admin_user(),
        )

    db_session.expire_all()
    assert db_session.get(TrainingSession, ids.session_id).status == "not_started"
    assert db_session.query(TrainingSessionEditLog).count() == 0
    assert db_session.query(DangerousOperationLog).count() == 0


def _admin_user():
    return SimpleNamespace(role_code="admin", display_name="Admin user")


def _seed_training_session(db, *, record_count: int, status: str):
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
        initial_load_value=80.0,
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
        status=status,
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
        initial_load=80.0,
        status="pending" if record_count == 0 else "in_progress",
    )
    for index in range(1, record_count + 1):
        session_item.records.append(
            SetRecord(
                set_number=index,
                target_weight=80.0,
                target_reps=5,
                actual_weight=80.0 + index,
                actual_reps=5,
                actual_rir=2,
                suggestion_weight=None,
                suggestion_reason=None,
                user_decision="accepted",
                final_weight=80.0 + index,
                completed_at=datetime(2026, 5, 14, 8, index, tzinfo=timezone.utc),
            )
        )

    db.add(session)
    db.commit()
    return SimpleNamespace(
        session_id=session.id,
        session_item_id=session_item.id,
    )
