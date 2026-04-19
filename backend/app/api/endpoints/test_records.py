from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.exceptions import not_found
from app.models import TestRecord
from app.schemas.test_record import TestRecordCreate, TestRecordRead, TestRecordUpdate


router = APIRouter(prefix="/test-records", tags=["test-records"])


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
