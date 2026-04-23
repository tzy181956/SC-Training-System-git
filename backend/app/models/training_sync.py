from datetime import date

from sqlalchemy import JSON, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TrainingSyncConflict(BaseModel):
    __tablename__ = "training_sync_conflicts"

    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("athlete_plan_assignments.id"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("training_sessions.id"))
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(20), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    local_snapshot: Mapped[dict | None] = mapped_column(JSON)
    remote_snapshot: Mapped[dict | None] = mapped_column(JSON)
