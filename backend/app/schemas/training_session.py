from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.assignment import AssignmentRead
from app.schemas.athlete import AthleteRead
from app.schemas.common import ORMModel
from app.schemas.exercise import ExerciseRead


class SuggestionRead(BaseModel):
    suggestion_weight: float | None = None
    decision_hint: str
    reason_code: str
    reason_text: str
    should_deload: bool = False
    should_stop_progression: bool = False


class SetRecordCreate(BaseModel):
    actual_weight: float
    actual_reps: int
    actual_rir: int
    user_decision: str | None = None
    final_weight: float | None = None
    notes: str | None = None


class SetRecordUpdate(BaseModel):
    actual_weight: float
    actual_reps: int
    actual_rir: int
    final_weight: float | None = None
    notes: str | None = None


class SetRecordRead(ORMModel):
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


class SessionItemRead(ORMModel):
    id: int
    template_item_id: int
    sort_order: int
    prescribed_sets: int
    prescribed_reps: int
    target_note: str | None = None
    is_main_lift: bool
    enable_auto_load: bool
    initial_load: float | None = None
    status: str
    exercise: ExerciseRead
    records: list[SetRecordRead] = []


class SessionRead(ORMModel):
    id: int
    athlete_id: int
    assignment_id: int
    template_id: int
    session_date: date
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    coach_note: str | None = None
    athlete_note: str | None = None
    items: list[SessionItemRead] = []


class TrainingPlanAssignmentRead(AssignmentRead):
    training_status: str = "not_started"


class TrainingAthleteRead(AthleteRead):
    training_status: str = "no_plan"
    assignments: list[TrainingPlanAssignmentRead] = []


class TrainingModePlanListRead(BaseModel):
    athlete: AthleteRead
    session_date: date
    assignments: list[TrainingPlanAssignmentRead]


class SetSubmissionResponse(BaseModel):
    record: SetRecordRead
    next_suggestion: SuggestionRead | None = None
    item: SessionItemRead
    session: SessionRead
    session_status: str
    session_completed_at: datetime | None = None


class SetRecordUpdateResponse(BaseModel):
    record: SetRecordRead
    next_suggestion: SuggestionRead | None = None
    item: SessionItemRead
    session: SessionRead
    session_status: str
    session_completed_at: datetime | None = None
