from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import Sport, TrainingPlanTemplate, User
from app.services import access_control_service


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


def test_auth_me_returns_admin_capabilities_and_legacy_fields(asgi_client: Any) -> None:
    admin = User(
        id=1,
        username="admin",
        password_hash="unused",
        display_name="Admin",
        role_code="admin",
        is_active=True,
    )

    with _api_overrides(current_user=admin):
        response = asgi_client.get("/api/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_code"] == "admin"
    assert payload["mode"] == "management"
    assert payload["available_modes"] == ["management", "training", "monitor"]
    assert payload["can_manage_users"] is True
    assert payload["can_manage_system"] is True
    assert payload["capabilities"]["can_manage_users"] is True
    assert payload["capabilities"]["can_manage_sports"] is True
    assert payload["capabilities"]["can_manage_teams"] is True
    assert payload["capabilities"]["can_manage_athletes"] is True
    assert payload["capabilities"]["can_manage_templates"] is True
    assert payload["capabilities"]["can_manage_backups"] is True
    assert payload["capabilities"]["can_manage_test_definitions"] is True
    assert payload["capabilities"]["can_import_test_records"] is True
    assert payload["capabilities"]["can_enter_training"] is True
    assert payload["capabilities"]["can_view_monitor"] is True
    assert payload["capabilities"]["can_run_maintenance"] is True
    assert payload["capabilities"]["manage_users"] is True
    assert payload["capabilities"]["manage_system"] is True
    assert payload["capabilities"]["access_management"] is True
    assert payload["capabilities"]["access_training"] is True
    assert payload["capabilities"]["access_monitor"] is True


def test_auth_me_returns_coach_capabilities_and_legacy_fields(asgi_client: Any) -> None:
    sport = Sport(id=10, name="Basketball", code="basketball")
    coach = User(
        id=2,
        username="coach",
        password_hash="unused",
        display_name="Coach",
        role_code="coach",
        sport_id=sport.id,
        sport=sport,
        is_active=True,
    )

    with _api_overrides(current_user=coach):
        response = asgi_client.get("/api/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_code"] == "coach"
    assert payload["mode"] == "training"
    assert payload["sport_id"] == sport.id
    assert payload["sport_name"] == sport.name
    assert payload["available_modes"] == ["management", "training", "monitor"]
    assert payload["can_manage_users"] is False
    assert payload["can_manage_system"] is True
    assert payload["capabilities"]["can_manage_users"] is False
    assert payload["capabilities"]["can_manage_sports"] is False
    assert payload["capabilities"]["can_manage_teams"] is True
    assert payload["capabilities"]["can_manage_athletes"] is True
    assert payload["capabilities"]["can_manage_templates"] is True
    assert payload["capabilities"]["can_manage_backups"] is False
    assert payload["capabilities"]["can_manage_test_definitions"] is True
    assert payload["capabilities"]["can_import_test_records"] is True
    assert payload["capabilities"]["can_enter_training"] is True
    assert payload["capabilities"]["can_view_monitor"] is True
    assert payload["capabilities"]["can_run_maintenance"] is False
    assert payload["capabilities"]["manage_users"] is False
    assert payload["capabilities"]["manage_system"] is True
    assert payload["capabilities"]["access_management"] is True
    assert payload["capabilities"]["access_training"] is True
    assert payload["capabilities"]["access_monitor"] is True


def test_admin_template_list_returns_permission_fields(
    asgi_client: Any,
    db_session: Session,
) -> None:
    users = _seed_template_permission_data(db_session)

    with _api_overrides(current_user=users["admin"], db=db_session):
        response = asgi_client.get("/api/plan-templates")

    assert response.status_code == 200
    templates = {item["name"]: item for item in response.json()}

    assert set(templates) == {"公共模板", "教练自建模板", "其他教练模板"}
    assert templates["公共模板"]["can_edit"] is True
    assert templates["公共模板"]["can_copy"] is True
    assert templates["公共模板"]["edit_lock_reason"] is None
    assert templates["教练自建模板"]["can_edit"] is True
    assert templates["教练自建模板"]["can_copy"] is False
    assert templates["教练自建模板"]["edit_lock_reason"] is None
    assert templates["其他教练模板"]["can_edit"] is True
    assert templates["其他教练模板"]["can_copy"] is False
    assert templates["其他教练模板"]["edit_lock_reason"] is None


def test_coach_template_list_returns_permission_fields(
    asgi_client: Any,
    db_session: Session,
) -> None:
    users = _seed_template_permission_data(db_session)

    with _api_overrides(current_user=users["coach"], db=db_session):
        response = asgi_client.get("/api/plan-templates")

    assert response.status_code == 200
    templates = {item["name"]: item for item in response.json()}

    assert set(templates) == {"公共模板", "教练自建模板"}
    assert templates["公共模板"]["can_edit"] is False
    assert templates["公共模板"]["can_copy"] is True
    assert templates["公共模板"]["edit_lock_reason"] == access_control_service.PUBLIC_TEMPLATE_EDIT_DENIED_DETAIL
    assert templates["教练自建模板"]["can_edit"] is True
    assert templates["教练自建模板"]["can_copy"] is False
    assert templates["教练自建模板"]["edit_lock_reason"] is None


@contextmanager
def _api_overrides(current_user: User, db: Session | None = None):
    previous_user_override = app.dependency_overrides.get(get_current_user)
    previous_db_override = app.dependency_overrides.get(get_db)

    app.dependency_overrides[get_current_user] = lambda: current_user
    if db is not None:
        def override_get_db():
            yield db

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


def _seed_template_permission_data(db: Session) -> dict[str, User]:
    sport = Sport(name="Basketball", code="basketball")
    admin = User(
        username="admin",
        password_hash="unused",
        display_name="Admin",
        role_code="admin",
        is_active=True,
    )
    coach = User(
        username="coach",
        password_hash="unused",
        display_name="Coach",
        role_code="coach",
        sport=sport,
        is_active=True,
    )
    other_coach = User(
        username="other_coach",
        password_hash="unused",
        display_name="Other Coach",
        role_code="coach",
        sport=sport,
        is_active=True,
    )
    db.add_all([sport, admin, coach, other_coach])
    db.flush()

    db.add_all(
        [
            TrainingPlanTemplate(
                name="公共模板",
                sport=sport,
                visibility="public",
                owner_user_id=None,
                created_by_user_id=admin.id,
                created_by=admin.id,
            ),
            TrainingPlanTemplate(
                name="教练自建模板",
                sport=sport,
                visibility="private",
                owner_user_id=coach.id,
                created_by_user_id=coach.id,
                created_by=coach.id,
            ),
            TrainingPlanTemplate(
                name="其他教练模板",
                sport=sport,
                visibility="private",
                owner_user_id=other_coach.id,
                created_by_user_id=other_coach.id,
                created_by=other_coach.id,
            ),
        ]
    )
    db.commit()
    return {"admin": admin, "coach": coach, "other_coach": other_coach}
