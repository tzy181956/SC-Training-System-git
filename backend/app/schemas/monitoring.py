from datetime import date, datetime

from pydantic import BaseModel


class MonitoringLatestSetRead(BaseModel):
    actual_weight: float | None = None
    actual_reps: int | None = None
    actual_rir: int | None = None
    completed_at: datetime | None = None


class MonitoringTeamOptionRead(BaseModel):
    team_id: int | None = None
    team_name: str
    athlete_count: int


class MonitoringAthleteCardRead(BaseModel):
    athlete_id: int
    athlete_name: str
    team_id: int | None = None
    team_name: str | None = None
    session_id: int | None = None
    session_status: str
    sync_status: str
    current_exercise_name: str | None = None
    completed_items: int
    total_items: int
    completed_sets: int
    total_sets: int
    latest_set: MonitoringLatestSetRead | None = None
    has_alert: bool


class MonitoringTodayRead(BaseModel):
    session_date: date
    updated_at: datetime
    teams: list[MonitoringTeamOptionRead]
    athletes: list[MonitoringAthleteCardRead]
