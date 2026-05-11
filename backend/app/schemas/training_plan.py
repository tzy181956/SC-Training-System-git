from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.exercise import ExerciseRead


class PlanTemplateModuleBase(BaseModel):
    sort_order: int
    title: str | None = None
    note: str | None = None


class PlanTemplateModuleCreate(PlanTemplateModuleBase):
    pass


class PlanTemplateModuleUpdate(BaseModel):
    sort_order: int | None = None
    title: str | None = None
    note: str | None = None


class PlanTemplateItemBase(BaseModel):
    module_id: int
    exercise_id: int
    sort_order: int
    prescribed_sets: int
    prescribed_reps: int
    target_note: str | None = None
    is_main_lift: bool = False
    enable_auto_load: bool = False
    initial_load_mode: str = "fixed_weight"
    initial_load_value: float | None = None
    initial_load_test_metric_definition_id: int | None = None
    progression_goal: str | None = None
    progression_rules: dict | None = None
    ai_adjust_enabled: bool = False


class PlanTemplateItemCreate(PlanTemplateItemBase):
    pass


class PlanTemplateItemUpdate(BaseModel):
    module_id: int | None = None
    exercise_id: int | None = None
    sort_order: int | None = None
    prescribed_sets: int | None = None
    prescribed_reps: int | None = None
    target_note: str | None = None
    is_main_lift: bool | None = None
    enable_auto_load: bool | None = None
    initial_load_mode: str | None = None
    initial_load_value: float | None = None
    initial_load_test_metric_definition_id: int | None = None
    progression_goal: str | None = None
    progression_rules: dict | None = None
    ai_adjust_enabled: bool | None = None


class PlanTemplateBase(BaseModel):
    name: str
    description: str | None = None
    sport_id: int | None = None
    team_id: int | None = None
    is_active: bool = True


class PlanTemplateCreate(PlanTemplateBase):
    pass


class PlanTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    sport_id: int | None = None
    team_id: int | None = None
    is_active: bool | None = None


class PlanTemplateItemRead(ORMModel, PlanTemplateItemBase):
    id: int
    module_code: str | None = None
    module_title: str | None = None
    display_index: int | None = None
    display_code: str | None = None
    initial_load_test_metric_definition_name: str | None = None
    initial_load_test_type_name: str | None = None
    exercise: ExerciseRead | None = None


class PlanTemplateModuleRead(ORMModel, PlanTemplateModuleBase):
    id: int
    module_code: str
    display_label: str
    items: list[PlanTemplateItemRead] = []


class PlanTemplateRead(ORMModel, PlanTemplateBase):
    id: int
    created_by: int | None = None
    modules: list[PlanTemplateModuleRead] = []
    items: list[PlanTemplateItemRead] = []
