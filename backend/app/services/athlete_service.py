from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import Athlete, AthletePlanAssignment, Sport, Team, TestRecord, TrainingSession
from app.schemas.athlete import AthleteCreate, AthleteUpdate, SportCreate, TeamCreate
from app.services import backup_service, dangerous_operation_service


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


def delete_athlete(db: Session, athlete_id: int, *, actor_name: str | None = None) -> None:
    athlete = (
        db.query(Athlete)
        .options(joinedload(Athlete.sport), joinedload(Athlete.team))
        .filter(Athlete.id == athlete_id)
        .first()
    )
    if not athlete:
        raise not_found("Athlete not found")

    assignment_refs = db.query(AthletePlanAssignment).filter(AthletePlanAssignment.athlete_id == athlete_id).count()
    session_refs = db.query(TrainingSession).filter(TrainingSession.athlete_id == athlete_id).count()
    test_refs = db.query(TestRecord).filter(TestRecord.athlete_id == athlete_id).count()
    if assignment_refs or session_refs or test_refs:
        reference_labels: list[str] = []
        if assignment_refs:
            reference_labels.append(f"{assignment_refs} 条计划分配")
        if session_refs:
            reference_labels.append(f"{session_refs} 条训练记录")
        if test_refs:
            reference_labels.append(f"{test_refs} 条测试记录")
        raise bad_request(f"该运动员仍被{', '.join(reference_labels)}引用，请先处理这些数据后再删除。")

    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_athlete_{athlete_id}")
    db.delete(athlete)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_athlete",
        object_type="athlete",
        object_id=athlete_id,
        actor_name=actor_name,
        summary=f"删除运动员“{athlete.full_name}”",
        impact_scope={
            "athlete_name": athlete.full_name,
            "sport_name": athlete.sport.name if athlete.sport else None,
            "team_name": athlete.team.name if athlete.team else None,
            "gender": athlete.gender,
            "is_active": athlete.is_active,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()
