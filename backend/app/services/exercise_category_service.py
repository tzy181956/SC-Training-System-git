from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.models import Exercise, ExerciseCategory
from app.schemas.exercise_category import ExerciseCategoryCreate, ExerciseCategoryUpdate, ExerciseImportPreview
from app.services import backup_service, content_change_log_service, dangerous_operation_service
from app.services.exercise_library_import import (
    EXOS_SOURCE_PATH,
    _build_code,
    import_exos_library as import_exos_library_impl,
    list_categories as list_categories_impl,
    list_category_tree as list_category_tree_impl,
    preview_exos_import as preview_exos_import_impl,
)


PENDING_CATEGORY_NAME = "待定"


def list_categories(db: Session) -> list[ExerciseCategory]:
    return list_categories_impl(db)


def list_category_tree(db: Session) -> list[ExerciseCategory]:
    return list_category_tree_impl(db)


def create_category(db: Session, payload: ExerciseCategoryCreate, *, actor_name: str | None = None) -> ExerciseCategory:
    parent = _get_parent_for_level(db, payload.parent_id, payload.level)
    name_zh = _normalize_required_name(payload.name_zh, "分类名称不能为空")
    code = _resolve_category_code(db, parent, name_zh, payload.name_en, payload.code)
    _ensure_unique_category_path(db, parent.id if parent else None, payload.level, name_zh)
    _ensure_unique_category_code(db, code)

    category = ExerciseCategory(
        parent_id=parent.id if parent else None,
        level=payload.level,
        name_zh=name_zh,
        name_en=_normalize_optional_text(payload.name_en),
        code=code,
        sort_order=payload.sort_order,
        is_system=payload.is_system,
    )
    db.add(category)
    db.flush()
    _ensure_pending_descendants(db, category)
    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="exercise_category",
        object_id=category.id,
        object_label=category.name_zh,
        actor_name=actor_name,
        summary=f"新建动作分类“{category.name_zh}”",
        after_snapshot=_serialize_category(category),
    )
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category_id: int,
    payload: ExerciseCategoryUpdate,
    *,
    actor_name: str | None = None,
) -> ExerciseCategory:
    category = db.get(ExerciseCategory, category_id)
    if not category:
        raise not_found("动作分类不存在")
    before_snapshot = _serialize_category(category)
    updates = payload.model_dump(exclude_unset=True)

    next_parent_id = updates.get("parent_id", category.parent_id)
    parent = _get_parent_for_level(db, next_parent_id, category.level)
    next_name = _normalize_required_name(updates.get("name_zh", category.name_zh), "分类名称不能为空")
    next_code = _normalize_optional_text(updates.get("code", category.code)) or _resolve_category_code(
        db,
        parent,
        next_name,
        updates.get("name_en", category.name_en),
        None,
        current_category_id=category.id,
    )
    _ensure_unique_category_path(db, parent.id if parent else None, category.level, next_name, current_category_id=category.id)
    _ensure_unique_category_code(db, next_code, current_category_id=category.id)

    category.parent_id = parent.id if parent else None
    category.name_zh = next_name
    category.name_en = _normalize_optional_text(updates.get("name_en", category.name_en))
    category.code = next_code
    if "sort_order" in updates:
        category.sort_order = updates["sort_order"]
    if "is_system" in updates:
        category.is_system = bool(updates["is_system"])
    db.flush()
    _ensure_pending_descendants(db, category)
    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="exercise_category",
        object_id=category.id,
        object_label=category.name_zh,
        actor_name=actor_name,
        summary=f"更新动作分类“{category.name_zh}”",
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_category(category),
    )
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int, *, actor_name: str | None = None) -> None:
    category = db.get(ExerciseCategory, category_id)
    if not category:
        raise not_found("动作分类不存在")

    child_count = db.query(ExerciseCategory).filter(ExerciseCategory.parent_id == category_id).count()
    exercise_count = _count_exercises_for_category(db, category)
    if child_count or exercise_count:
        raise bad_request(f"该分类下仍有 {child_count} 个子分类、{exercise_count} 个动作，不能直接删除。")

    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_exercise_category_{category_id}")
    snapshot = _serialize_category(category)
    db.delete(category)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_exercise_category",
        object_type="exercise_category",
        object_id=category_id,
        actor_name=actor_name,
        summary=f"删除动作分类“{snapshot['name_zh']}”",
        impact_scope=snapshot,
        backup_path=backup_result.backup_path,
    )
    db.commit()


def ensure_pending_categories(db: Session) -> dict[str, int]:
    created = {"level1": 0, "level2": 0}
    existing_level1 = db.query(ExerciseCategory).filter(ExerciseCategory.level == 1).all()
    if not any(item.name_zh == PENDING_CATEGORY_NAME and item.parent_id is None for item in existing_level1):
        pending_root = _create_pending_category(db, None, 1)
        created["level1"] += 1
        existing_level1.append(pending_root)

    db.flush()
    for level1 in db.query(ExerciseCategory).filter(ExerciseCategory.level == 1).all():
        level2 = _ensure_pending_child(db, level1, 2)
        if level2:
            created["level2"] += 1

    db.commit()
    return created


def preview_exos_import(db: Session, source_path: Path | None = None) -> ExerciseImportPreview:
    return preview_exos_import_impl(db, source_path or EXOS_SOURCE_PATH)


def import_exos_library(
    db: Session,
    *,
    source_path: Path | None = None,
    replace_existing: bool = True,
    actor_name: str | None = None,
) -> ExerciseImportPreview:
    backup_path = None
    if replace_existing:
        backup_result = backup_service.create_pre_dangerous_operation_backup(label="import_exos_replace_existing")
        backup_path = backup_result.backup_path
    result = import_exos_library_impl(db, source_path=source_path or EXOS_SOURCE_PATH, replace_existing=replace_existing)
    if replace_existing:
        dangerous_operation_service.log_dangerous_operation(
            db,
            operation_key="import_exos_replace_existing",
            object_type="exercise_library",
            actor_name=actor_name,
            summary="覆盖导入 EXOS 动作库",
            impact_scope={
                "total_rows": result.total_rows,
                "new_categories": result.new_categories,
                "updated_categories": result.updated_categories,
                "new_exercises": result.new_exercises,
                "updated_exercises": result.updated_exercises,
            },
            backup_path=backup_path,
        )
        db.commit()
    ensure_pending_categories(db)
    return result


def _normalize_optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_required_name(value: object, message: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise bad_request(message)
    return text


def _get_parent_for_level(db: Session, parent_id: int | None, level: int) -> ExerciseCategory | None:
    if level not in {1, 2}:
        raise bad_request("动作分类层级只支持 1 或 2")
    if level == 1:
        if parent_id is not None:
            raise bad_request("一级分类不能指定父分类")
        return None
    if parent_id is None:
        raise bad_request("二级分类必须指定父分类")
    parent = db.get(ExerciseCategory, parent_id)
    if not parent:
        raise bad_request("父分类不存在")
    if parent.level != level - 1:
        raise bad_request("父分类层级不匹配")
    return parent


def _ensure_unique_category_path(
    db: Session,
    parent_id: int | None,
    level: int,
    name_zh: str,
    *,
    current_category_id: int | None = None,
) -> None:
    query = db.query(ExerciseCategory).filter(
        ExerciseCategory.parent_id == parent_id,
        ExerciseCategory.level == level,
        ExerciseCategory.name_zh == name_zh,
    )
    if current_category_id is not None:
        query = query.filter(ExerciseCategory.id != current_category_id)
    if query.first():
        raise bad_request("同一父分类下已存在同名分类")


def _ensure_unique_category_code(db: Session, code: str, *, current_category_id: int | None = None) -> None:
    query = db.query(ExerciseCategory).filter(ExerciseCategory.code == code)
    if current_category_id is not None:
        query = query.filter(ExerciseCategory.id != current_category_id)
    if query.first():
        raise bad_request("分类编码已存在，请换一个编码")


def _resolve_category_code(
    db: Session,
    parent: ExerciseCategory | None,
    name_zh: str,
    name_en: str | None,
    requested_code: str | None,
    *,
    current_category_id: int | None = None,
) -> str:
    normalized = _normalize_optional_text(requested_code)
    if normalized:
        return normalized

    base = _build_code(parent.code if parent else None, name_zh, name_en)
    code = base
    counter = 2
    while True:
        query = db.query(ExerciseCategory).filter(ExerciseCategory.code == code)
        if current_category_id is not None:
            query = query.filter(ExerciseCategory.id != current_category_id)
        if not query.first():
            return code
        code = f"{base}-{counter}"
        counter += 1


def _ensure_pending_descendants(db: Session, category: ExerciseCategory) -> None:
    if category.level == 1:
        _ensure_pending_child(db, category, 2)


def _ensure_pending_child(db: Session, parent: ExerciseCategory, level: int) -> ExerciseCategory | None:
    existing = (
        db.query(ExerciseCategory)
        .filter(
            ExerciseCategory.parent_id == parent.id,
            ExerciseCategory.level == level,
            ExerciseCategory.name_zh == PENDING_CATEGORY_NAME,
        )
        .first()
    )
    if existing:
        return None
    return _create_pending_category(db, parent, level)


def _create_pending_category(db: Session, parent: ExerciseCategory | None, level: int) -> ExerciseCategory:
    code_prefix = parent.code if parent else None
    base_code = f"{code_prefix}/pending" if code_prefix else "pending"
    code = base_code
    counter = 2
    while db.query(ExerciseCategory).filter(ExerciseCategory.code == code).first():
        code = f"{base_code}-{counter}"
        counter += 1
    sort_order = 9999
    category = ExerciseCategory(
        parent_id=parent.id if parent else None,
        level=level,
        name_zh=PENDING_CATEGORY_NAME,
        name_en="Pending",
        code=code,
        sort_order=sort_order,
        is_system=True,
    )
    db.add(category)
    db.flush()
    return category


def _serialize_category(category: ExerciseCategory) -> dict:
    return {
        "id": category.id,
        "parent_id": category.parent_id,
        "level": category.level,
        "name_zh": category.name_zh,
        "name_en": category.name_en,
        "code": category.code,
        "sort_order": category.sort_order,
        "is_system": category.is_system,
    }


def _count_exercises_for_category(db: Session, category: ExerciseCategory) -> int:
    if category.level == 1:
        return db.query(Exercise).filter(Exercise.level1_category == category.name_zh).count()
    if category.level == 2:
        query = db.query(Exercise).filter(Exercise.level2_category == category.name_zh)
        parent = db.get(ExerciseCategory, category.parent_id) if category.parent_id else None
        if parent:
            query = query.filter(Exercise.level1_category == parent.name_zh)
        return query.count()
    return 0
