from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActiveMixin, BaseModel


def module_code_from_sort_order(sort_order: int | None) -> str:
    value = max(int(sort_order or 1), 1)
    code = ""
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        code = f"{chr(65 + remainder)}{code}"
    return code


class TrainingPlanTemplate(BaseModel, ActiveMixin):
    __tablename__ = "training_plan_templates"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sport_id: Mapped[int | None] = mapped_column(ForeignKey("sports.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    modules = relationship(
        "TrainingPlanTemplateModule",
        back_populates="template",
        order_by="TrainingPlanTemplateModule.sort_order",
        cascade="all, delete-orphan",
    )
    items = relationship(
        "TrainingPlanTemplateItem",
        back_populates="template",
        order_by="TrainingPlanTemplateItem.sort_order",
        cascade="all, delete-orphan",
        overlaps="module,items",
    )
    sport = relationship("Sport")
    team = relationship("Team")
    creator = relationship("User")


class TrainingPlanTemplateModule(BaseModel):
    __tablename__ = "training_plan_template_modules"

    template_id: Mapped[int] = mapped_column(ForeignKey("training_plan_templates.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)

    template = relationship("TrainingPlanTemplate", back_populates="modules")
    items = relationship(
        "TrainingPlanTemplateItem",
        back_populates="module",
        order_by="TrainingPlanTemplateItem.sort_order",
        cascade="all, delete",
        overlaps="template,items",
    )

    @property
    def module_code(self) -> str:
        return module_code_from_sort_order(self.sort_order)

    @property
    def display_label(self) -> str:
        return f"模块 {self.module_code}"


class TrainingPlanTemplateItem(BaseModel):
    __tablename__ = "training_plan_template_items"

    template_id: Mapped[int] = mapped_column(ForeignKey("training_plan_templates.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("training_plan_template_modules.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prescribed_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    prescribed_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    target_note: Mapped[str | None] = mapped_column(Text)
    is_main_lift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_auto_load: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    initial_load_mode: Mapped[str] = mapped_column(String(30), default="fixed_weight", nullable=False)
    initial_load_value: Mapped[float | None] = mapped_column(Float)
    initial_load_test_metric_definition_id: Mapped[int | None] = mapped_column(ForeignKey("test_metric_definitions.id"))
    progression_goal: Mapped[str | None] = mapped_column(String(30))
    progression_rules: Mapped[dict | None] = mapped_column(JSON)
    ai_adjust_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    template = relationship("TrainingPlanTemplate", back_populates="items", overlaps="items,module")
    module = relationship("TrainingPlanTemplateModule", back_populates="items", overlaps="template,items")
    exercise = relationship("Exercise")
    initial_load_test_metric_definition = relationship("TestMetricDefinition")

    @property
    def module_code(self) -> str | None:
        return self.module.module_code if self.module else None

    @property
    def module_title(self) -> str | None:
        return self.module.title if self.module else None

    @property
    def display_index(self) -> int | None:
        if not self.module:
            return None
        ordered_items = sorted(
            self.module.items or [],
            key=lambda item: (item.sort_order, item.id or 0),
        )
        for index, item in enumerate(ordered_items, start=1):
            if item.id == self.id:
                return index
        return None

    @property
    def display_code(self) -> str | None:
        if not self.module_code:
            return None
        display_index = self.display_index
        if display_index is None:
            return None
        return f"{self.module_code}.{display_index}"

    @property
    def initial_load_test_metric_definition_name(self) -> str | None:
        return self.initial_load_test_metric_definition.name if self.initial_load_test_metric_definition else None

    @property
    def initial_load_test_type_name(self) -> str | None:
        if not self.initial_load_test_metric_definition or not self.initial_load_test_metric_definition.test_type:
            return None
        return self.initial_load_test_metric_definition.test_type.name
