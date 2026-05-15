from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DashboardMemo(BaseModel):
    __tablename__ = "dashboard_memos"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", server_default=text("''"), nullable=False)
    source: Mapped[str] = mapped_column(String(30), default="dashboard", server_default=text("'dashboard'"), nullable=False)

    user = relationship("User")
