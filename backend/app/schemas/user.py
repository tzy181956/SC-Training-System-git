from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


UserRoleCode = Literal["admin", "coach"]


class UserManagementRead(ORMModel):
    id: int
    username: str
    display_name: str
    role_code: UserRoleCode
    sport_id: int | None = None
    sport_name: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    username: str
    display_name: str
    role_code: UserRoleCode
    sport_id: int | None = None
    is_active: bool = True
    password: str = Field(min_length=8)

    @field_validator("username", "display_name")
    @classmethod
    def _require_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class UserUpdate(BaseModel):
    display_name: str | None = None
    role_code: UserRoleCode | None = None
    sport_id: int | None = None
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def _normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class UserPasswordResetPayload(BaseModel):
    password: str = Field(min_length=8)
