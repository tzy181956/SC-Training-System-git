from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class DangerousOperationLog(BaseModel):
    __tablename__ = "dangerous_operation_logs"

    operation_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    object_id: Mapped[int | None] = mapped_column(Integer, index=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="api")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact_scope: Mapped[dict | None] = mapped_column(JSON)
    confirmation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmation_phrase: Mapped[str | None] = mapped_column(String(80))
    backup_path: Mapped[str | None] = mapped_column(String(255))
    extra_data: Mapped[dict | None] = mapped_column(JSON)
