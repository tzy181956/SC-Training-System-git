from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, TimestampRead


class ExerciseCategoryCreate(BaseModel):
    parent_id: int | None = None
    level: int
    name_zh: str
    name_en: str | None = None
    code: str | None = None
    sort_order: int = 0
    is_system: bool = False


class ExerciseCategoryUpdate(BaseModel):
    parent_id: int | None = None
    name_zh: str | None = None
    name_en: str | None = None
    code: str | None = None
    sort_order: int | None = None
    is_system: bool | None = None


class ExerciseCategoryBase(BaseModel):
    parent_id: int | None = None
    level: int
    name_zh: str
    name_en: str | None = None
    code: str
    sort_order: int = 0
    is_system: bool = False


class ExerciseCategoryRead(TimestampRead, ExerciseCategoryBase):
    pass


class ExerciseCategoryTreeNode(ExerciseCategoryRead):
    children: list["ExerciseCategoryTreeNode"] = Field(default_factory=list)


class ExerciseCategoryPathNode(ORMModel):
    id: int
    level: int
    name_zh: str
    name_en: str | None = None
    code: str


class ExerciseImportPreview(BaseModel):
    source_path: str
    total_rows: int
    valid_rows: int
    unique_codes: int
    level1_categories: int
    level2_categories: int
    exercises: int
    to_create: int
    to_update: int
    skipped_duplicates: int


ExerciseCategoryTreeNode.model_rebuild()
