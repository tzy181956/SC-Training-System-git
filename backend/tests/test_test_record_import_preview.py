from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import (
    Athlete,
    Sport,
    Team,
    TestMetricDefinition as MetricDefinitionModel,
    TestRecord as RecordModel,
    TestTypeDefinition as TypeDefinitionModel,
    User,
)
from app.services.test_record_excel_service import (
    ATHLETE_CODE_HEADER,
    ATHLETE_NAME_HEADER,
    METRIC_NAME_HEADER,
    NOTES_HEADER,
    RESULT_TEXT_HEADER,
    RESULT_VALUE_HEADER,
    TEMPLATE_HEADERS,
    TEST_DATE_HEADER,
    TEST_TYPE_HEADER,
    UNIT_HEADER,
)


@pytest.fixture()
def db_session() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_import_preview_returns_errors_without_writing_database(
    asgi_client: Any,
    db_session: Session,
) -> None:
    data = _seed_import_data(db_session)
    workbook = _build_workbook(
        [
            _valid_row(result_value=100),
            _valid_row(metric_name="不存在项目", result_value=101),
        ]
    )

    with _api_overrides(current_user=data["coach"], db=db_session):
        response = asgi_client.post("/api/test-records/import/preview", files=_upload_file(workbook))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["valid_rows"] == 1
    assert payload["duplicate_rows"] == 0
    assert payload["skipped_rows"] == 0
    assert payload["error_rows"] == 1
    assert payload["errors"][0]["row_number"] == 3
    assert "不存在项目" in payload["errors"][0]["message"]
    assert db_session.query(RecordModel).count() == 0


def test_import_preview_counts_duplicate_rows_as_skipped(
    asgi_client: Any,
    db_session: Session,
) -> None:
    data = _seed_import_data(db_session)
    db_session.add(
        RecordModel(
            athlete_id=data["athlete"].id,
            test_date=date(2026, 3, 14),
            test_type="力量测试",
            metric_name="深蹲1RM",
            result_value=100,
            result_text=None,
            unit="kg",
            notes=None,
        )
    )
    db_session.commit()
    workbook = _build_workbook(
        [
            _valid_row(result_value=100),
            _valid_row(result_value=101),
        ]
    )

    with _api_overrides(current_user=data["coach"], db=db_session):
        response = asgi_client.post("/api/test-records/import/preview", files=_upload_file(workbook))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 2
    assert payload["valid_rows"] == 1
    assert payload["duplicate_rows"] == 1
    assert payload["skipped_rows"] == 1
    assert payload["error_rows"] == 0
    assert len(payload["pending_records_data"]) == 1
    assert db_session.query(RecordModel).count() == 1


def test_import_still_writes_valid_records(
    asgi_client: Any,
    db_session: Session,
) -> None:
    data = _seed_import_data(db_session)
    workbook = _build_workbook([_valid_row(result_value=100)])

    with _api_overrides(current_user=data["coach"], db=db_session):
        response = asgi_client.post("/api/test-records/import", files=_upload_file(workbook))

    assert response.status_code == 200
    assert response.json() == {"total_rows": 1, "imported_rows": 1, "skipped_rows": 0}
    record = db_session.query(RecordModel).one()
    assert record.athlete_id == data["athlete"].id
    assert record.test_date == date(2026, 3, 14)
    assert record.test_type == "力量测试"
    assert record.metric_name == "深蹲1RM"
    assert record.result_value == 100


def test_import_preview_returns_limited_valid_samples(
    asgi_client: Any,
    db_session: Session,
) -> None:
    data = _seed_import_data(db_session)
    workbook = _build_workbook([_valid_row(result_value=100 + index) for index in range(55)])

    with _api_overrides(current_user=data["coach"], db=db_session):
        response = asgi_client.post("/api/test-records/import/preview", files=_upload_file(workbook))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 55
    assert payload["valid_rows"] == 55
    assert payload["sample_limit"] == 50
    assert payload["has_more_valid_rows"] is True
    assert len(payload["sample_records"]) == 50
    assert len(payload["pending_records_data"]) == 50


def test_import_preview_returns_limited_errors(
    asgi_client: Any,
    db_session: Session,
) -> None:
    data = _seed_import_data(db_session)
    workbook = _build_workbook([
        _valid_row(metric_name=f"不存在项目{index}", result_value=100 + index)
        for index in range(55)
    ])

    with _api_overrides(current_user=data["coach"], db=db_session):
        response = asgi_client.post("/api/test-records/import/preview", files=_upload_file(workbook))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rows"] == 55
    assert payload["valid_rows"] == 0
    assert payload["error_rows"] == 55
    assert payload["error_limit"] == 50
    assert payload["has_more_errors"] is True
    assert len(payload["errors"]) == 50


def test_import_still_writes_all_valid_records_after_preview_slimming(
    asgi_client: Any,
    db_session: Session,
) -> None:
    data = _seed_import_data(db_session)
    workbook = _build_workbook([_valid_row(result_value=100 + index) for index in range(55)])

    with _api_overrides(current_user=data["coach"], db=db_session):
        response = asgi_client.post("/api/test-records/import", files=_upload_file(workbook))

    assert response.status_code == 200
    assert response.json() == {"total_rows": 55, "imported_rows": 55, "skipped_rows": 0}
    assert db_session.query(RecordModel).count() == 55


@contextmanager
def _api_overrides(current_user: User, db: Session):
    previous_user_override = app.dependency_overrides.get(get_current_user)
    previous_db_override = app.dependency_overrides.get(get_db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        if previous_user_override is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_user_override

        if previous_db_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_db_override


def _seed_import_data(db: Session) -> dict[str, Any]:
    sport = Sport(name="Basketball", code="basketball")
    team = Team(name="Test Team", code="test_team", sport=sport)
    coach = User(
        username="coach",
        password_hash="unused",
        display_name="Coach",
        role_code="coach",
        sport=sport,
        is_active=True,
    )
    athlete = Athlete(code="A001", full_name="张三", sport=sport, team=team)
    test_type = TypeDefinitionModel(name="力量测试", code="strength", sport=sport)
    metric = MetricDefinitionModel(
        test_type=test_type,
        name="深蹲1RM",
        code="squat_1rm",
        default_unit="kg",
    )
    db.add_all([sport, team, coach, athlete, test_type, metric])
    db.commit()
    return {"coach": coach, "athlete": athlete}


def _valid_row(*, metric_name: str = "深蹲1RM", result_value: float) -> dict[str, Any]:
    return {
        ATHLETE_CODE_HEADER: "A001",
        ATHLETE_NAME_HEADER: "张三",
        TEST_DATE_HEADER: "2026-03-14",
        TEST_TYPE_HEADER: "力量测试",
        METRIC_NAME_HEADER: metric_name,
        RESULT_VALUE_HEADER: result_value,
        RESULT_TEXT_HEADER: "",
        UNIT_HEADER: "kg",
        NOTES_HEADER: "",
    }


def _build_workbook(rows: list[dict[str, Any]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "测试数据导入模板"
    sheet.append(TEMPLATE_HEADERS)
    for row in rows:
        sheet.append([row.get(header, "") for header in TEMPLATE_HEADERS])

    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def _upload_file(content: bytes):
    return {
        "file": (
            "test-records.xlsx",
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
