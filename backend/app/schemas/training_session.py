from datetime import date, datetime

from pydantic import BaseModel
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
    last_server_updated_at: datetime | None = None
    last_server_signature: str | None = None
    trigger_reason: Literal['manual', 'fallback'] = 'manual'
    items: list[SessionFullSyncItem] = []


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
    coach_note: str | None = None
    athlete_note: str | None = None
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
