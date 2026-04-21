from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.exercise import ExerciseRead


class PlanTemplateItemBase(BaseModel):
    exercise_id: int
    sort_order: int
    prescribed_sets: int
    prescribed_reps: int
    target_note: str | None = None
    is_main_lift: bool = False
    enable_auto_load: bool = False
    initial_load_mode: str = "fixed_weight"
    initial_load_value: float | None = None
    progression_goal: str | None = None
    progression_rules: dict | None = None
    ai_adjust_enabled: bool = False


class PlanTemplateItemCreate(PlanTemplateItemBase):
    pass


class PlanTemplateItemUpdate(BaseModel):
    exercise_id: int | None = None
    sort_order: int | None = None
    prescribed_sets: int | None = None
    prescribed_reps: int | None = None
    target_note: str | None = None
    is_main_lift: bool | None = None
    enable_auto_load: bool | None = None
    initial_load_mode: str | None = None
    initial_load_value: float | None = None
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
    exercise: ExerciseRead


class PlanTemplateRead(ORMModel, PlanTemplateBase):
    id: int
    created_by: int | None = None
    items: list[PlanTemplateItemRead] = []
