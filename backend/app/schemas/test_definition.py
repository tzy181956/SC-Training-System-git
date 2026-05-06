from typing import Literal

from pydantic import BaseModel, Field, computed_field

from app.schemas.common import ORMModel


def _require_text(value: object, *, field_label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_label}不能为空")
    return text


def _normalize_optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


class TestMetricDefinitionSummaryRead(ORMModel):
    id: int
    test_type_id: int
    name: str
    code: str
    default_unit: str | None = None
    is_lower_better: bool = False
    notes: str | None = None

    @computed_field(return_type=Literal["higher", "lower"])
    @property
    def direction(self) -> Literal["higher", "lower"]:
        return "lower" if self.is_lower_better else "higher"


class TestTypeDefinitionSummaryRead(ORMModel):
    id: int
    name: str
    code: str
    team_id: int | None = None
    team_name: str | None = None
    is_system: bool
    notes: str | None = None


class TestTypeDefinitionRead(TestTypeDefinitionSummaryRead):
    metrics: list[TestMetricDefinitionSummaryRead] = Field(default_factory=list)


class TestMetricDefinitionRead(TestMetricDefinitionSummaryRead):
    test_type: TestTypeDefinitionSummaryRead | None = None


class TestDefinitionCatalogRead(BaseModel):
    types: list[TestTypeDefinitionRead]


class TestTypeDefinitionCreate(BaseModel):
    name: str
    code: str
    team_id: int | None = None
    notes: str | None = None

    def normalized_name(self) -> str:
        return _require_text(self.name, field_label="测试类型名称")

    def normalized_code(self) -> str:
        return _require_text(self.code, field_label="测试类型编码")

    def normalized_notes(self) -> str | None:
        return _normalize_optional_text(self.notes)

    def normalized_team_id(self) -> int | None:
        return self.team_id


class TestTypeDefinitionUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    notes: str | None = None

    def normalized_name(self) -> str | None:
        if self.name is None:
            return None
        return _require_text(self.name, field_label="测试类型名称")

    def normalized_code(self) -> str | None:
        if self.code is None:
            return None
        return _require_text(self.code, field_label="测试类型编码")

    def normalized_notes(self) -> str | None:
        if self.notes is None:
            return None
        return _normalize_optional_text(self.notes)


class TestMetricDefinitionCreate(BaseModel):
    test_type_id: int
    name: str
    code: str
    default_unit: str | None = None
    is_lower_better: bool = False
    notes: str | None = None

    def normalized_name(self) -> str:
        return _require_text(self.name, field_label="测试项目名称")

    def normalized_code(self) -> str:
        return _require_text(self.code, field_label="测试项目编码")

    def normalized_default_unit(self) -> str | None:
        return _normalize_optional_text(self.default_unit)

    def normalized_notes(self) -> str | None:
        return _normalize_optional_text(self.notes)


class TestMetricDefinitionUpdate(BaseModel):
    test_type_id: int | None = None
    name: str | None = None
    code: str | None = None
    default_unit: str | None = None
    is_lower_better: bool | None = None
    notes: str | None = None

    def normalized_name(self) -> str | None:
        if self.name is None:
            return None
        return _require_text(self.name, field_label="测试项目名称")

    def normalized_code(self) -> str | None:
        if self.code is None:
            return None
        return _require_text(self.code, field_label="测试项目编码")

    def normalized_default_unit(self) -> str | None:
        if self.default_unit is None:
            return None
        return _normalize_optional_text(self.default_unit)

    def normalized_notes(self) -> str | None:
        if self.notes is None:
            return None
        return _normalize_optional_text(self.notes)
