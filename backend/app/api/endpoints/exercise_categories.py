from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.exercise_category import ExerciseCategoryRead, ExerciseCategoryTreeNode, ExerciseImportPreview
from app.services import exercise_category_service


router = APIRouter(prefix="/exercise-categories", tags=["exercise-categories"])


class ExosImportPayload(BaseModel):
    replace_existing: bool = True


@router.get("", response_model=list[ExerciseCategoryRead])
def list_categories(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_category_service.list_categories(db)


@router.get("/tree", response_model=list[ExerciseCategoryTreeNode])
def tree_categories(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_category_service.list_category_tree(db)


@router.post("/import-exos-preview", response_model=ExerciseImportPreview)
def preview_exos_import(_payload: ExosImportPayload | None = None, _=Depends(require_roles("coach"))):
    return exercise_category_service.preview_exos_import()


@router.post("/import-exos", response_model=ExerciseImportPreview)
def import_exos(payload: ExosImportPayload, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_category_service.import_exos_library(db, replace_existing=payload.replace_existing)
