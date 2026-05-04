from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TrainingSessionEditLog(BaseModel):
    __tablename__ = "training_session_edit_logs"

    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False, index=True)
    session_item_id: Mapped[int | None] = mapped_column(ForeignKey("training_session_items.id"), index=True)
    set_record_id: Mapped[int | None] = mapped_column(ForeignKey("set_records.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    object_type: Mapped[str] = mapped_column(String(30), nullable=False)
    object_id: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    before_snapshot: Mapped[dict | None] = mapped_column(JSON)
    after_snapshot: Mapped[dict | None] = mapped_column(JSON)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
