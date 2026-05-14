from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import create_access_token, get_password_hash
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


def test_login_uses_forwarded_ip_from_local_proxy(asgi_client: Any, db_session: Session) -> None:
    user = _create_user(db_session, username="coach", password="correct-password", role_code="coach")

    response = asgi_client.post(
        "/api/auth/login",
        json_body={"username": "coach", "password": "correct-password"},
        headers={
            "User-Agent": "AuthAuditTest/1.0",
            "X-Forwarded-For": "203.0.113.10, 127.0.0.1",
        },
    )

    assert response.status_code == 200
    event_log = db_session.query(AuthEventLog).one()
    assert event_log.user_id == user.id
    assert event_log.ip == "203.0.113.10"


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
    assert response.json() == {"detail": "用户名或密码错误，或登录尝试过于频繁，请稍后再试"}

    event_log = db_session.query(AuthEventLog).one()
    assert event_log.username == login_username
    assert event_log.user_id == (users[expected_user_id].id if expected_user_id else None)
    assert event_log.success is False
    assert event_log.ip == "127.0.0.1"
    assert event_log.user_agent == "AuthAuditTest/1.0"
    assert event_log.failure_reason == expected_reason
    assert event_log.created_at is not None


def test_username_rate_limit_returns_generic_429_and_logs_attempt(
    asgi_client: Any,
    db_session: Session,
) -> None:
    user = _create_user(db_session, username="coach", password="correct-password", role_code="coach")
    created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    for _ in range(5):
        _create_auth_event(
            db_session,
            username="coach",
            success=False,
            failure_reason="invalid_password",
            ip="127.0.0.1",
            created_at=created_at,
        )

    response = asgi_client.post(
        "/api/auth/login",
        json_body={"username": "coach", "password": "correct-password"},
        headers={"User-Agent": "AuthAuditTest/1.0"},
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "用户名或密码错误，或登录尝试过于频繁，请稍后再试"}

    event_log = db_session.query(AuthEventLog).order_by(AuthEventLog.id.desc()).first()
    assert event_log is not None
    assert event_log.username == "coach"
    assert event_log.user_id == user.id
    assert event_log.success is False
    assert event_log.ip == "127.0.0.1"
    assert event_log.failure_reason == "rate_limited_username"


def test_ip_rate_limit_returns_generic_429_and_logs_attempt(
    asgi_client: Any,
    db_session: Session,
) -> None:
    user = _create_user(db_session, username="coach", password="correct-password", role_code="coach")
    created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    for index in range(20):
        _create_auth_event(
            db_session,
            username=f"other-{index}",
            success=False,
            failure_reason="invalid_password",
            ip="127.0.0.1",
            created_at=created_at,
        )

    response = asgi_client.post(
        "/api/auth/login",
        json_body={"username": "coach", "password": "correct-password"},
        headers={"User-Agent": "AuthAuditTest/1.0"},
    )

    assert response.status_code == 429
    assert response.json() == {"detail": "用户名或密码错误，或登录尝试过于频繁，请稍后再试"}

    event_log = db_session.query(AuthEventLog).order_by(AuthEventLog.id.desc()).first()
    assert event_log is not None
    assert event_log.username == "coach"
    assert event_log.user_id == user.id
    assert event_log.success is False
    assert event_log.ip == "127.0.0.1"
    assert event_log.failure_reason == "rate_limited_ip"


def test_admin_can_query_auth_event_logs(asgi_client: Any, db_session: Session) -> None:
    admin = _create_user(db_session, username="admin", password="admin-password", role_code="admin")
    _create_auth_event(
        db_session,
        username="coach",
        success=True,
        failure_reason=None,
        ip="10.0.0.11",
        created_at=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
    )
    _create_auth_event(
        db_session,
        username="missing",
        success=False,
        failure_reason="user_not_found",
        ip="10.0.0.12",
        created_at=datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc),
    )

    response = asgi_client.get("/api/auth-events?page=1&page_size=1", headers=_auth_headers(admin))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["username"] == "missing"
    assert payload["items"][0]["success"] is False


def test_coach_cannot_query_auth_event_logs(asgi_client: Any, db_session: Session) -> None:
    coach = _create_user(db_session, username="coach", password="coach-password", role_code="coach")
    _create_auth_event(
        db_session,
        username="coach",
        success=True,
        failure_reason=None,
        ip="10.0.0.11",
        created_at=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
    )

    response = asgi_client.get("/api/auth-events", headers=_auth_headers(coach))

    assert response.status_code == 403


def test_auth_event_filters_success_and_failure_reason(asgi_client: Any, db_session: Session) -> None:
    admin = _create_user(db_session, username="admin", password="admin-password", role_code="admin")
    _create_auth_event(
        db_session,
        username="success-coach",
        success=True,
        failure_reason=None,
        ip="10.0.0.10",
        created_at=datetime(2026, 5, 14, 8, 0, tzinfo=timezone.utc),
    )
    _create_auth_event(
        db_session,
        username="wrong-password",
        success=False,
        failure_reason="invalid_password",
        ip="10.0.0.11",
        created_at=datetime(2026, 5, 14, 9, 0, tzinfo=timezone.utc),
    )
    _create_auth_event(
        db_session,
        username="missing-user",
        success=False,
        failure_reason="user_not_found",
        ip="10.0.0.12",
        created_at=datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc),
    )

    failure_response = asgi_client.get("/api/auth-events?success=false", headers=_auth_headers(admin))
    reason_response = asgi_client.get(
        "/api/auth-events?success=false&failure_reason=invalid_password",
        headers=_auth_headers(admin),
    )

    assert failure_response.status_code == 200
    assert failure_response.json()["total"] == 2

    assert reason_response.status_code == 200
    reason_payload = reason_response.json()
    assert reason_payload["total"] == 1
    assert reason_payload["items"][0]["username"] == "wrong-password"
    assert reason_payload["items"][0]["failure_reason"] == "invalid_password"


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


def _create_auth_event(
    db: Session,
    *,
    username: str,
    success: bool,
    failure_reason: str | None,
    ip: str,
    created_at: datetime,
) -> AuthEventLog:
    event_log = AuthEventLog(
        username=username,
        success=success,
        failure_reason=failure_reason,
        ip=ip,
        user_agent="AuthAuditTest/1.0",
        created_at=created_at,
    )
    db.add(event_log)
    db.commit()
    db.refresh(event_log)
    return event_log


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id), token_version=user.token_version)
    return {"Authorization": f"Bearer {token}"}
