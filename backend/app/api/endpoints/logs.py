from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.core.database import get_db
from app.schemas.logs import LogListRead
from app.services import log_service


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=LogListRead)
def list_logs(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    actor_name: str | None = Query(default=None),
    object_type: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_current_user),
):
    return log_service.list_logs(
        db,
        date_from=date_from,
        date_to=date_to,
        actor_name=actor_name,
        object_type=object_type,
        limit=limit,
        current_user=current_user,
    )
