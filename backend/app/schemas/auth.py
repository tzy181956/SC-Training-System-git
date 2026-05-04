from pydantic import BaseModel

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(ORMModel):
    id: int
    username: str
    display_name: str
    role_code: str
    team_id: int | None = None
    team_name: str | None = None
    mode: str
    available_modes: list[str]
    can_manage_users: bool
    can_manage_system: bool
    can_switch_athletes: bool
    is_active: bool
