from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Sport(BaseModel):
    __tablename__ = "sports"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    teams = relationship("Team", back_populates="sport")
    athletes = relationship("Athlete", back_populates="sport")


class Team(BaseModel):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("sport_id", "code", name="uq_team_sport_code"),)

    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    sport = relationship("Sport", back_populates="teams")
    athletes = relationship("Athlete", back_populates="team")
