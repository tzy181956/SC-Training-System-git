from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampRead


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
    children: list["ExerciseCategoryTreeNode"] = []


class ExerciseCategoryPathNode(ORMModel):
    id: int
    level: int
    name_zh: str
    name_en: str | None = None
    code: str


class ExerciseImportPreview(BaseModel):
    source_path: str
    level1_categories: int
    level2_categories: int
    level3_categories: int
    exercises: int
    skipped_duplicates: int


ExerciseCategoryTreeNode.model_rebuild()
