from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.athlete import AthleteRead


class SessionTrainingLoadRead(BaseModel):
    session_id: int
    session_date: date
    status: str
    session_rpe: int | None = None
    session_duration_minutes: int | None = None
    session_srpe_load: int | None = None


class DailyTrainingLoadRead(BaseModel):
    load_date: date
    session_count: int
    total_duration_minutes: int
    total_srpe_load: int


class TrainingLoadMetricsRead(BaseModel):
    formula_status: Literal["pending"] = "pending"
    acwr: float | None = None
    monotony: float | None = None
    strain: float | None = None


class AthleteTrainingLoadRead(BaseModel):
    athlete: AthleteRead
    date_range: dict[str, date]
    sessions: list[SessionTrainingLoadRead]
    daily_loads: list[DailyTrainingLoadRead]
    metrics: TrainingLoadMetricsRead
