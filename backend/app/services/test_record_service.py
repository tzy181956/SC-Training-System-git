from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request
from app.models import Athlete, TestRecord
from app.services.backup_service import create_pre_dangerous_operation_backup
from app.services.dangerous_operation_service import log_dangerous_operation


def delete_test_records_batch(db: Session, record_ids: list[int], *, actor_name: str | None = None) -> int:
    normalized_ids = sorted({int(record_id) for record_id in record_ids if int(record_id) > 0})
    if not normalized_ids:
        raise bad_request("至少选择一条测试记录后才能删除")

    records = (
        db.query(TestRecord)
        .options(joinedload(TestRecord.athlete).joinedload(Athlete.team))
        .filter(TestRecord.id.in_(normalized_ids))
        .order_by(TestRecord.test_date.desc(), TestRecord.id.desc())
        .all()
    )
    if not records:
        raise bad_request("未找到可删除的测试记录")

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
