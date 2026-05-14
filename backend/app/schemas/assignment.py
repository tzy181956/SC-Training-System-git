from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.schemas.athlete import AthleteRead
from app.schemas.common import ORMModel
from app.schemas.training_plan import PlanTemplateRead


DEFAULT_REPEAT_WEEKDAYS = [1, 2, 3, 4, 5, 6, 7]


def _normalize_repeat_weekdays(value: object) -> list[int]:
    if value is None:
        return DEFAULT_REPEAT_WEEKDAYS.copy()
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("循环星期格式不正确")

    normalized: list[int] = list()
    seen: set[int] = set()
    for raw in value:
        try:
            weekday = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("循环星期只能使用 1-7") from exc
        if weekday < 1 or weekday > 7:
            raise ValueError("循环星期只能使用 1-7")
        if weekday not in seen:
            normalized.append(weekday)
            seen.add(weekday)

    if not normalized:
        raise ValueError("至少选择一个循环星期")
    return sorted(normalized)


class AssignmentOverrideBase(BaseModel):
    template_item_id: int
    initial_load_override: float


class AssignmentOverrideCreate(AssignmentOverrideBase):
    pass


class AssignmentOverrideUpdate(BaseModel):
    initial_load_override: float


class AssignmentOverrideRead(ORMModel, AssignmentOverrideBase):
    id: int


class AssignmentBase(BaseModel):
    athlete_id: int
    template_id: int
    assigned_date: date
    start_date: date
    end_date: date
    repeat_weekdays: list[int] = Field(default_factory=lambda: DEFAULT_REPEAT_WEEKDAYS.copy())
    status: str = "active"
    notes: str | None = None

    @field_validator("repeat_weekdays", mode="before")
    @classmethod
    def normalize_repeat_weekdays(cls, value: object) -> list[int]:
        return _normalize_repeat_weekdays(value)


class AssignmentCreate(AssignmentBase):
    overrides: list[AssignmentOverrideCreate] = Field(default_factory=list)


class AssignmentUpdate(BaseModel):
    template_id: int | None = None
    assigned_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    repeat_weekdays: list[int] | None = None
    status: str | None = None
    notes: str | None = None

    @field_validator("repeat_weekdays", mode="before")
    @classmethod
    def normalize_repeat_weekdays(cls, value: object) -> list[int] | None:
        if value is None:
            return None
        return _normalize_repeat_weekdays(value)


class AssignmentRead(ORMModel, AssignmentBase):
    id: int
    athlete: AthleteRead
    template: PlanTemplateRead
    overrides: list[AssignmentOverrideRead] = Field(default_factory=list)


class BatchAssignmentCreate(BaseModel):
    athlete_ids: list[int]
    template_id: int
    assigned_date: date
    start_date: date
    end_date: date
    repeat_weekdays: list[int] = Field(default_factory=lambda: DEFAULT_REPEAT_WEEKDAYS.copy())
    status: str = "active"
    notes: str | None = None

    @field_validator("repeat_weekdays", mode="before")
    @classmethod
    def normalize_repeat_weekdays(cls, value: object) -> list[int]:
        return _normalize_repeat_weekdays(value)


class AssignmentPreviewItemRead(BaseModel):
    template_item_id: int
    module_id: int | None = None
    module_code: str | None = None
    module_title: str | None = None
    display_index: int | None = None
    display_code: str | None = None
    exercise_name: str
    load_mode_label: str
    computed_load: float | None = None
    basis_label: str | None = None
    status: str


class AssignmentPreviewRowRead(BaseModel):
    athlete: AthleteRead
    items: list[AssignmentPreviewItemRead]
    conflict_status: str = "none"
    conflict_dates: list[date] = Field(default_factory=list)
    conflict_message: str | None = None


class BatchAssignmentPreviewRead(BaseModel):
    template: PlanTemplateRead
    start_date: date
    end_date: date
    repeat_weekdays: list[int] = Field(default_factory=lambda: DEFAULT_REPEAT_WEEKDAYS.copy())
    rows: list[AssignmentPreviewRowRead]


class BatchAssignmentCancel(BaseModel):
    assignment_ids: list[int]


class AssignmentOverviewEntryRead(BaseModel):
    assignment_id: int
    athlete: AthleteRead
    notes: str | None = None


class AssignmentOverviewGroupRead(BaseModel):
    template: PlanTemplateRead
    start_date: date
    end_date: date
    repeat_weekdays: list[int] = Field(default_factory=lambda: DEFAULT_REPEAT_WEEKDAYS.copy())
    group_status: str
    entries: list[AssignmentOverviewEntryRead]
    athletes: list[AthleteRead]
    assignment_ids: list[int]
    notes: list[str]
    athlete_count: int


class AssignmentOverviewRead(BaseModel):
    assignment_groups: list[AssignmentOverviewGroupRead]
    unassigned_athletes: list[AthleteRead]
    assigned_count: int
    unassigned_count: int
    group_count: int
