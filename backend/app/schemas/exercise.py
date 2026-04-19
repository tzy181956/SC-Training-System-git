from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.schemas.tag import TagRead


class ExerciseBase(BaseModel):
    name: str
    alias: str | None = None
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
    tag_ids: list[int] = []


class ExerciseUpdate(BaseModel):
    name: str | None = None
    alias: str | None = None
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
    tags: list[ExerciseTagLinkRead] = []
