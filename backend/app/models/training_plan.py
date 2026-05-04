from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActiveMixin, BaseModel


class TrainingPlanTemplate(BaseModel, ActiveMixin):
    __tablename__ = "training_plan_templates"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sport_id: Mapped[int | None] = mapped_column(ForeignKey("sports.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    items = relationship(
        "TrainingPlanTemplateItem",
        back_populates="template",
        order_by="TrainingPlanTemplateItem.sort_order",
        cascade="all, delete-orphan",
    )
    sport = relationship("Sport")
    team = relationship("Team")
    creator = relationship("User")


class TrainingPlanTemplateItem(BaseModel):
    __tablename__ = "training_plan_template_items"

    template_id: Mapped[int] = mapped_column(ForeignKey("training_plan_templates.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prescribed_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    prescribed_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    target_note: Mapped[str | None] = mapped_column(Text)
    is_main_lift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_auto_load: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    initial_load_mode: Mapped[str] = mapped_column(String(30), default="fixed_weight", nullable=False)
    initial_load_value: Mapped[float | None] = mapped_column(Float)
    progression_goal: Mapped[str | None] = mapped_column(String(30))
    progression_rules: Mapped[dict | None] = mapped_column(JSON)
    ai_adjust_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    template = relationship("TrainingPlanTemplate", back_populates="items")
    exercise = relationship("Exercise")
