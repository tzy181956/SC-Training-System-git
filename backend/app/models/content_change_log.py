from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ContentChangeLog(BaseModel):
    __tablename__ = "content_change_logs"

    action_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    object_id: Mapped[int | None] = mapped_column(Integer, index=True)
    object_label: Mapped[str | None] = mapped_column(String(160))
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    before_snapshot: Mapped[dict | None] = mapped_column(JSON)
    after_snapshot: Mapped[dict | None] = mapped_column(JSON)
    extra_context: Mapped[dict | None] = mapped_column(JSON)

    team = relationship("Team")
