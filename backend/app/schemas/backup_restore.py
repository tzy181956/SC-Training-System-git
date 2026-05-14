from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.dangerous_action import DangerousActionConfirm


class RestoreScopeRead(BaseModel):
    key: str
    label: str
    description: str
    impact_summary: list[str] = Field(default_factory=list)
    affected_tables: list[str] = Field(default_factory=list)


class BackupItemRead(BaseModel):
    filename: str
    stem: str
    restore_point_at: datetime
    file_modified_at: datetime
    size_bytes: int
    trigger: str | None = None
    trigger_label: str | None = None
    label: str | None = None
    naming_scheme: str
    is_managed: bool


class BackupListRead(BaseModel):
    filename_pattern: str
    keep_recent_days: int
    keep_recent_weeks: int
    items: list[BackupItemRead] = Field(default_factory=list)
    available_restore_scopes: list[RestoreScopeRead] = Field(default_factory=list)


class BackupRestorePayload(DangerousActionConfirm):
    backup_filename: str = Field(min_length=1, max_length=255)
    restore_scope: Literal["full_database", "training_records", "test_records"]
    team_id: int | None = None


class BackupRestoreRead(BaseModel):
    backup_filename: str
    restore_scope: str
    restore_scope_label: str
    restore_point_at: datetime
    team_id: int | None = None
    team_name: str | None = None
    restored_tables: list[str] = Field(default_factory=list)
    restored_row_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    message: str
