from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TrainingSession(BaseModel):
    __tablename__ = "training_sessions"
    __table_args__ = (UniqueConstraint("assignment_id", "session_date", name="uq_assignment_session_date"),)

    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("athlete_plan_assignments.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("training_plan_templates.id"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coach_note: Mapped[str | None] = mapped_column(Text)
    athlete_note: Mapped[str | None] = mapped_column(Text)
    session_rpe: Mapped[int | None] = mapped_column(Integer)
    session_feedback: Mapped[str | None] = mapped_column(Text)

    athlete = relationship("Athlete")
    assignment = relationship("AthletePlanAssignment")
    template = relationship("TrainingPlanTemplate")
    items = relationship(
        "TrainingSessionItem",
        back_populates="session",
        order_by="TrainingSessionItem.sort_order",
        cascade="all, delete-orphan",
    )


class TrainingSessionItem(BaseModel):
    __tablename__ = "training_session_items"

    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False)
    template_item_id: Mapped[int] = mapped_column(ForeignKey("training_plan_template_items.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prescribed_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    prescribed_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    target_note: Mapped[str | None] = mapped_column(Text)
    is_main_lift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_auto_load: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    initial_load: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    session = relationship("TrainingSession", back_populates="items")
    template_item = relationship("TrainingPlanTemplateItem")
    exercise = relationship("Exercise")
    records = relationship(
        "SetRecord",
        back_populates="session_item",
        cascade="all, delete-orphan",
        order_by="SetRecord.set_number",
    )


class SetRecord(BaseModel):
    __tablename__ = "set_records"
    __table_args__ = (UniqueConstraint("session_item_id", "set_number", name="uq_session_item_set_number"),)

    session_item_id: Mapped[int] = mapped_column(ForeignKey("training_session_items.id"), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_weight: Mapped[float | None] = mapped_column(Float)
    target_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_weight: Mapped[float] = mapped_column(Float, nullable=False)
    actual_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_rir: Mapped[int] = mapped_column(Integer, nullable=False)
    suggestion_weight: Mapped[float | None] = mapped_column(Float)
    suggestion_reason: Mapped[str | None] = mapped_column(Text)
    user_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    final_weight: Mapped[float] = mapped_column(Float, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    session_item = relationship("TrainingSessionItem", back_populates="records")
