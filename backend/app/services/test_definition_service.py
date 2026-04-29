from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.test_definition_defaults import (
    DEFAULT_TEST_DEFINITION_CATALOG,
    build_auto_test_metric_code,
    build_auto_test_type_code,
)
from app.core.exceptions import bad_request, not_found
from app.models import TestMetricDefinition, TestRecord, TestTypeDefinition
from app.schemas.test_definition import (
    TestMetricDefinitionCreate,
    TestMetricDefinitionUpdate,
    TestTypeDefinitionCreate,
    TestTypeDefinitionUpdate,
)
from app.services import backup_service, dangerous_operation_service


def list_test_type_definitions(db: Session) -> list[TestTypeDefinition]:
    return (
        db.query(TestTypeDefinition)
        .options(joinedload(TestTypeDefinition.metrics))
        .order_by(TestTypeDefinition.name.asc(), TestTypeDefinition.id.asc())
        .all()
    )


def list_test_metric_definitions(db: Session) -> list[TestMetricDefinition]:
    return (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type))
        .order_by(TestMetricDefinition.name.asc(), TestMetricDefinition.id.asc())
        .all()
    )


def ensure_default_test_definition_catalog(db: Session, *, commit: bool = False) -> dict[str, int]:
    created_type_count = 0
    created_metric_count = 0
    updated_metric_unit_count = 0

    for definition in DEFAULT_TEST_DEFINITION_CATALOG:
        type_definition = _find_test_type_definition_by_name_or_code(db, definition["name"], definition["code"])
        if not type_definition:
            type_definition = TestTypeDefinition(
                name=definition["name"],
                code=definition["code"],
                notes=definition["notes"],
            )
            db.add(type_definition)
            db.flush()
            created_type_count += 1

        for metric in definition["metrics"]:
            metric_definition = _find_test_metric_definition_by_name_or_code(
                db,
                test_type_id=type_definition.id,
                name=metric["name"],
                code=metric["code"],
            )
            if not metric_definition:
                db.add(
                    TestMetricDefinition(
                        test_type_id=type_definition.id,
                        name=metric["name"],
                        code=metric["code"],
                        default_unit=metric["default_unit"],
                        is_lower_better=bool(metric.get("is_lower_better", False)),
                        notes=metric["notes"],
                    )
                )
                db.flush()
                created_metric_count += 1
                continue

            if not metric_definition.default_unit and metric["default_unit"]:
                metric_definition.default_unit = metric["default_unit"]
                updated_metric_unit_count += 1

    if commit:
        db.commit()

    return {
        "created_type_count": created_type_count,
        "created_metric_count": created_metric_count,
        "updated_metric_unit_count": updated_metric_unit_count,
    }


def backfill_test_definitions_from_records(db: Session, *, commit: bool = False) -> dict[str, int]:
    created_type_count = 0
    created_metric_count = 0
    updated_metric_unit_count = 0

    rows = (
        db.query(TestRecord.test_type, TestRecord.metric_name, TestRecord.unit)
        .distinct()
        .order_by(TestRecord.test_type.asc(), TestRecord.metric_name.asc())
        .all()
    )
    for test_type_name, metric_name, unit in rows:
        result = ensure_test_definition_for_record_snapshot(
            db,
            test_type_name=test_type_name,
            metric_name=metric_name,
            unit=unit,
        )
        created_type_count += 1 if result["created_type"] else 0
        created_metric_count += 1 if result["created_metric"] else 0
        updated_metric_unit_count += 1 if result["updated_metric_unit"] else 0

    if commit:
        db.commit()

    return {
        "created_type_count": created_type_count,
        "created_metric_count": created_metric_count,
        "updated_metric_unit_count": updated_metric_unit_count,
    }


def ensure_test_definition_for_record_snapshot(
    db: Session,
    *,
    test_type_name: str,
    metric_name: str,
    unit: str | None = None,
) -> dict[str, bool]:
    normalized_type_name = (test_type_name or "").strip()
    normalized_metric_name = (metric_name or "").strip()
    normalized_unit = (unit or "").strip() or None
    if not normalized_type_name or not normalized_metric_name:
        return {
            "created_type": False,
            "created_metric": False,
            "updated_metric_unit": False,
        }

    type_definition = db.query(TestTypeDefinition).filter(TestTypeDefinition.name == normalized_type_name).first()
    created_type = False
    if not type_definition:
        type_definition = TestTypeDefinition(
            name=normalized_type_name,
            code=build_auto_test_type_code(normalized_type_name),
            notes="由历史测试记录自动补建",
        )
        db.add(type_definition)
        db.flush()
        created_type = True

    metric_definition = (
        db.query(TestMetricDefinition)
        .filter(
            TestMetricDefinition.test_type_id == type_definition.id,
            TestMetricDefinition.name == normalized_metric_name,
        )
        .first()
    )
    created_metric = False
    updated_metric_unit = False
    if not metric_definition:
        metric_definition = TestMetricDefinition(
            test_type_id=type_definition.id,
            name=normalized_metric_name,
            code=build_auto_test_metric_code(normalized_type_name, normalized_metric_name),
            default_unit=normalized_unit,
            is_lower_better=False,
            notes="由历史测试记录自动补建",
        )
        db.add(metric_definition)
        db.flush()
        created_metric = True
    elif normalized_unit and not metric_definition.default_unit:
        metric_definition.default_unit = normalized_unit
        updated_metric_unit = True

    return {
        "created_type": created_type,
        "created_metric": created_metric,
        "updated_metric_unit": updated_metric_unit,
    }


def create_test_type_definition(db: Session, payload: TestTypeDefinitionCreate) -> TestTypeDefinition:
    definition = TestTypeDefinition(
        name=payload.normalized_name(),
        code=payload.normalized_code(),
        notes=payload.normalized_notes(),
    )
    db.add(definition)
    _commit_or_raise(db, conflict_message="测试类型名称或编码已存在，请修改后重试。")
    db.refresh(definition)
    return get_test_type_definition(db, definition.id)


def update_test_type_definition(db: Session, definition_id: int, payload: TestTypeDefinitionUpdate) -> TestTypeDefinition:
    definition = db.query(TestTypeDefinition).filter(TestTypeDefinition.id == definition_id).first()
    if not definition:
        raise not_found("测试类型不存在")

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        definition.name = payload.normalized_name()
    if "code" in updates:
        definition.code = payload.normalized_code()
    if "notes" in updates:
        definition.notes = payload.normalized_notes()

    _commit_or_raise(db, conflict_message="测试类型名称或编码已存在，请修改后重试。")
    return get_test_type_definition(db, definition.id)


def delete_test_type_definition(db: Session, definition_id: int, *, actor_name: str | None = None) -> None:
    definition = db.query(TestTypeDefinition).options(joinedload(TestTypeDefinition.metrics)).filter(TestTypeDefinition.id == definition_id).first()
    if not definition:
        raise not_found("测试类型不存在")

    metric_count = len(definition.metrics or [])
    if metric_count:
        raise bad_request(f"该测试类型下仍有 {metric_count} 个测试项目，请先处理这些二级分类后再删除。")

    historical_record_count = db.query(TestRecord).filter(TestRecord.test_type == definition.name).count()
    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_test_type_definition_{definition_id}")
    db.delete(definition)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_test_type_definition",
        object_type="test_type_definition",
        object_id=definition_id,
        actor_name=actor_name,
        summary=f"删除测试类型“{definition.name}”",
        impact_scope={
            "test_type_name": definition.name,
            "test_type_code": definition.code,
            "historical_record_count": historical_record_count,
            "note": "删除测试类型定义不会删除已有历史测试记录。",
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def get_test_type_definition(db: Session, definition_id: int) -> TestTypeDefinition:
    definition = (
        db.query(TestTypeDefinition)
        .options(joinedload(TestTypeDefinition.metrics))
        .filter(TestTypeDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise not_found("测试类型不存在")
    return definition


def create_test_metric_definition(db: Session, payload: TestMetricDefinitionCreate) -> TestMetricDefinition:
    test_type = db.query(TestTypeDefinition).filter(TestTypeDefinition.id == payload.test_type_id).first()
    if not test_type:
        raise bad_request("所属测试类型不存在，请先刷新后重试。")

    definition = TestMetricDefinition(
        test_type_id=test_type.id,
        name=payload.normalized_name(),
        code=payload.normalized_code(),
        default_unit=payload.normalized_default_unit(),
        is_lower_better=payload.is_lower_better,
        notes=payload.normalized_notes(),
    )
    db.add(definition)
    _commit_or_raise(db, conflict_message="该测试类型下已存在同名或同编码的测试项目，请修改后重试。")
    return get_test_metric_definition(db, definition.id)


def update_test_metric_definition(db: Session, definition_id: int, payload: TestMetricDefinitionUpdate) -> TestMetricDefinition:
    definition = db.query(TestMetricDefinition).filter(TestMetricDefinition.id == definition_id).first()
    if not definition:
        raise not_found("测试项目不存在")

    if payload.test_type_id is not None:
        test_type = db.query(TestTypeDefinition).filter(TestTypeDefinition.id == payload.test_type_id).first()
        if not test_type:
            raise bad_request("所属测试类型不存在，请先刷新后重试。")
        definition.test_type_id = test_type.id

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        definition.name = payload.normalized_name()
    if "code" in updates:
        definition.code = payload.normalized_code()
    if "default_unit" in updates:
        definition.default_unit = payload.normalized_default_unit()
    if "is_lower_better" in updates:
        definition.is_lower_better = bool(payload.is_lower_better)
    if "notes" in updates:
        definition.notes = payload.normalized_notes()

    _commit_or_raise(db, conflict_message="该测试类型下已存在同名或同编码的测试项目，请修改后重试。")
    return get_test_metric_definition(db, definition.id)


def delete_test_metric_definition(db: Session, definition_id: int, *, actor_name: str | None = None) -> None:
    definition = db.query(TestMetricDefinition).options(joinedload(TestMetricDefinition.test_type)).filter(TestMetricDefinition.id == definition_id).first()
    if not definition:
        raise not_found("测试项目不存在")

    historical_record_count = db.query(TestRecord).filter(
        TestRecord.test_type == (definition.test_type.name if definition.test_type else ""),
        TestRecord.metric_name == definition.name,
    ).count()
    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_test_metric_definition_{definition_id}")
    db.delete(definition)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_test_metric_definition",
        object_type="test_metric_definition",
        object_id=definition_id,
        actor_name=actor_name,
        summary=f"删除测试项目“{definition.name}”",
        impact_scope={
            "metric_name": definition.name,
            "metric_code": definition.code,
            "test_type_name": definition.test_type.name if definition.test_type else None,
            "historical_record_count": historical_record_count,
            "note": "删除测试项目定义不会删除已有历史测试记录。",
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def get_test_metric_definition(db: Session, definition_id: int) -> TestMetricDefinition:
    definition = (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type))
        .filter(TestMetricDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise not_found("测试项目不存在")
    return definition


def _commit_or_raise(db: Session, *, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(conflict_message) from exc


def _find_test_type_definition_by_name_or_code(db: Session, name: str, code: str) -> TestTypeDefinition | None:
    return (
        db.query(TestTypeDefinition)
        .filter((TestTypeDefinition.name == name) | (TestTypeDefinition.code == code))
        .first()
    )


def _find_test_metric_definition_by_name_or_code(
    db: Session,
    *,
    test_type_id: int,
    name: str,
    code: str,
) -> TestMetricDefinition | None:
    return (
        db.query(TestMetricDefinition)
        .filter(
            TestMetricDefinition.test_type_id == test_type_id,
            (TestMetricDefinition.name == name) | (TestMetricDefinition.code == code),
        )
        .first()
    )
