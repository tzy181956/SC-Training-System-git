from typing import Any


def test_unauthenticated_athletes_returns_401(asgi_client: Any) -> None:
    response = asgi_client.get("/api/athletes")

    assert response.status_code == 401


def test_unauthenticated_users_returns_401(asgi_client: Any) -> None:
    response = asgi_client.get("/api/users")

    assert response.status_code == 401


def test_health_does_not_require_login(asgi_client: Any) -> None:
    response = asgi_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_ready_does_not_require_login_and_returns_checks(asgi_client: Any) -> None:
    response = asgi_client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["backup_directory"]["status"] == "ok"


def test_response_includes_request_id(asgi_client: Any) -> None:
    response = asgi_client.get("/health")

    assert response.headers["X-Request-ID"]
