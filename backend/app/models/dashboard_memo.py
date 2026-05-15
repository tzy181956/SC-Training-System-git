from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DashboardMemo(BaseModel):
    __tablename__ = "dashboard_memos"
    __table_args__ = (UniqueConstraint("user_id", name="uq_dashboard_memos_user_id"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", server_default=text("''"), nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="dashboard", server_default=text("'dashboard'"), nullable=False)

    user = relationship("User")
