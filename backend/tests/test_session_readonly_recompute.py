from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user
from app.core.database import Base, SessionLocal, engine, get_db
from app.main import app
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
    User,
)
from app.services import session_service


@pytest.fixture()
def db_session() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_get_session_does_not_change_updated_at(asgi_client: Any, db_session: Session) -> None:
    session_id = _create_training_session(db_session, include_record=True, status="not_started")
    original_updated_at = db_session.get(TrainingSession, session_id).updated_at

    with _api_overrides(db_session):
        response = asgi_client.get(f"/api/training/sessions/{session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "not_started"
    assert payload["server_signature"]

    db_session.expire_all()
    session = db_session.get(TrainingSession, session_id)
    assert session.status == "not_started"
    assert session.updated_at == original_updated_at


def test_post_recompute_can_change_session_status(asgi_client: Any, db_session: Session) -> None:
    session_id = _create_training_session(db_session, include_record=True, status="not_started")

    with _api_overrides(db_session):
        response = asgi_client.post(f"/api/training/sessions/{session_id}/recompute")

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    db_session.expire_all()
    session = db_session.get(TrainingSession, session_id)
    assert session.status == "in_progress"


def test_close_due_sessions_only_runs_from_explicit_maintenance_post(
    asgi_client: Any,
    db_session: Session,
) -> None:
    session_id = _create_training_session(
        db_session,
        include_record=False,
        session_date=date.today() - timedelta(days=2),
        status="not_started",
    )

    with _api_overrides(db_session):
        get_response = asgi_client.get(f"/api/training/sessions/{session_id}")

    assert get_response.status_code == 200
    db_session.expire_all()
    assert db_session.get(TrainingSession, session_id).status == "not_started"

    with _api_overrides(db_session):
        close_response = asgi_client.post("/api/system/maintenance/close-due-sessions")

    assert close_response.status_code == 200
    assert close_response.json() == {"closed_count": 1}

    db_session.expire_all()
    assert db_session.get(TrainingSession, session_id).status == "absent"


def test_training_and_monitoring_get_endpoints_do_not_close_due_sessions(
    asgi_client: Any,
    db_session: Session,
) -> None:
    session_date = date.today() - timedelta(days=2)
    session_id = _create_training_session(
        db_session,
        include_record=False,
        session_date=session_date,
        status="not_started",
    )
    session = db_session.get(TrainingSession, session_id)
    athlete_id = session.athlete_id
    session_date_param = session_date.isoformat()

    with _api_overrides(db_session):
        responses = [
            asgi_client.get(f"/api/training/athletes?session_date={session_date_param}"),
            asgi_client.get(f"/api/training/plans?athlete_id={athlete_id}&session_date={session_date_param}"),
            asgi_client.get(f"/api/training/today?athlete_id={athlete_id}&session_date={session_date_param}"),
            asgi_client.get(f"/api/monitoring/today?session_date={session_date_param}"),
            asgi_client.get(f"/api/monitoring/athlete-detail?athlete_id={athlete_id}&session_date={session_date_param}"),
        ]

    assert [response.status_code for response in responses] == [200, 200, 200, 200, 200]
    db_session.expire_all()
    assert db_session.get(TrainingSession, session_id).status == "not_started"


def test_close_due_sessions_does_not_close_yesterday_before_rollover(db_session: Session) -> None:
    session_id = _create_training_session(
        db_session,
        include_record=False,
        session_date=date(2026, 5, 14),
        status="not_started",
    )

    closed_count = session_service.close_due_sessions(
        db_session,
        reference_time=_local_datetime(2026, 5, 15, 3),
    )

    assert closed_count == 0
    db_session.expire_all()
    assert db_session.get(TrainingSession, session_id).status == "not_started"


def test_close_due_sessions_closes_yesterday_after_rollover(db_session: Session) -> None:
    session_id = _create_training_session(
        db_session,
        include_record=False,
        session_date=date(2026, 5, 14),
        status="not_started",
    )

    closed_count = session_service.close_due_sessions(
        db_session,
        reference_time=_local_datetime(2026, 5, 15, 5),
    )

    assert closed_count == 1
    db_session.expire_all()
    assert db_session.get(TrainingSession, session_id).status == "absent"


def test_close_due_sessions_always_closes_day_before_yesterday(db_session: Session) -> None:
    session_id = _create_training_session(
        db_session,
        include_record=False,
        session_date=date(2026, 5, 13),
        status="not_started",
    )

    closed_count = session_service.close_due_sessions(
        db_session,
        reference_time=_local_datetime(2026, 5, 15, 3),
    )

    assert closed_count == 1
    db_session.expire_all()
    assert db_session.get(TrainingSession, session_id).status == "absent"


@contextmanager
def _api_overrides(db: Session):
    previous_user_override = app.dependency_overrides.get(get_current_user)
    previous_db_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_current_user] = lambda: User(
        username="admin_user",
        password_hash="unused",
        display_name="Admin user",
        role_code="admin",
        is_active=True,
    )
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        if previous_user_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_user_override

        if previous_db_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_db_override


def _create_training_session(
    db: Session,
    *,
    include_record: bool,
    status: str,
    session_date: date | None = None,
) -> int:
    target_date = session_date or date.today()
    sport = Sport(name="Test sport", code="test_sport")
    team = Team(name="Test team", code="test_team", sport=sport)
    athlete = Athlete(code="athlete_001", full_name="Test Athlete", sport=sport, team=team)
    exercise = Exercise(name="Back Squat", structured_tags={}, search_keywords=[])
    template = TrainingPlanTemplate(name="Strength template", sport=sport, team=team, visibility="public")
    module = TrainingPlanTemplateModule(template=template, sort_order=1, title="Main")
    template_item = TrainingPlanTemplateItem(
        template=template,
        module=module,
        exercise=exercise,
        sort_order=1,
        prescribed_sets=2,
        prescribed_reps=5,
        is_main_lift=True,
        enable_auto_load=False,
        initial_load_mode="fixed_weight",
        initial_load_value=80,
    )
    assignment = AthletePlanAssignment(
        athlete=athlete,
        template=template,
        assigned_date=target_date,
        start_date=target_date - timedelta(days=7),
        end_date=target_date + timedelta(days=7),
        repeat_weekdays=[1, 2, 3, 4, 5, 6, 7],
        status="active",
    )
    session = TrainingSession(
        athlete=athlete,
        assignment=assignment,
        template=template,
        session_date=target_date,
        status=status,
    )
    session_item = TrainingSessionItem(
        session=session,
        template_item=template_item,
        exercise=exercise,
        sort_order=1,
        prescribed_sets=2,
        prescribed_reps=5,
        is_main_lift=True,
        enable_auto_load=False,
        initial_load=80,
        status="pending",
    )
    if include_record:
        session_item.records.append(
            SetRecord(
                set_number=1,
                target_weight=80,
                target_reps=5,
                actual_weight=80,
                actual_reps=5,
                actual_rir=2,
                suggestion_weight=None,
                suggestion_reason=None,
                user_decision="accepted",
                final_weight=80,
                completed_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
            )
        )

    db.add(session)
    db.commit()

    fixed_updated_at = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
    db.execute(
        update(TrainingSession)
        .where(TrainingSession.id == session.id)
        .values(status=status, updated_at=fixed_updated_at)
    )
    db.commit()
    session_id = session.id
    db.expire_all()
    return session_id


def _local_datetime(year: int, month: int, day: int, hour: int) -> datetime:
    local_timezone = datetime.now().astimezone().tzinfo
    return datetime(year, month, day, hour, 0, tzinfo=local_timezone)
