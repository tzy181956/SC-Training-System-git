from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class TestTypeDefinition(BaseModel):
    __tablename__ = "test_type_definitions"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    notes: Mapped[str | None] = mapped_column(Text)

    metrics = relationship(
        "TestMetricDefinition",
        back_populates="test_type",
        cascade="all, delete-orphan",
        order_by="TestMetricDefinition.name",
    )


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
