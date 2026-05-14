from sqlalchemy import JSON, Boolean, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


EXERCISE_VISIBILITY_PUBLIC = "public"
EXERCISE_VISIBILITY_PRIVATE = "private"


class Exercise(BaseModel):
    __tablename__ = "exercises"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    alias: Mapped[str | None] = mapped_column(String(120))
    code: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="custom_manual", nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(160))
    level1_category: Mapped[str | None] = mapped_column(String(120))
    level2_category: Mapped[str | None] = mapped_column(String(160))
    category_path: Mapped[str | None] = mapped_column(String(255))
    original_english_fields: Mapped[dict | None] = mapped_column(JSON)
    structured_tags: Mapped[dict | None] = mapped_column(JSON)
    search_keywords: Mapped[list | None] = mapped_column(JSON)
    tag_text: Mapped[str | None] = mapped_column(Text)
    raw_row: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(255))
    video_path: Mapped[str | None] = mapped_column(String(255))
    coaching_points: Mapped[str | None] = mapped_column(Text)
    common_errors: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    default_increment: Mapped[float | None] = mapped_column(Float)
    is_main_lift_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20),
        default=EXERCISE_VISIBILITY_PUBLIC,
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    tags = relationship("ExerciseTag", back_populates="exercise", cascade="all, delete-orphan")
    owner_user = relationship("User", foreign_keys=[owner_user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])

    @property
    def visibility_label(self) -> str:
        return "公共动作" if self.visibility == EXERCISE_VISIBILITY_PUBLIC else "自建动作"

    @property
    def owner_name(self) -> str | None:
        return self.owner_user.display_name if self.owner_user else None


class ExerciseTag(BaseModel):
    __tablename__ = "exercise_tags"
    __table_args__ = (UniqueConstraint("exercise_id", "tag_id", name="uq_exercise_tag"),)

    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False)

    exercise = relationship("Exercise", back_populates="tags")
    tag = relationship("Tag", back_populates="exercises")
