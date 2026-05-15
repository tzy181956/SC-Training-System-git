from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, JSON, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AthleteDailyTrainingLoad(BaseModel):
    __tablename__ = "athlete_daily_training_loads"
    __table_args__ = (UniqueConstraint("athlete_id", "load_date", name="uq_athlete_daily_training_loads_athlete_date"),)

    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False, index=True)
    load_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    total_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    total_srpe_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    source_session_ids: Mapped[list[int] | None] = mapped_column(JSON)

    athlete = relationship("Athlete")
