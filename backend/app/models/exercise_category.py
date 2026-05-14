from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ExerciseCategory(BaseModel):
    __tablename__ = "exercise_categories"
    __table_args__ = (UniqueConstraint("parent_id", "level", "name_zh", name="uq_exercise_category_path"),)

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("exercise_categories.id"))
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    name_zh: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    parent = relationship("ExerciseCategory", remote_side="ExerciseCategory.id", back_populates="children")
    children = relationship(
        "ExerciseCategory",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="ExerciseCategory.sort_order, ExerciseCategory.name_zh",
    )
