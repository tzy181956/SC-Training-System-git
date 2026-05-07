from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TestTypeDefinition(BaseModel):
    __tablename__ = "test_type_definitions"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    sport_id: Mapped[int | None] = mapped_column(ForeignKey("sports.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    sport = relationship("Sport", back_populates="test_type_definitions")
    team = relationship("Team", back_populates="test_type_definitions")
    metrics = relationship(
        "TestMetricDefinition",
        back_populates="test_type",
        cascade="all, delete-orphan",
        order_by="TestMetricDefinition.name",
    )

    @property
    def is_system(self) -> bool:
        return self.sport_id is None

    @property
    def sport_name(self) -> str | None:
        return self.sport.name if self.sport else None


class TestMetricDefinition(BaseModel):
    __tablename__ = "test_metric_definitions"
    __table_args__ = (
        UniqueConstraint("test_type_id", "name", name="uq_test_metric_definition_type_name"),
        UniqueConstraint("test_type_id", "code", name="uq_test_metric_definition_type_code"),
    )

    test_type_id: Mapped[int] = mapped_column(ForeignKey("test_type_definitions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    default_unit: Mapped[str | None] = mapped_column(String(30))
    is_lower_better: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    notes: Mapped[str | None] = mapped_column(Text)

    test_type = relationship("TestTypeDefinition", back_populates="metrics")
