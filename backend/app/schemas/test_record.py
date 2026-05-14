from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.athlete import AthleteRead
from app.schemas.common import ORMModel


class TestRecordBase(BaseModel):
    athlete_id: int
    test_date: date
    test_type: str
    metric_name: str
    result_value: float
    result_text: str | None = None
    unit: str
    notes: str | None = None


class TestRecordCreate(TestRecordBase):
    pass


class TestRecordUpdate(BaseModel):
    test_date: date | None = None
    test_type: str | None = None
    metric_name: str | None = None
    result_value: float | None = None
    result_text: str | None = None
    unit: str | None = None
    notes: str | None = None


class TestRecordRead(ORMModel, TestRecordBase):
    id: int
    athlete: AthleteRead | None = None


class TestRecordListResponse(BaseModel):
    items: list[TestRecordRead] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0


class TestRecordImportRead(BaseModel):
    total_rows: int
    imported_rows: int
    skipped_rows: int


class TestRecordImportPreviewError(BaseModel):
    row_number: int
    message: str


class TestRecordImportPreviewRead(BaseModel):
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    skipped_rows: int
    error_rows: int
    errors: list[TestRecordImportPreviewError] = Field(default_factory=list)
    pending_records_data: list[dict[str, Any]] = Field(default_factory=list)
