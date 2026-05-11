from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.dangerous_action import DeleteTestRecordsBatchPayload, DeleteTestRecordsByFilterPayload
from app.schemas.test_record import (
    TestRecordCreate,
    TestRecordImportRead,
    TestRecordListResponse,
    TestRecordRead,
    TestRecordUpdate,
)
from app.services import dangerous_operation_service, test_record_service
from app.services.test_record_excel_service import (
    build_import_template_workbook,
    build_test_record_library_workbook,
    import_test_records_from_workbook,
)


router = APIRouter(prefix="/test-records", tags=["test-records"])


@router.get("/template")
def download_test_record_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    content = build_import_template_workbook(db, current_user)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="test-record-import-template.xlsx"'},
    )


@router.post("/import", response_model=TestRecordImportRead)
async def import_test_records(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供导入文件。")
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xlsm 文件导入。")

    try:
        summary = import_test_records_from_workbook(db, await file.read(), current_user)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TestRecordImportRead(
        total_rows=summary.total_rows,
        imported_rows=summary.imported_rows,
        skipped_rows=summary.skipped_rows,
    )


@router.get("/export")
def export_test_record_library(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    content = build_test_record_library_workbook(db, current_user)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="test-record-library.xlsx"'},
    )


@router.get("", response_model=TestRecordListResponse)
def list_test_records(
    athlete_keyword: str | None = Query(default=None),
    metric_keyword: str | None = Query(default=None),
    test_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_record_service.list_test_record_library(
        db,
        current_user,
        athlete_keyword=athlete_keyword,
        metric_keyword=metric_keyword,
        test_type=test_type,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TestRecordRead)
def create_test_record(
    payload: TestRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_record_service.create_test_record(db, current_user, payload)


@router.patch("/{record_id}", response_model=TestRecordRead)
def update_test_record(
    record_id: int,
    payload: TestRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return test_record_service.update_test_record(db, current_user, record_id, payload)


@router.post("/delete-batch", response_model=dict[str, int])
def delete_test_records_batch(
    payload: DeleteTestRecordsBatchPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="批量删除测试数据")
    deleted_count = test_record_service.delete_test_records_batch(
        db,
        current_user,
        payload.record_ids,
        actor_name=payload.actor_name or current_user.display_name,
    )
    return {"deleted_count": deleted_count}


@router.post("/delete-filtered", response_model=dict[str, int])
def delete_test_records_filtered(
    payload: DeleteTestRecordsByFilterPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="批量删除测试数据")
    deleted_count = test_record_service.delete_test_records_by_filter(
        db,
        current_user,
        athlete_keyword=payload.athlete_keyword,
        metric_keyword=payload.metric_keyword,
        test_type=payload.test_type,
        actor_name=payload.actor_name or current_user.display_name,
    )
    return {"deleted_count": deleted_count}
