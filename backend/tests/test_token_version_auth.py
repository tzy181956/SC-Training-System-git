from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models import User


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


def test_reset_password_revokes_existing_token_and_allows_new_password(
    asgi_client: Any,
    db_session: Session,
) -> None:
    admin = _create_user(db_session, username="admin", password="admin-password", role_code="admin")
    coach = _create_user(db_session, username="coach", password="old-password", role_code="coach")

    admin_token = _login(asgi_client, "admin", "admin-password")
    old_coach_token = _login(asgi_client, "coach", "old-password")

    old_me_response = asgi_client.get("/api/auth/me", headers=_auth_headers(old_coach_token))
    assert old_me_response.status_code == 200
    assert old_me_response.json()["username"] == "coach"

    reset_response = asgi_client.post(
        f"/api/users/{coach.id}/reset-password",
        json_body={"password": "new-password"},
        headers=_auth_headers(admin_token),
    )
    assert reset_response.status_code == 200

    revoked_response = asgi_client.get("/api/auth/me", headers=_auth_headers(old_coach_token))
    assert revoked_response.status_code == 401

    new_coach_token = _login(asgi_client, "coach", "new-password")
    new_me_response = asgi_client.get("/api/auth/me", headers=_auth_headers(new_coach_token))
    assert new_me_response.status_code == 200
    assert new_me_response.json()["username"] == "coach"

    db_session.refresh(coach)
    db_session.refresh(admin)
    assert coach.token_version == 2
    assert coach.password_changed_at is not None
    assert coach.last_login_at is not None
    assert admin.last_login_at is not None


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


def _login(asgi_client: Any, username: str, password: str) -> str:
    response = asgi_client.post("/api/auth/login", json_body={"username": username, "password": password})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"access_token", "token_type"}
    assert payload["token_type"] == "bearer"
    return payload["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
