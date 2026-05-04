from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActiveMixin, BaseModel


class Athlete(BaseModel, ActiveMixin):
    __tablename__ = "athletes"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sport_id: Mapped[int | None] = mapped_column(ForeignKey("sports.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    position: Mapped[str | None] = mapped_column(String(100))
    height: Mapped[float | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    body_fat_percentage: Mapped[float | None] = mapped_column(nullable=True)
    wingspan: Mapped[float | None] = mapped_column(nullable=True)
    standing_reach: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)

    user = relationship("User")
    sport = relationship("Sport", back_populates="athletes")
    team = relationship("Team", back_populates="athletes")
