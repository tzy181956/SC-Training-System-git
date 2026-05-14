from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.exercise_category import (
    ExerciseCategoryCreate,
    ExerciseCategoryRead,
    ExerciseCategoryTreeNode,
    ExerciseCategoryUpdate,
    ExerciseImportPreview,
)
from app.services import dangerous_operation_service, exercise_category_service


router = APIRouter(prefix="/exercise-categories", tags=["exercise-categories"])


class ExosImportPayload(DangerousActionConfirm):
    replace_existing: bool = True


@router.get("", response_model=list[ExerciseCategoryRead])
def list_categories(db: Session = Depends(get_db), current_user: User = Depends(require_roles("coach"))):
    _ = current_user
    return exercise_category_service.list_categories(db)


@router.get("/tree", response_model=list[ExerciseCategoryTreeNode])
def tree_categories(db: Session = Depends(get_db), current_user: User = Depends(require_roles("coach"))):
    _ = current_user
    return exercise_category_service.list_category_tree(db)


@router.post("", response_model=ExerciseCategoryRead)
def create_category(
    payload: ExerciseCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return exercise_category_service.create_category(db, payload, actor_name=current_user.display_name)


@router.patch("/{category_id}", response_model=ExerciseCategoryRead)
def update_category(
    category_id: int,
    payload: ExerciseCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return exercise_category_service.update_category(db, category_id, payload, actor_name=current_user.display_name)


@router.delete("/{category_id}", response_model=dict[str, str])
def delete_category(
    category_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除动作分类")
    exercise_category_service.delete_category(db, category_id, actor_name=payload.actor_name or current_user.display_name)
    return {"message": "deleted"}


@router.post("/import-exos-preview", response_model=ExerciseImportPreview)
def preview_exos_import(
    _payload: ExosImportPayload | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    _ = current_user
    return exercise_category_service.preview_exos_import(db)


@router.post("/import-exos", response_model=ExerciseImportPreview)
def import_exos(
    payload: ExosImportPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    if payload.replace_existing:
        dangerous_operation_service.require_confirmation(payload, action_label="覆盖导入 EXOS 动作库")
    return exercise_category_service.import_exos_library(
        db,
        replace_existing=payload.replace_existing,
        actor_name=payload.actor_name or current_user.display_name,
    )
