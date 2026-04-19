from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TestRecord(BaseModel):
    __tablename__ = "test_records"

    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    test_date: Mapped[date] = mapped_column(Date, nullable=False)
    test_type: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    result_value: Mapped[float] = mapped_column(Float, nullable=False)
    result_text: Mapped[str | None] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    athlete = relationship("Athlete")
