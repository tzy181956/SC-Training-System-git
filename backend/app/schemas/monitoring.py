from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


MonitoringSessionStatus = Literal["no_plan", "not_started", "in_progress", "completed", "partial_complete", "absent"]
MonitoringSyncStatus = Literal["synced", "pending", "manual_retry_required"]


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
    session_status: MonitoringSessionStatus
    sync_status: MonitoringSyncStatus
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


class MonitoringSetRecordRead(BaseModel):
    id: int | None = None
    set_number: int
    target_weight: float | None = None
    target_reps: int | None = None
    actual_weight: float | None = None
    actual_reps: int | None = None
    actual_rir: int | None = None
    completed_at: datetime | None = None
    notes: str | None = None


class MonitoringExerciseItemRead(BaseModel):
    item_id: int | None = None
    exercise_id: int | None = None
    exercise_name: str
    sort_order: int
    prescribed_sets: int
    prescribed_reps: int | None = None
    target_weight: float | None = None
    target_note: str | None = None
    is_main_lift: bool
    status: str
    completed_sets: int
    records: list[MonitoringSetRecordRead]


class MonitoringAssignmentDetailRead(BaseModel):
    assignment_id: int
    template_id: int | None = None
    template_name: str
    session_id: int | None = None
    session_status: MonitoringSessionStatus
    completed_items: int
    total_items: int
    completed_sets: int
    total_sets: int
    exercises: list[MonitoringExerciseItemRead]


class MonitoringAthleteDetailRead(BaseModel):
    session_date: date
    updated_at: datetime
    athlete_id: int
    athlete_name: str
    team_id: int | None = None
    team_name: str | None = None
    session_status: MonitoringSessionStatus
    sync_status: MonitoringSyncStatus
    has_alert: bool
    assignments: list[MonitoringAssignmentDetailRead]
