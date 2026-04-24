from datetime import date, datetime

from pydantic import BaseModel, Field


class LogItemRead(BaseModel):
    id: int
    source_type: str
    action_type: str
    object_type: str
    object_id: int | None = None
    object_label: str | None = None
    summary: str
    actor_name: str
    occurred_at: datetime
    team_id: int | None = None
    team_name: str | None = None
    athlete_id: int | None = None
    athlete_name: str | None = None
    session_id: int | None = None
    session_date: date | None = None
    status: str | None = None
    before_snapshot: dict | None = None
    after_snapshot: dict | None = None
    extra_context: dict | None = None


class LogListRead(BaseModel):
    items: list[LogItemRead] = Field(default_factory=list)
    available_object_types: list[str] = Field(default_factory=list)
