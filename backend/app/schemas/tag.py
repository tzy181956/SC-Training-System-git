from pydantic import BaseModel

from app.schemas.common import ORMModel


class TagBase(BaseModel):
    category: str
    name: str
    code: str
    color: str | None = None
    sort_order: int = 0
    is_system: bool = False


class TagCreate(TagBase):
    pass


class TagRead(ORMModel, TagBase):
    id: int
