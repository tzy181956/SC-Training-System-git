from __future__ import annotations

from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Query, Session, joinedload

from app.core.exceptions import bad_request
from app.models import Athlete, TestRecord, User
from app.schemas.test_record import TestRecordCreate, TestRecordListResponse, TestRecordUpdate
from app.services import access_control_service, test_definition_service
from app.services.backup_service import create_pre_dangerous_operation_backup
from app.services.dangerous_operation_service import log_dangerous_operation


def _normalize_query_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _build_visible_test_records_query(
    db: Session,
    user: User,
    *,
    athlete_keyword: str | None = None,
    metric_keyword: str | None = None,
    test_type: str | None = None,
) -> Query:
    query = db.query(TestRecord).options(
        joinedload(TestRecord.athlete).joinedload(Athlete.team),
        joinedload(TestRecord.athlete).joinedload(Athlete.sport),
    )

    visible_sport_id = access_control_service.resolve_visible_sport_id(user)
    if visible_sport_id is not None:
        query = query.join(TestRecord.athlete).filter(Athlete.sport_id == visible_sport_id)
    else:
        query = query.join(TestRecord.athlete)

    normalized_athlete_keyword = _normalize_query_text(athlete_keyword)
    normalized_metric_keyword = _normalize_query_text(metric_keyword)
    normalized_test_type = _normalize_query_text(test_type)

    if normalized_athlete_keyword:
        query = query.filter(Athlete.full_name.ilike(f"%{normalized_athlete_keyword}%"))
    if normalized_metric_keyword:
        query = query.filter(TestRecord.metric_name.ilike(f"%{normalized_metric_keyword}%"))
    if normalized_test_type:
        query = query.filter(TestRecord.test_type == normalized_test_type)

    return query


def list_test_records(db: Session, user: User) -> list[TestRecord]:
    query = _build_visible_test_records_query(db, user)
    return query.order_by(TestRecord.test_date.desc(), TestRecord.id.desc()).all()


def list_test_record_library(
    db: Session,
    user: User,
    *,
    athlete_keyword: str | None = None,
    metric_keyword: str | None = None,
    test_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> TestRecordListResponse:
    query = _build_visible_test_records_query(
        db,
        user,
        athlete_keyword=athlete_keyword,
        metric_keyword=metric_keyword,
        test_type=test_type,
    )
    total = query.order_by(None).with_entities(func.count(TestRecord.id)).scalar() or 0
    total_pages = ceil(total / page_size) if total else 0
    offset = (page - 1) * page_size

    items = (
        query.order_by(TestRecord.test_date.desc(), TestRecord.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return TestRecordListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_test_record(db: Session, user: User, payload: TestRecordCreate) -> TestRecord:
    access_control_service.get_accessible_athlete(db, user, payload.athlete_id)
    visible_sport_id = access_control_service.resolve_visible_sport_id(user)
    test_definition_service.require_visible_metric_definition(
        db,
        visible_sport_id=visible_sport_id,
        include_system=access_control_service.is_admin(user),
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
    visible_sport_id = access_control_service.resolve_visible_sport_id(user)
    test_definition_service.require_visible_metric_definition(
        db,
        visible_sport_id=visible_sport_id,
        include_system=access_control_service.is_admin(user),
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

    query = _build_visible_test_records_query(db, user).filter(TestRecord.id.in_(normalized_ids))
    records = query.order_by(TestRecord.test_date.desc(), TestRecord.id.desc()).all()
    if not records:
        visible_sport_id = access_control_service.resolve_visible_sport_id(user)
        if visible_sport_id is not None:
            existing_any = db.query(TestRecord.id).filter(TestRecord.id.in_(normalized_ids)).first()
            if existing_any:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="包含无权限删除的测试记录。")
        raise bad_request("未找到可删除的测试记录。")
    if len(records) != len(normalized_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="包含无权限删除的测试记录。")

    return _delete_test_records(db, records, actor_name=actor_name)


def delete_test_records_by_filter(
    db: Session,
    user: User,
    *,
    athlete_keyword: str | None = None,
    metric_keyword: str | None = None,
    test_type: str | None = None,
    actor_name: str | None = None,
) -> int:
    query = _build_visible_test_records_query(
        db,
        user,
        athlete_keyword=athlete_keyword,
        metric_keyword=metric_keyword,
        test_type=test_type,
    )
    records = query.order_by(TestRecord.test_date.desc(), TestRecord.id.desc()).all()
    if not records:
        raise bad_request("当前筛选条件下没有可删除的测试记录。")
    return _delete_test_records(db, records, actor_name=actor_name)


def _delete_test_records(db: Session, records: list[TestRecord], *, actor_name: str | None = None) -> int:
    backup_result = create_pre_dangerous_operation_backup(label=f"delete_test_records_batch_{len(records)}")
    athletes = sorted({record.athlete.full_name for record in records if record.athlete})
    team_names = sorted({record.athlete.team.name for record in records if record.athlete and record.athlete.team})
    team_ids = sorted({record.athlete.team_id for record in records if record.athlete and record.athlete.team_id})
    metrics = sorted({record.metric_name for record in records})
    test_types = sorted({record.test_type for record in records})
    dates = sorted(record.test_date.isoformat() for record in records)
    record_ids = sorted(record.id for record in records)

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
            "record_ids": record_ids,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()
    return deleted_count
