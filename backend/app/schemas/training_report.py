from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.athlete import AthleteRead


class TrainingReportSetRead(BaseModel):
    id: int
    set_number: int
    target_weight: float | None = None
    target_reps: int
    actual_weight: float
    actual_reps: int
    actual_rir: int
    suggestion_weight: float | None = None
    suggestion_reason: str | None = None
    user_decision: str
    final_weight: float
    completed_at: datetime
    notes: str | None = None
    adjustment_type: str


class TrainingReportItemRead(BaseModel):
    id: int
    exercise_name: str
    sort_order: int
    prescribed_sets: int
    prescribed_reps: int
    completed_sets: int
    target_note: str | None = None
    is_main_lift: bool
    status: str
    records: list[TrainingReportSetRead]


class TrainingReportSessionRead(BaseModel):
    id: int
    session_date: date
    template_name: str
    status: str
    completed_items: int
    total_items: int
    completed_sets: int
    total_sets: int
    items: list[TrainingReportItemRead]


class TrainingReportSummaryRead(BaseModel):
    total_sessions: int
    completed_sessions: int
    completion_rate: float
    completed_items: int
    total_items: int
    completed_sets: int
    total_sets: int
    latest_session_date: date | None = None


class TrainingReportTrendPointRead(BaseModel):
    session_date: date
    value: float


class TrainingReportTrendSeriesRead(BaseModel):
    exercise_name: str
    points: list[TrainingReportTrendPointRead]


class TrainingReportCompletionTrendRead(BaseModel):
    session_date: date
    template_name: str
    completion_rate: float


class TrainingReportFlagRead(BaseModel):
    level: str
    title: str
    description: str


class TrainingReportRead(BaseModel):
    athlete: AthleteRead
    date_range: dict[str, date]
    summary: TrainingReportSummaryRead
    sessions: list[TrainingReportSessionRead]
    trend: dict[str, list[TrainingReportTrendSeriesRead] | list[TrainingReportCompletionTrendRead]]
    flags: list[TrainingReportFlagRead]
