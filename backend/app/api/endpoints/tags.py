from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.tag import TagCreate, TagRead
from app.services import exercise_service


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.list_tags(db)


@router.get("/grouped", response_model=dict[str, list[TagRead]])
def grouped_tags(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.grouped_tags(db)


@router.post("", response_model=TagRead)
def create_tag(payload: TagCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return exercise_service.create_tag(db, payload)
