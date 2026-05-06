from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request
from app.models import Athlete, TestRecord, User
from app.schemas.test_record import TestRecordCreate, TestRecordUpdate
from app.services import access_control_service, test_definition_service
from app.services.backup_service import create_pre_dangerous_operation_backup
from app.services.dangerous_operation_service import log_dangerous_operation


def list_test_records(db: Session, user: User) -> list[TestRecord]:
    query = db.query(TestRecord).options(
        joinedload(TestRecord.athlete).joinedload(Athlete.team),
        joinedload(TestRecord.athlete).joinedload(Athlete.sport),
    )
    visible_team_id = access_control_service.resolve_visible_team_id(user)
    if visible_team_id is not None:
        query = query.join(TestRecord.athlete).filter(Athlete.team_id == visible_team_id)
    return query.order_by(TestRecord.test_date.desc(), TestRecord.id.desc()).all()


def create_test_record(db: Session, user: User, payload: TestRecordCreate) -> TestRecord:
    access_control_service.get_accessible_athlete(db, user, payload.athlete_id)
    visible_team_id = access_control_service.resolve_visible_team_id(user)
    test_definition_service.require_visible_metric_definition(
        db,
        visible_team_id=visible_team_id,
        test_type_name=payload.test_type,
        metric_name=payload.metric_name,
    )

    record = TestRecord(**payload.model_dump())
    db.add(record)
    db.commit()
    return access_control_service.get_accessible_test_record(db, user, record.id)


def update_test_record(db: Session, user: User, record_id: int, payload: TestRecordUpdate) -> TestRecord:
    record = access_control_service.get_accessible_test_record(db, user, record_id)

    next_test_type = payload.test_type if payload.test_type is not None else record.test_type
    next_metric_name = payload.metric_name if payload.metric_name is not None else record.metric_name
    visible_team_id = access_control_service.resolve_visible_team_id(user)
    test_definition_service.require_visible_metric_definition(
        db,
        visible_team_id=visible_team_id,
        test_type_name=next_test_type,
        metric_name=next_metric_name,
    )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    return access_control_service.get_accessible_test_record(db, user, record.id)


def delete_test_records_batch(db: Session, user: User, record_ids: list[int], *, actor_name: str | None = None) -> int:
    normalized_ids = sorted({int(record_id) for record_id in record_ids if int(record_id) > 0})
    if not normalized_ids:
        raise bad_request("至少选择一条测试记录后才能删除。")

    query = (
        db.query(TestRecord)
        .options(
            joinedload(TestRecord.athlete).joinedload(Athlete.team),
            joinedload(TestRecord.athlete).joinedload(Athlete.sport),
        )
        .filter(TestRecord.id.in_(normalized_ids))
    )
    visible_team_id = access_control_service.resolve_visible_team_id(user)
    if visible_team_id is not None:
        query = query.join(TestRecord.athlete).filter(Athlete.team_id == visible_team_id)

    records = query.order_by(TestRecord.test_date.desc(), TestRecord.id.desc()).all()
    if not records:
        if visible_team_id is not None:
            existing_any = db.query(TestRecord.id).filter(TestRecord.id.in_(normalized_ids)).first()
            if existing_any:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="包含无权限删除的测试记录。")
        raise bad_request("未找到可删除的测试记录。")
    if len(records) != len(normalized_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="包含无权限删除的测试记录。")

    backup_result = create_pre_dangerous_operation_backup(label=f"delete_test_records_batch_{len(records)}")
    athletes = sorted({record.athlete.full_name for record in records if record.athlete})
    team_names = sorted({record.athlete.team.name for record in records if record.athlete and record.athlete.team})
    team_ids = sorted({record.athlete.team_id for record in records if record.athlete and record.athlete.team_id})
    metrics = sorted({record.metric_name for record in records})
    test_types = sorted({record.test_type for record in records})
    dates = sorted(record.test_date.isoformat() for record in records)

    deleted_count = len(records)
    for record in records:
        db.delete(record)

    log_dangerous_operation(
        db,
        operation_key="delete_test_records_batch",
        object_type="test_record",
        actor_name=actor_name,
        summary=f"批量删除测试记录 {deleted_count} 条",
        impact_scope={
            "deleted_count": deleted_count,
            "athletes": athletes,
            "team_ids": team_ids,
            "team_names": team_names,
            "test_types": test_types,
            "metrics": metrics,
            "date_from": dates[0] if dates else None,
            "date_to": dates[-1] if dates else None,
            "record_ids": normalized_ids,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()
    return deleted_count
