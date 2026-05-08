from datetime import date, datetime

from pydantic import BaseModel, Field, StrictInt, field_validator
from typing import Literal

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


class CoachSetRecordUpdate(BaseModel):
    actual_weight: float
    actual_reps: int
    actual_rir: int
    final_weight: float | None = None
    notes: str | None = None
    actor_name: str | None = None


class CoachSetRecordCreate(BaseModel):
    actual_weight: float
    actual_reps: int
    actual_rir: int
    final_weight: float | None = None
    notes: str | None = None
    actor_name: str | None = None


class CoachSetRecordDeleteResponse(BaseModel):
    deleted_record_id: int
    item: "SessionItemRead"
    session: "SessionRead"
    session_status: str
    session_completed_at: datetime | None = None


class SessionSetSyncOperation(BaseModel):
    operation_type: Literal['create_set', 'update_set', 'complete_session']
    assignment_id: int | None = None
    session_date: date | None = None
    template_item_id: int | None = None
    session_id: int | None = None
    session_item_id: int | None = None
    record_id: int | None = None
    local_record_id: int | None = None
    actual_weight: float | None = None
    actual_reps: int | None = None
    actual_rir: int | None = None
    final_weight: float | None = None
    notes: str | None = None


class SessionFullSyncRecord(BaseModel):
    set_number: int
    actual_weight: float
    actual_reps: int
    actual_rir: int
    final_weight: float
    notes: str | None = None
    completed_at: datetime


class SessionFullSyncItem(BaseModel):
    template_item_id: int
    exercise_id: int
    sort_order: int
    prescribed_sets: int
    prescribed_reps: int
    target_note: str | None = None
    is_main_lift: bool
    enable_auto_load: bool
    status: str
    initial_load: float | None = None
    records: list[SessionFullSyncRecord] = []


class SessionFullSyncPayload(BaseModel):
    assignment_id: int
    athlete_id: int
    template_id: int | None = None
    session_date: date
    session_id: int | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    session_rpe: StrictInt | None = Field(default=None, ge=0, le=10)
    session_feedback: str | None = Field(default=None, max_length=500)
    last_server_updated_at: datetime | None = None
    last_server_signature: str | None = None
    trigger_reason: Literal['manual', 'fallback'] = 'manual'
    items: list[SessionFullSyncItem] = []

    @field_validator("session_feedback", mode="before")
    @classmethod
    def normalize_session_feedback(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class SessionFinishFeedbackUpdate(BaseModel):
    session_rpe: StrictInt = Field(ge=0, le=10)
    session_feedback: str | None = Field(default=None, max_length=500)

    @field_validator("session_feedback", mode="before")
    @classmethod
    def normalize_session_feedback(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


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


class SessionItemSnapshotRead(ORMModel):
    id: int | None = None
    template_item_id: int
    module_id: int | None = None
    module_code: str | None = None
    module_title: str | None = None
    display_index: int | None = None
    display_code: str | None = None
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


class SessionModuleRead(BaseModel):
    id: int | None = None
    sort_order: int
    module_code: str
    title: str | None = None
    note: str | None = None
    display_label: str
    items: list[SessionItemSnapshotRead] = []


class SessionSnapshotRead(ORMModel):
    id: int | None = None
    athlete_id: int
    assignment_id: int
    template_id: int
    session_date: date
    status: str
    updated_at: datetime | None = None
    server_signature: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    session_rpe: int | None = None
    session_feedback: str | None = None
    coach_note: str | None = None
    athlete_note: str | None = None
    modules: list[SessionModuleRead] = []
    items: list[SessionItemSnapshotRead] = []


class SessionItemRead(SessionItemSnapshotRead):
    id: int


class SessionRead(SessionSnapshotRead):
    id: int
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


class SessionSetSyncResponse(BaseModel):
    record: SetRecordRead | None = None
    next_suggestion: SuggestionRead | None = None
    item: SessionItemRead | None = None
    session: SessionRead
    session_status: str
    session_completed_at: datetime | None = None
    operation_type: Literal['create_set', 'update_set', 'complete_session']
    local_record_id: int | None = None
    sync_status: Literal['synced'] = 'synced'


class SessionFullSyncResponse(BaseModel):
    session: SessionRead
    session_status: str
    session_completed_at: datetime | None = None
    sync_status: Literal['synced'] = 'synced'
    sync_mode: Literal['full'] = 'full'
    conflict_logged: bool = False


class TrainingSyncIssueRead(BaseModel):
    id: int
    athlete_id: int
    athlete_name: str | None = None
    assignment_id: int | None = None
    session_id: int | None = None
    session_date: date
    session_key: str
    issue_status: Literal['manual_retry_required', 'resolved']
    summary: str
    failure_count: int
    last_error: str | None = None
    updated_at: datetime
    resolved_at: datetime | None = None


class TrainingSyncIssueReportPayload(BaseModel):
    session_key: str
    athlete_id: int
    assignment_id: int | None = None
    session_id: int | None = None
    session_date: date
    failure_count: int = 0
    summary: str
    last_error: str | None = None
    sync_payload: SessionFullSyncPayload


class TrainingSyncIssueRetryResponse(BaseModel):
    issue: TrainingSyncIssueRead
    session: SessionRead
    conflict_logged: bool = False
