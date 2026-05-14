from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import TrainingPlanTemplate, User
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


def test_auth_me_returns_admin_capabilities(asgi_client: Any) -> None:
    admin = _user(1, "admin")

    with _current_user(admin):
        response = asgi_client.get("/api/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_code"] == "admin"
    assert payload["mode"] == "management"
    assert payload["available_modes"] == ["management", "training", "monitor"]
    assert payload["can_manage_users"] is True
    assert payload["can_manage_system"] is True
    assert payload["capabilities"] == {
        "can_manage_users": True,
        "can_manage_sports": True,
        "can_manage_teams": True,
        "can_manage_athletes": True,
        "can_manage_templates": True,
        "can_manage_backups": True,
        "can_manage_test_definitions": True,
        "can_import_test_records": True,
        "can_enter_training": True,
        "can_view_monitor": True,
        "can_run_maintenance": True,
        "manage_users": True,
        "manage_system": True,
        "access_management": True,
        "access_training": True,
        "access_monitor": True,
    }


def test_auth_me_returns_coach_capabilities(asgi_client: Any) -> None:
    coach = _user(2, "coach")

    with _current_user(coach):
        response = asgi_client.get("/api/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["role_code"] == "coach"
    assert payload["mode"] == "training"
    assert payload["available_modes"] == ["management", "training", "monitor"]
    assert payload["can_manage_users"] is False
    assert payload["can_manage_system"] is True
    assert payload["capabilities"] == {
        "can_manage_users": False,
        "can_manage_sports": False,
        "can_manage_teams": True,
        "can_manage_athletes": True,
        "can_manage_templates": True,
        "can_manage_backups": False,
        "can_manage_test_definitions": True,
        "can_import_test_records": True,
        "can_enter_training": True,
        "can_view_monitor": True,
        "can_run_maintenance": False,
        "manage_users": False,
        "manage_system": True,
        "access_management": True,
        "access_training": True,
        "access_monitor": True,
    }


def test_template_list_permission_fields_for_admin(
    asgi_client: Any,
    db_session: Session,
) -> None:
    admin, _, _ = _seed_template_permission_rows(db_session)

    with _api_overrides(db_session, admin):
        response = asgi_client.get("/api/plan-templates")

    assert response.status_code == 200
    templates = {item["name"]: item for item in response.json()}
    assert set(templates) == {"公共模板", "教练私有模板", "其他教练私有模板"}

    assert templates["公共模板"]["can_edit"] is True
    assert templates["公共模板"]["can_copy"] is True
    assert templates["公共模板"]["edit_lock_reason"] is None

    assert templates["教练私有模板"]["can_edit"] is True
    assert templates["教练私有模板"]["can_copy"] is False
    assert templates["教练私有模板"]["edit_lock_reason"] is None

    assert templates["其他教练私有模板"]["can_edit"] is True
    assert templates["其他教练私有模板"]["can_copy"] is False
    assert templates["其他教练私有模板"]["edit_lock_reason"] is None


def test_template_list_permission_fields_for_coach(
    asgi_client: Any,
    db_session: Session,
) -> None:
    _, coach, _ = _seed_template_permission_rows(db_session)

    with _api_overrides(db_session, coach):
        response = asgi_client.get("/api/plan-templates")

    assert response.status_code == 200
    templates = {item["name"]: item for item in response.json()}
    assert set(templates) == {"公共模板", "教练私有模板"}

    assert templates["公共模板"]["can_edit"] is False
    assert templates["公共模板"]["can_copy"] is True
    assert templates["公共模板"]["edit_lock_reason"] == access_control_service.PUBLIC_TEMPLATE_EDIT_DENIED_DETAIL

    assert templates["教练私有模板"]["can_edit"] is True
    assert templates["教练私有模板"]["can_copy"] is False
    assert templates["教练私有模板"]["edit_lock_reason"] is None


def _seed_template_permission_rows(db: Session) -> tuple[User, User, User]:
    admin = _user(None, "admin", username="admin")
    coach = _user(None, "coach", username="coach")
    other_coach = _user(None, "coach", username="other_coach")
    db.add_all([admin, coach, other_coach])
    db.flush()

    db.add_all(
        [
            TrainingPlanTemplate(
                name="公共模板",
                visibility="public",
                is_active=True,
                owner_user_id=None,
                created_by_user_id=admin.id,
                created_by=admin.id,
            ),
            TrainingPlanTemplate(
                name="教练私有模板",
                visibility="private",
                is_active=True,
                owner_user_id=coach.id,
                created_by_user_id=coach.id,
                created_by=coach.id,
            ),
            TrainingPlanTemplate(
                name="其他教练私有模板",
                visibility="private",
                is_active=True,
                owner_user_id=other_coach.id,
                created_by_user_id=other_coach.id,
                created_by=other_coach.id,
            ),
        ]
    )
    db.commit()
    return admin, coach, other_coach


def _user(user_id: int | None, role_code: str, *, username: str | None = None) -> User:
    return User(
        id=user_id,
        username=username or f"{role_code}_user",
        password_hash="unused",
        display_name=f"{role_code} user",
        role_code=role_code,
        is_active=True,
    )


@contextmanager
def _current_user(user: User):
    previous_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_override


@contextmanager
def _api_overrides(db: Session, user: User):
    previous_user_override = app.dependency_overrides.get(get_current_user)
    previous_db_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_current_user] = lambda: user
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
