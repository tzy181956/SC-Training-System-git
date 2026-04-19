from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.training_report import TrainingReportRead
from app.services import training_report_service


router = APIRouter(prefix="/training-reports", tags=["training-reports"])


@router.get("", response_model=TrainingReportRead)
def get_training_report(
    athlete_id: int = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    end_date = date_to or date.today()
    start_date = date_from or (end_date - timedelta(days=29))
    return training_report_service.get_training_report(db, athlete_id, start_date, end_date)
