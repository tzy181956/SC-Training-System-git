from datetime import date

from sqlalchemy import JSON, Date, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AthletePlanAssignment(BaseModel):
    __tablename__ = "athlete_plan_assignments"

    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("training_plan_templates.id"), nullable=False)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    repeat_weekdays: Mapped[list[int] | None] = mapped_column(JSON, default=lambda: [1, 2, 3, 4, 5, 6, 7])
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    athlete = relationship("Athlete")
    template = relationship("TrainingPlanTemplate")
    overrides = relationship("AssignmentItemOverride", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentItemOverride(BaseModel):
    __tablename__ = "assignment_item_overrides"
    __table_args__ = (UniqueConstraint("assignment_id", "template_item_id", name="uq_assignment_item_override"),)

    assignment_id: Mapped[int] = mapped_column(ForeignKey("athlete_plan_assignments.id"), nullable=False)
    template_item_id: Mapped[int] = mapped_column(ForeignKey("training_plan_template_items.id"), nullable=False)
    initial_load_override: Mapped[float] = mapped_column(Float, nullable=False)

    assignment = relationship("AthletePlanAssignment", back_populates="overrides")
    template_item = relationship("TrainingPlanTemplateItem")
