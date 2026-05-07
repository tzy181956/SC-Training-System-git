from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.core.test_definition_defaults import (
    DEFAULT_TEST_DEFINITION_CATALOG,
)
from app.models import Sport, TestMetricDefinition, TestRecord, TestTypeDefinition, User
from app.schemas.test_definition import (
    TestMetricDefinitionCreate,
    TestMetricDefinitionUpdate,
    TestTypeDefinitionCreate,
    TestTypeDefinitionUpdate,
)
from app.services import access_control_service, backup_service, dangerous_operation_service


def list_test_type_definitions(db: Session, *, visible_sport_id: int | None = None) -> list[TestTypeDefinition]:
    query = (
        db.query(TestTypeDefinition)
        .options(
            joinedload(TestTypeDefinition.sport),
            joinedload(TestTypeDefinition.metrics),
        )
    )
    if visible_sport_id is not None:
        query = query.filter(or_(TestTypeDefinition.sport_id.is_(None), TestTypeDefinition.sport_id == visible_sport_id))
    return (
        query.order_by(
            TestTypeDefinition.sport_id.asc(),
            TestTypeDefinition.name.asc(),
            TestTypeDefinition.id.asc(),
        )
        .all()
    )


def list_test_metric_definitions(db: Session, *, visible_sport_id: int | None = None) -> list[TestMetricDefinition]:
    query = (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type).joinedload(TestTypeDefinition.sport))
        .join(TestMetricDefinition.test_type)
    )
    if visible_sport_id is not None:
        query = query.filter(or_(TestTypeDefinition.sport_id.is_(None), TestTypeDefinition.sport_id == visible_sport_id))
    return query.order_by(TestTypeDefinition.name.asc(), TestMetricDefinition.name.asc(), TestMetricDefinition.id.asc()).all()


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
                sport_id=None,
                team_id=None,
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
    _ = db
    if commit:
        return {"created_type_count": 0, "created_metric_count": 0, "updated_metric_unit_count": 0}
    return {"created_type_count": 0, "created_metric_count": 0, "updated_metric_unit_count": 0}


def ensure_test_definition_for_record_snapshot(
    db: Session,
    *,
    test_type_name: str,
    metric_name: str,
    unit: str | None = None,
) -> dict[str, bool]:
    _ = (db, test_type_name, metric_name, unit)
    return {
        "created_type": False,
        "created_metric": False,
        "updated_metric_unit": False,
    }


def create_test_type_definition(db: Session, payload: TestTypeDefinitionCreate, user: User) -> TestTypeDefinition:
    sport_id = _resolve_definition_sport_id(db, payload, user)
    normalized_name = payload.normalized_name()
    normalized_code = payload.normalized_code()

    _ensure_test_type_name_and_code_unique(db, name=normalized_name, code=normalized_code)

    definition = TestTypeDefinition(
        name=normalized_name,
        code=normalized_code,
        sport_id=sport_id,
        team_id=None,
        notes=payload.normalized_notes(),
    )
    db.add(definition)
    _commit_or_raise(db, conflict_message="测试类型名称或编码已存在，请修改后重试。")
    db.refresh(definition)
    return get_test_type_definition(db, definition.id)


def update_test_type_definition(
    db: Session,
    definition_id: int,
    payload: TestTypeDefinitionUpdate,
    user: User,
) -> TestTypeDefinition:
    definition = access_control_service.get_accessible_test_type_definition(
        db,
        user,
        definition_id,
        allow_system_read=False,
        allow_system_write=False,
    )

    next_name = payload.normalized_name() if payload.name is not None else definition.name
    next_code = payload.normalized_code() if payload.code is not None else definition.code
    _ensure_test_type_name_and_code_unique(
        db,
        name=next_name,
        code=next_code,
        exclude_id=definition.id,
    )

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        definition.name = next_name
    if "code" in updates:
        definition.code = next_code
    if "notes" in updates:
        definition.notes = payload.normalized_notes()

    _commit_or_raise(db, conflict_message="测试类型名称或编码已存在，请修改后重试。")
    return get_test_type_definition(db, definition.id)


def delete_test_type_definition(db: Session, definition_id: int, user: User, *, actor_name: str | None = None) -> None:
    definition = access_control_service.get_accessible_test_type_definition(
        db,
        user,
        definition_id,
        allow_system_read=False,
        allow_system_write=False,
    )

    metric_count = len(definition.metrics or [])
    if metric_count:
        raise bad_request(f"该测试类型下仍有 {metric_count} 个测试项目，请先处理这些测试项目后再删除。")

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
            "sport_id": definition.sport_id,
            "sport_name": definition.sport_name,
            "historical_record_count": historical_record_count,
            "note": "删除测试类型定义不会删除已有历史测试记录。",
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def get_test_type_definition(db: Session, definition_id: int) -> TestTypeDefinition:
    definition = (
        db.query(TestTypeDefinition)
        .options(
            joinedload(TestTypeDefinition.sport),
            joinedload(TestTypeDefinition.metrics),
        )
        .filter(TestTypeDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise not_found("Test type definition not found")
    return definition


def create_test_metric_definition(db: Session, payload: TestMetricDefinitionCreate, user: User) -> TestMetricDefinition:
    test_type = access_control_service.get_accessible_test_type_definition(
        db,
        user,
        payload.test_type_id,
        allow_system_read=False,
        allow_system_write=False,
    )

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


def update_test_metric_definition(
    db: Session,
    definition_id: int,
    payload: TestMetricDefinitionUpdate,
    user: User,
) -> TestMetricDefinition:
    definition = access_control_service.get_accessible_test_metric_definition(
        db,
        user,
        definition_id,
        allow_system_read=False,
        allow_system_write=False,
    )

    if payload.test_type_id is not None and payload.test_type_id != definition.test_type_id:
        test_type = access_control_service.get_accessible_test_type_definition(
            db,
            user,
            payload.test_type_id,
            allow_system_read=False,
            allow_system_write=False,
        )
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


def delete_test_metric_definition(db: Session, definition_id: int, user: User, *, actor_name: str | None = None) -> None:
    definition = access_control_service.get_accessible_test_metric_definition(
        db,
        user,
        definition_id,
        allow_system_read=False,
        allow_system_write=False,
    )

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
            "sport_id": definition.test_type.sport_id if definition.test_type else None,
            "sport_name": definition.test_type.sport_name if definition.test_type else None,
            "historical_record_count": historical_record_count,
            "note": "删除测试项目定义不会删除已有历史测试记录。",
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def get_test_metric_definition(db: Session, definition_id: int) -> TestMetricDefinition:
    definition = (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type).joinedload(TestTypeDefinition.sport))
        .filter(TestMetricDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise not_found("Test metric definition not found")
    return definition


def require_visible_metric_definition(
    db: Session,
    *,
    visible_sport_id: int | None,
    test_type_name: str,
    metric_name: str,
) -> TestMetricDefinition:
    normalized_type_name = (test_type_name or "").strip()
    normalized_metric_name = (metric_name or "").strip()
    if not normalized_type_name or not normalized_metric_name:
        raise bad_request("测试类型和测试项目不能为空。")

    query = (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type).joinedload(TestTypeDefinition.sport))
        .join(TestMetricDefinition.test_type)
        .filter(
            TestTypeDefinition.name == normalized_type_name,
            TestMetricDefinition.name == normalized_metric_name,
        )
    )
    if visible_sport_id is not None:
        query = query.filter(or_(TestTypeDefinition.sport_id.is_(None), TestTypeDefinition.sport_id == visible_sport_id))
    definition = query.first()
    if definition:
        return definition

    raise bad_request("测试项目不存在，或当前账号无权使用该测试项目，请先检查测试项目目录。")


def _commit_or_raise(db: Session, *, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(conflict_message) from exc


def _resolve_definition_sport_id(db: Session, payload: TestTypeDefinitionCreate, user: User) -> int | None:
    if access_control_service.is_admin(user):
        sport_id = payload.normalized_sport_id()
    else:
        sport_id = access_control_service.ensure_sport_bound_user(user)
    if sport_id is not None:
        _ensure_sport_exists(db, sport_id)
    return sport_id


def _ensure_sport_exists(db: Session, sport_id: int) -> None:
    if not db.query(Sport.id).filter(Sport.id == sport_id).first():
        raise bad_request("绑定项目不存在，请刷新后重试。")


def _ensure_test_type_name_and_code_unique(
    db: Session,
    *,
    name: str,
    code: str,
    exclude_id: int | None = None,
) -> None:
    duplicate_name_query = db.query(TestTypeDefinition.id).filter(TestTypeDefinition.name == name)
    duplicate_code_query = db.query(TestTypeDefinition.id).filter(TestTypeDefinition.code == code)
    if exclude_id is not None:
        duplicate_name_query = duplicate_name_query.filter(TestTypeDefinition.id != exclude_id)
        duplicate_code_query = duplicate_code_query.filter(TestTypeDefinition.id != exclude_id)

    if duplicate_name_query.first():
        raise bad_request("测试类型名称已存在，请修改后重试。")
    if duplicate_code_query.first():
        raise bad_request("测试类型编码已存在，请修改后重试。")


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
