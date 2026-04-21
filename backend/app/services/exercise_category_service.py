from pathlib import Path

from sqlalchemy.orm import Session

from app.models import ExerciseCategory
from app.schemas.exercise_category import ExerciseImportPreview
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


def import_exos_library(db: Session, *, source_path: Path | None = None, replace_existing: bool = True) -> ExerciseImportPreview:
    return import_exos_library_impl(db, source_path=source_path or EXOS_SOURCE_PATH, replace_existing=replace_existing)
