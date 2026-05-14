from datetime import datetime

from pydantic import BaseModel, Field


class ServerTimeRead(BaseModel):
    server_time: datetime
    timezone: str
    utc_offset_minutes: int


class DashboardMemoRead(BaseModel):
    content: str = ""
    updated_at: datetime | None = None


class DashboardMemoUpdate(BaseModel):
    content: str = Field(default="", max_length=1200)


class CloseDueSessionsRead(BaseModel):
    closed_count: int
