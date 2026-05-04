from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.training_load import AthleteTrainingLoadRead
from app.services import access_control_service, training_load_service


router = APIRouter(prefix="/training-loads", tags=["training-loads"])


@router.get("/athletes/{athlete_id}", response_model=AthleteTrainingLoadRead)
def get_athlete_training_loads(
    athlete_id: int,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_athlete(db, current_user, athlete_id)
    end_date = date_to or date.today()
    start_date = date_from or (end_date - timedelta(days=29))
    return training_load_service.get_athlete_training_loads(db, athlete_id, start_date, end_date)
