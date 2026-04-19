from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.athlete import AthleteCreate, AthleteRead, AthleteUpdate, SportCreate, SportRead, TeamCreate, TeamRead
from app.services import athlete_service


router = APIRouter(tags=["athletes"])


@router.get("/sports", response_model=list[SportRead])
def list_sports(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.list_sports(db)


@router.post("/sports", response_model=SportRead)
def create_sport(payload: SportCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.create_sport(db, payload)


@router.get("/teams", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.list_teams(db)


@router.post("/teams", response_model=TeamRead)
def create_team(payload: TeamCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.create_team(db, payload)


@router.get("/athletes", response_model=list[AthleteRead])
def list_athletes(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.list_athletes(db)


@router.post("/athletes", response_model=AthleteRead)
def create_athlete(payload: AthleteCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.create_athlete(db, payload)


@router.get("/athletes/{athlete_id}", response_model=AthleteRead)
def get_athlete(athlete_id: int, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.get_athlete(db, athlete_id)


@router.patch("/athletes/{athlete_id}", response_model=AthleteRead)
def update_athlete(athlete_id: int, payload: AthleteUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return athlete_service.update_athlete(db, athlete_id, payload)
