from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AuthEventLogRead(ORMModel):
    id: int
    username: str
    user_id: int | None = None
    success: bool
    ip: str | None = None
    user_agent: str | None = None
    failure_reason: str | None = None
    created_at: datetime


class AuthEventLogListRead(BaseModel):
    items: list[AuthEventLogRead] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0
