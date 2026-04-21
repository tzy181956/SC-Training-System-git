from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.exercise import ExerciseCreate, ExerciseFacetValuesRead, ExerciseRead, ExerciseUpdate
from app.services import exercise_service


router = APIRouter(prefix="/exercises", tags=["exercises"])


class ExerciseTagPayload(BaseModel):
    tag_id: int


@router.get("", response_model=list[ExerciseRead])
def list_exercises(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.list_exercises(db)


@router.get("/facets", response_model=ExerciseFacetValuesRead)
def list_exercise_facets(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.list_exercise_facets(db)


@router.post("", response_model=ExerciseRead)
def create_exercise(payload: ExerciseCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.create_exercise(db, payload)


@router.get("/{exercise_id}", response_model=ExerciseRead)
def get_exercise(exercise_id: int, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.get_exercise(db, exercise_id)


@router.patch("/{exercise_id}", response_model=ExerciseRead)
def update_exercise(exercise_id: int, payload: ExerciseUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.update_exercise(db, exercise_id, payload)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    exercise_service.delete_exercise(db, exercise_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{exercise_id}/tags", response_model=ExerciseRead)
def attach_tag(exercise_id: int, payload: ExerciseTagPayload, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.attach_tag(db, exercise_id, payload.tag_id)


@router.delete("/{exercise_id}/tags/{tag_id}", response_model=ExerciseRead)
def detach_tag(exercise_id: int, tag_id: int, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.detach_tag(db, exercise_id, tag_id)
