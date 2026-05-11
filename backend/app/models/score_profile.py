from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ScoreProfile(BaseModel):
    __tablename__ = "score_profiles"
    __table_args__ = (UniqueConstraint("sport_id", "name", name="uq_score_profile_sport_name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sport_id: Mapped[int | None] = mapped_column(ForeignKey("sports.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"))

    sport = relationship("Sport")
    team = relationship("Team")
    dimensions = relationship(
        "ScoreDimension",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ScoreDimension.sort_order, ScoreDimension.id",
    )


class ScoreDimension(BaseModel):
    __tablename__ = "score_dimensions"
    __table_args__ = (UniqueConstraint("profile_id", "name", name="uq_score_dimension_profile_name"),)

    profile_id: Mapped[int] = mapped_column(ForeignKey("score_profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default=text("1"))

    profile = relationship("ScoreProfile", back_populates="dimensions")
    metrics = relationship(
        "ScoreDimensionMetric",
        back_populates="dimension",
        cascade="all, delete-orphan",
        order_by="ScoreDimensionMetric.sort_order, ScoreDimensionMetric.id",
    )


class ScoreDimensionMetric(BaseModel):
    __tablename__ = "score_dimension_metrics"
    __table_args__ = (
        UniqueConstraint("dimension_id", "test_metric_definition_id", name="uq_score_dimension_metric_unique_metric"),
    )

    dimension_id: Mapped[int] = mapped_column(ForeignKey("score_dimensions.id"), nullable=False)
    test_metric_definition_id: Mapped[int] = mapped_column(ForeignKey("test_metric_definitions.id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default=text("1"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))

    dimension = relationship("ScoreDimension", back_populates="metrics")
    test_metric_definition = relationship("TestMetricDefinition")
