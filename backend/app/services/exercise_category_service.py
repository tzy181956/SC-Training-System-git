from pathlib import Path

from sqlalchemy.orm import Session

from app.models import ExerciseCategory
from app.schemas.exercise_category import ExerciseImportPreview
from app.services import backup_service, dangerous_operation_service
from app.services.exercise_library_import import (
    EXOS_SOURCE_PATH,
    import_exos_library as import_exos_library_impl,
    list_categories as list_categories_impl,
    list_category_tree as list_category_tree_impl,
    preview_exos_import as preview_exos_import_impl,
)


def list_categories(db: Session) -> list[ExerciseCategory]:
    return list_categories_impl(db)


def list_category_tree(db: Session) -> list[ExerciseCategory]:
    return list_category_tree_impl(db)


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
    return result
