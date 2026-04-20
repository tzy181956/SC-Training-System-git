from datetime import date

from pydantic import BaseModel

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


class TestRecordImportRead(BaseModel):
    total_rows: int
    imported_rows: int
    skipped_rows: int
