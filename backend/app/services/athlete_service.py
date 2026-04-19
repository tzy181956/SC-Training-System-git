from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import Athlete, Sport, Team
from app.schemas.athlete import AthleteCreate, AthleteUpdate, SportCreate, TeamCreate


def list_sports(db: Session) -> list[Sport]:
    return db.query(Sport).order_by(Sport.name).all()


def create_sport(db: Session, payload: SportCreate) -> Sport:
    sport = Sport(**payload.model_dump())
    db.add(sport)
    db.commit()
    db.refresh(sport)
    return sport


def list_teams(db: Session) -> list[Team]:
    return db.query(Team).options(joinedload(Team.sport)).order_by(Team.name).all()


def create_team(db: Session, payload: TeamCreate) -> Team:
    team = Team(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def list_athletes(db: Session) -> list[Athlete]:
    return db.query(Athlete).options(joinedload(Athlete.sport), joinedload(Athlete.team)).order_by(Athlete.full_name).all()


def create_athlete(db: Session, payload: AthleteCreate) -> Athlete:
    athlete = Athlete(**payload.model_dump())
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return get_athlete(db, athlete.id)


def get_athlete(db: Session, athlete_id: int) -> Athlete:
    athlete = (
        db.query(Athlete)
        .options(joinedload(Athlete.sport), joinedload(Athlete.team))
        .filter(Athlete.id == athlete_id)
        .first()
    )
    if not athlete:
        raise not_found("Athlete not found")
    return athlete


def update_athlete(db: Session, athlete_id: int, payload: AthleteUpdate) -> Athlete:
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise not_found("Athlete not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(athlete, key, value)
    db.commit()
    return get_athlete(db, athlete.id)
