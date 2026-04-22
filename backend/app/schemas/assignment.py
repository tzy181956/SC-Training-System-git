from datetime import date

from pydantic import BaseModel

from app.schemas.athlete import AthleteRead
from app.schemas.common import ORMModel
from app.schemas.training_plan import PlanTemplateRead


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
    status: str = "active"
    notes: str | None = None


class AssignmentCreate(AssignmentBase):
    overrides: list[AssignmentOverrideCreate] = []


class AssignmentUpdate(BaseModel):
    template_id: int | None = None
    assigned_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    notes: str | None = None


class AssignmentRead(ORMModel, AssignmentBase):
    id: int
    athlete: AthleteRead
    template: PlanTemplateRead
    overrides: list[AssignmentOverrideRead] = []


class BatchAssignmentCreate(BaseModel):
    athlete_ids: list[int]
    template_id: int
    assigned_date: date
    start_date: date
    end_date: date
    status: str = "active"
    notes: str | None = None


class AssignmentPreviewItemRead(BaseModel):
    template_item_id: int
    exercise_name: str
    load_mode_label: str
    computed_load: float | None = None
    basis_label: str | None = None
    status: str


class AssignmentPreviewRowRead(BaseModel):
    athlete: AthleteRead
    items: list[AssignmentPreviewItemRead]


class BatchAssignmentPreviewRead(BaseModel):
    template: PlanTemplateRead
    start_date: date
    end_date: date
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
