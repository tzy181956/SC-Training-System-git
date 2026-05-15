from typing import Any

from sqlalchemy import text


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


def test_ready_does_not_require_login_and_returns_database_check(asgi_client: Any, monkeypatch: Any) -> None:
    from app import main

    def fail_backup_directory_check() -> dict[str, str]:
        raise AssertionError("/ready must not perform backup directory writes")

    monkeypatch.setattr(main, "_check_backup_directory_ready", fail_backup_directory_check)

    response = asgi_client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert set(payload["checks"]) == {"database"}
    assert payload["checks"]["database"]["status"] == "ok"


def test_ready_deep_does_not_require_login_and_returns_database_backup_and_migration_checks(
    asgi_client: Any,
    monkeypatch: Any,
) -> None:
    from app import main

    monkeypatch.setattr(
        main,
        "_check_alembic_revision_ready",
        lambda: {
            "status": "ok",
            "current_revision": "test-head",
            "head_revision": "test-head",
        },
    )

    response = asgi_client.get("/ready/deep")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert set(payload["checks"]) == {"database", "backup_directory", "alembic_revision"}
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["backup_directory"]["status"] == "ok"
    assert payload["checks"]["alembic_revision"]["status"] == "ok"


def test_alembic_ini_path_points_to_backend_config() -> None:
    from app import main

    assert main.BACKEND_DIR.name == "backend"
    assert main.ALEMBIC_INI == main.BACKEND_DIR / "alembic.ini"
    assert main.ALEMBIC_INI.exists()


def test_alembic_revision_check_passes_when_database_matches_cached_head(monkeypatch: Any) -> None:
    from app import main

    _set_alembic_version("test-head")
    monkeypatch.setattr(main, "_alembic_head_revision", "test-head")
    monkeypatch.setattr(main, "_alembic_head_error", None)

    try:
        result = main._check_alembic_revision_ready()
    finally:
        _drop_alembic_version()

    assert result == {
        "status": "ok",
        "current_revision": "test-head",
        "head_revision": "test-head",
    }


def test_alembic_revision_check_reports_mismatch(monkeypatch: Any) -> None:
    from app import main

    _set_alembic_version("old-head")
    monkeypatch.setattr(main, "_alembic_head_revision", "test-head")
    monkeypatch.setattr(main, "_alembic_head_error", None)

    try:
        result = main._check_alembic_revision_ready()
    finally:
        _drop_alembic_version()

    assert result["status"] == "error"
    assert result["current_revision"] == "old-head"
    assert result["head_revision"] == "test-head"


def test_cors_preflight_uses_limited_methods_and_headers(asgi_client: Any) -> None:
    response = asgi_client.request(
        "OPTIONS",
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type, X-Request-ID",
        },
    )

    assert response.status_code == 200
    allowed_methods = response.headers["access-control-allow-methods"]
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "*" not in allowed_methods
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
        assert method in allowed_methods
    for header in ["authorization", "content-type", "x-request-id"]:
        assert header in allowed_headers


def test_response_includes_request_id(asgi_client: Any) -> None:
    response = asgi_client.get("/health")

    assert response.headers["X-Request-ID"]


def _set_alembic_version(revision: str) -> None:
    from app.core.database import engine

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": revision})


def _drop_alembic_version() -> None:
    from app.core.database import engine

    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
