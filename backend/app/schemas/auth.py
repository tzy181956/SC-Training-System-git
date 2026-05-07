from pydantic import BaseModel

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    username: str
    password: str


class VerifyPasswordRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyPasswordResponse(BaseModel):
    verified: bool = True


class UserRead(ORMModel):
    id: int
    username: str
    display_name: str
    role_code: str
    sport_id: int | None = None
    sport_name: str | None = None
    mode: str
    available_modes: list[str]
    can_manage_users: bool
    can_manage_system: bool
    is_active: bool
