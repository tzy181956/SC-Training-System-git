from sqlalchemy import Boolean, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Exercise(BaseModel):
    __tablename__ = "exercises"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    alias: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(255))
    video_path: Mapped[str | None] = mapped_column(String(255))
    coaching_points: Mapped[str | None] = mapped_column(Text)
    common_errors: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    load_profile: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    default_increment: Mapped[float | None] = mapped_column(Float)
    is_main_lift_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tags = relationship("ExerciseTag", back_populates="exercise", cascade="all, delete-orphan")


class ExerciseTag(BaseModel):
    __tablename__ = "exercise_tags"
    __table_args__ = (UniqueConstraint("exercise_id", "tag_id", name="uq_exercise_tag"),)

    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False)

    exercise = relationship("Exercise", back_populates="tags")
    tag = relationship("Tag", back_populates="exercises")
