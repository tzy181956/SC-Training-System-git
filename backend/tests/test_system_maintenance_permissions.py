from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from app.api.deps import get_current_user
from app.api.endpoints import system as system_endpoint
from app.core.database import get_db
from app.main import app
from app.models import User


def test_close_due_sessions_rejects_coach(asgi_client: Any) -> None:
    with (
        _api_overrides("coach"),
        patch.object(system_endpoint.session_service, "close_due_sessions", return_value=3) as close_mock,
    ):
        response = asgi_client.post("/api/system/maintenance/close-due-sessions")

    assert response.status_code == 403
    close_mock.assert_not_called()


def test_close_due_sessions_allows_admin_and_returns_closed_count(asgi_client: Any) -> None:
    db_marker = object()

    with (
        _api_overrides("admin", db_marker=db_marker),
        patch.object(system_endpoint.session_service, "close_due_sessions", return_value=3) as close_mock,
    ):
        response = asgi_client.post("/api/system/maintenance/close-due-sessions")

    assert response.status_code == 200
    assert response.json() == {"closed_count": 3}
    close_mock.assert_called_once_with(db_marker)


@contextmanager
def _api_overrides(role_code: str, *, db_marker: object | None = None):
    previous_user_override = app.dependency_overrides.get(get_current_user)
    previous_db_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        yield db_marker if db_marker is not None else object()

    app.dependency_overrides[get_current_user] = lambda: User(
        username=f"{role_code}_user",
        password_hash="unused",
        display_name=f"{role_code} user",
        role_code=role_code,
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
