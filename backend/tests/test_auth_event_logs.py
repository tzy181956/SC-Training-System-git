from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models import AuthEventLog, User


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


def test_successful_login_writes_auth_event_log(asgi_client: Any, db_session: Session) -> None:
    user = _create_user(db_session, username="coach", password="correct-password", role_code="coach")

    response = asgi_client.post(
        "/api/auth/login",
        json_body={"username": " coach ", "password": "correct-password"},
        headers={"User-Agent": "AuthAuditTest/1.0"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}

    event_log = db_session.query(AuthEventLog).one()
    assert event_log.username == "coach"
    assert event_log.user_id == user.id
    assert event_log.success is True
    assert event_log.ip == "127.0.0.1"
    assert event_log.user_agent == "AuthAuditTest/1.0"
    assert event_log.failure_reason is None
    assert event_log.created_at is not None


@pytest.mark.parametrize(
    ("login_username", "login_password", "expected_user_id", "expected_reason"),
    [
        ("missing", "any-password", None, "user_not_found"),
        ("coach", "wrong-password", "coach", "invalid_password"),
        ("athlete", "athlete-password", "athlete", "role_disabled"),
    ],
)
def test_failed_login_writes_auth_event_log_without_leaking_user_existence(
    asgi_client: Any,
    db_session: Session,
    login_username: str,
    login_password: str,
    expected_user_id: str | None,
    expected_reason: str,
) -> None:
    users = {
        "coach": _create_user(db_session, username="coach", password="correct-password", role_code="coach"),
        "athlete": _create_user(db_session, username="athlete", password="athlete-password", role_code="training"),
    }

    response = asgi_client.post(
        "/api/auth/login",
        json_body={"username": login_username, "password": login_password},
        headers={"User-Agent": "AuthAuditTest/1.0"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "用户名或密码错误"}

    event_log = db_session.query(AuthEventLog).one()
    assert event_log.username == login_username
    assert event_log.user_id == (users[expected_user_id].id if expected_user_id else None)
    assert event_log.success is False
    assert event_log.ip == "127.0.0.1"
    assert event_log.user_agent == "AuthAuditTest/1.0"
    assert event_log.failure_reason == expected_reason
    assert event_log.created_at is not None


def _create_user(db: Session, *, username: str, password: str, role_code: str) -> User:
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        display_name=username,
        role_code=role_code,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
