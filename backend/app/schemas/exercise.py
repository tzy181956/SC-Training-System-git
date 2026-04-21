from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.exercise_category import ExerciseCategoryPathNode
from app.schemas.tag import TagRead


class ExerciseBase(BaseModel):
    name: str
    alias: str | None = None
    code: str | None = None
    source_type: str = "custom_manual"
    name_en: str | None = None
    level1_category: str | None = None
    level2_category: str | None = None
    base_movement: str | None = None
    category_path: str | None = None
    original_english_fields: dict | None = None
    structured_tags: dict = Field(default_factory=dict)
    search_keywords: list[str] = Field(default_factory=list)
    tag_text: str | None = None
    raw_row: dict | None = None
    base_category_id: int | None = None
    description: str | None = None
    video_url: str | None = None
    video_path: str | None = None
    coaching_points: str | None = None
    common_errors: str | None = None
    notes: str | None = None
    load_profile: str = "general"
    default_increment: float | None = None
    is_main_lift_candidate: bool = False


class ExerciseCreate(ExerciseBase):
    tag_ids: list[int] = Field(default_factory=list)


class ExerciseUpdate(BaseModel):
    name: str | None = None
    alias: str | None = None
    code: str | None = None
    source_type: str | None = None
    name_en: str | None = None
    level1_category: str | None = None
    level2_category: str | None = None
    base_movement: str | None = None
    category_path: str | None = None
    original_english_fields: dict | None = None
    structured_tags: dict | None = None
    search_keywords: list[str] | None = None
    tag_text: str | None = None
    raw_row: dict | None = None
    base_category_id: int | None = None
    description: str | None = None
    video_url: str | None = None
    video_path: str | None = None
    coaching_points: str | None = None
    common_errors: str | None = None
    notes: str | None = None
    load_profile: str | None = None
    default_increment: float | None = None
    is_main_lift_candidate: bool | None = None
    tag_ids: list[int] | None = None


class ExerciseTagLinkRead(ORMModel):
    id: int
    tag: TagRead


class ExerciseRead(ORMModel, ExerciseBase):
    id: int
    base_category: ExerciseCategoryPathNode | None = None
    tags: list[ExerciseTagLinkRead] = Field(default_factory=list)
