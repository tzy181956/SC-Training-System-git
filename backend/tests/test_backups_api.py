from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from app.api.deps import get_current_user
from app.api.endpoints import backups as backups_endpoint
from app.main import app
from app.models import User
from app.services.backup_service import (
    BackupCatalogRecord,
    BackupResult,
    RestoreResult,
    RestoreScopeDefinition,
)


FORBIDDEN_RESPONSE_KEYS = {
    "backup_directory",
    "path",
    "backup_path",
    "pre_restore_backup_path",
}


def test_admin_can_list_backups_without_server_paths(asgi_client: Any) -> None:
    with _current_user_role("admin"), _backup_service_catalog_patches():
        response = asgi_client.get("/api/backups")

    assert response.status_code == 200
    payload = response.json()
    _assert_forbidden_keys_absent(payload)

    assert payload["filename_pattern"] == "training-YYYYMMDD-HHMMSS-trigger-label.db"
    assert payload["keep_recent_days"] == 14
    assert payload["keep_recent_weeks"] == 8

    item = payload["items"][0]
    for key in (
        "filename",
        "restore_point_at",
        "file_modified_at",
        "size_bytes",
        "trigger",
        "trigger_label",
        "label",
        "naming_scheme",
        "is_managed",
    ):
        assert key in item

    assert item["filename"] == "training-20260514-101500-manual-server.db"
    assert "C:/server/private/backups" not in response.content.decode("utf-8")


def test_coach_cannot_list_backups(asgi_client: Any) -> None:
    with (
        _current_user_role("coach"),
        patch.object(backups_endpoint.backup_service, "list_backup_catalog") as list_mock,
    ):
        response = asgi_client.get("/api/backups")

    assert response.status_code == 403
    list_mock.assert_not_called()


def test_restore_response_uses_filename_without_server_paths(asgi_client: Any) -> None:
    restore_result = _restore_result()
    payload = {
        "confirmed": True,
        "confirmation_text": "RESTORE",
        "backup_filename": restore_result.backup_record.filename,
        "restore_scope": "full_database",
    }

    with (
        _current_user_role("admin"),
        patch.object(backups_endpoint.dangerous_operation_service, "require_confirmation"),
        patch.object(backups_endpoint.backup_service, "restore_backup", return_value=restore_result) as restore_mock,
    ):
        response = asgi_client.post("/api/backups/restore", json_body=payload)

    assert response.status_code == 200
    restore_mock.assert_called_once_with(
        backup_filename="training-20260514-101500-manual-server.db",
        restore_scope_key="full_database",
        team_id=None,
        actor_name="admin user",
    )

    payload = response.json()
    _assert_forbidden_keys_absent(payload)
    assert payload["backup_filename"] == "training-20260514-101500-manual-server.db"
    assert "C:/server/private/backups" not in response.content.decode("utf-8")


@contextmanager
def _current_user_role(role_code: str):
    previous_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: User(
        username=f"{role_code}_user",
        password_hash="unused",
        display_name=f"{role_code} user",
        role_code=role_code,
        is_active=True,
    )
    try:
        yield
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_override


@contextmanager
def _backup_service_catalog_patches():
    with (
        patch.object(
            backups_endpoint.backup_service,
            "describe_backup_policy",
            return_value={
                "backup_directory": "C:/server/private/backups",
                "filename_pattern": "training-YYYYMMDD-HHMMSS-trigger-label.db",
                "keep_recent_days": 14,
                "keep_recent_weeks": 8,
            },
        ),
        patch.object(
            backups_endpoint.backup_service,
            "list_backup_catalog",
            return_value=[_backup_catalog_record()],
        ),
        patch.object(
            backups_endpoint.backup_service,
            "list_restore_scopes",
            return_value=[_restore_scope()],
        ),
    ):
        yield


def _restore_result() -> RestoreResult:
    pre_restore_backup = BackupResult(
        created=True,
        backup_path=Path("C:/server/private/backups/training-20260514-102000-before_dangerous.db"),
        trigger="before_dangerous",
        label="before_restore_full_database",
        skipped_reason=None,
        deleted_paths=[],
    )
    return RestoreResult(
        backup_record=_backup_catalog_record(),
        scope=_restore_scope(),
        restored_tables=["*"],
        pre_restore_backup=pre_restore_backup,
        restored_row_counts={},
        team_id=None,
        team_name=None,
        post_restore_note=None,
    )


def _restore_scope() -> RestoreScopeDefinition:
    return RestoreScopeDefinition(
        key="full_database",
        label="Full database restore",
        description="Restore the whole database from the selected backup.",
        impact_summary=["Create a pre-restore backup first."],
        tables=[],
    )


def _backup_catalog_record() -> BackupCatalogRecord:
    restore_point_at = datetime(2026, 5, 14, 10, 15, tzinfo=timezone.utc)
    file_modified_at = datetime(2026, 5, 14, 10, 16, tzinfo=timezone.utc)
    return BackupCatalogRecord(
        path=Path("C:/server/private/backups/training-20260514-101500-manual-server.db"),
        filename="training-20260514-101500-manual-server.db",
        stem="training",
        restore_point_at=restore_point_at,
        file_modified_at=file_modified_at,
        size_bytes=4096,
        trigger="manual",
        trigger_label="Manual backup",
        label="server",
        naming_scheme="managed",
        is_managed=True,
    )


def _assert_forbidden_keys_absent(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in FORBIDDEN_RESPONSE_KEYS
            _assert_forbidden_keys_absent(child)
        return
    if isinstance(value, list):
        for child in value:
            _assert_forbidden_keys_absent(child)
