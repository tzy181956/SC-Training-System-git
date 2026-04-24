from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.exceptions import not_found
from app.models import TestRecord
from app.schemas.dangerous_action import DeleteTestRecordsBatchPayload
from app.schemas.test_record import TestRecordCreate, TestRecordImportRead, TestRecordRead, TestRecordUpdate
from app.services import dangerous_operation_service, test_record_service
from app.services.test_record_excel_service import (
    build_import_template_workbook,
    build_test_record_library_workbook,
    import_test_records_from_workbook,
)


router = APIRouter(prefix="/test-records", tags=["test-records"])


@router.get("/template")
def download_test_record_template(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    content = build_import_template_workbook(db)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="test-record-import-template.xlsx"'},
    )


@router.post("/import", response_model=TestRecordImportRead)
async def import_test_records(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供导入文件")
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件导入")

    try:
        summary = import_test_records_from_workbook(db, await file.read())
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TestRecordImportRead(
        total_rows=summary.total_rows,
        imported_rows=summary.imported_rows,
        skipped_rows=summary.skipped_rows,
    )


@router.get("/export")
def export_test_record_library(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    content = build_test_record_library_workbook(db)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="test-record-library.xlsx"'},
    )


@router.get("", response_model=list[TestRecordRead])
def list_test_records(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return db.query(TestRecord).options(joinedload(TestRecord.athlete)).order_by(TestRecord.test_date.desc()).all()


@router.post("", response_model=TestRecordRead)
def create_test_record(payload: TestRecordCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    record = TestRecord(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{record_id}", response_model=TestRecordRead)
def update_test_record(record_id: int, payload: TestRecordUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    record = db.query(TestRecord).filter(TestRecord.id == record_id).first()
    if not record:
        raise not_found("Test record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.post("/delete-batch", response_model=dict[str, int])
def delete_test_records_batch(
    payload: DeleteTestRecordsBatchPayload,
    db: Session = Depends(get_db),
    _=Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="批量删除测试数据")
    deleted_count = test_record_service.delete_test_records_batch(
        db,
        payload.record_ids,
        actor_name=payload.actor_name,
    )
    return {"deleted_count": deleted_count}
