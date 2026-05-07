from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import (
    Athlete,
    AthletePlanAssignment,
    Sport,
    Team,
    TestRecord,
    TrainingPlanTemplate,
    TrainingSession,
    User,
)
from app.schemas.athlete import AthleteCreate, AthleteUpdate, SportCreate, TeamCreate
from app.services import backup_service, dangerous_operation_service

ATHLETE_CODE_PREFIX = "ATH"
ATHLETE_CODE_WIDTH = 6


def list_sports(db: Session) -> list[Sport]:
    return db.query(Sport).order_by(Sport.name).all()


def create_sport(db: Session, payload: SportCreate) -> Sport:
    sport = Sport(
        name=_require_text(payload.name, field_label="项目名称"),
        code=_require_text(payload.code, field_label="项目编码"),
        notes=_normalize_optional_text(payload.notes),
    )
    db.add(sport)
    _commit_or_raise(db, conflict_message="项目编码已存在，请修改项目名称后重试。")
    db.refresh(sport)
    return sport


def list_teams(db: Session, sport_id: int | None = None) -> list[Team]:
    query = db.query(Team).options(joinedload(Team.sport)).order_by(Team.name)
    if sport_id is not None:
        query = query.filter(Team.sport_id == sport_id)
    return query.all()


def create_team(db: Session, payload: TeamCreate) -> Team:
    sport = db.query(Sport).filter(Sport.id == payload.sport_id).first()
    if not sport:
        raise bad_request("所属项目不存在，请先刷新后重试。")

    team = Team(
        sport_id=sport.id,
        name=_require_text(payload.name, field_label="队伍名称"),
        code=_require_text(payload.code, field_label="队伍编码"),
        notes=_normalize_optional_text(payload.notes),
    )
    db.add(team)
    _commit_or_raise(db, conflict_message="该项目下已存在同编码的队伍，请修改队伍名称后重试。")
    return (
        db.query(Team)
        .options(joinedload(Team.sport))
        .filter(Team.id == team.id)
        .first()
    )


def list_athletes(
    db: Session,
    *,
    sport_id: int | None = None,
    team_id: int | None = None,
) -> list[Athlete]:
    query = db.query(Athlete).options(joinedload(Athlete.sport), joinedload(Athlete.team)).order_by(Athlete.full_name)
    if sport_id is not None:
        query = query.filter(Athlete.sport_id == sport_id)
    if team_id is not None:
        query = query.filter(Athlete.team_id == team_id)
    return query.all()


def create_athlete(db: Session, payload: AthleteCreate) -> Athlete:
    payload_data = payload.model_dump()
    requested_code = _normalize_optional_code(payload_data.pop("code", None))
    resolved_sport_id, resolved_team_id = _resolve_athlete_scope(
        db,
        sport_id=payload_data.pop("sport_id", None),
        team_id=payload_data.pop("team_id", None),
    )
    athlete = Athlete(
        **payload_data,
        sport_id=resolved_sport_id,
        team_id=resolved_team_id,
        code=requested_code or _build_temporary_athlete_code(),
    )
    db.add(athlete)
    db.flush()
    if not requested_code:
        athlete.code = build_athlete_code(athlete.id)
    _commit_or_raise(db, conflict_message="运动员编码已存在，请修改后重试。")
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

    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates:
        normalized_code = _normalize_optional_code(updates.pop("code"))
        if not normalized_code:
            raise bad_request("运动员编码不能为空")
        athlete.code = normalized_code

    if "sport_id" in updates or "team_id" in updates:
        resolved_sport_id, resolved_team_id = _resolve_athlete_scope(
            db,
            sport_id=updates.pop("sport_id", athlete.sport_id),
            team_id=updates.pop("team_id", athlete.team_id),
        )
        athlete.sport_id = resolved_sport_id
        athlete.team_id = resolved_team_id

    for key, value in updates.items():
        setattr(athlete, key, value)
    _commit_or_raise(db, conflict_message="运动员编码已存在，请修改后重试。")
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


def delete_sport(db: Session, sport_id: int, *, actor_name: str | None = None) -> None:
    sport = db.query(Sport).filter(Sport.id == sport_id).first()
    if not sport:
        raise not_found("项目不存在")

    athlete_refs = db.query(Athlete).filter(Athlete.sport_id == sport_id).count()
    team_refs = db.query(Team).filter(Team.sport_id == sport_id).count()
    template_refs = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.sport_id == sport_id).count()
    reference_summary = _build_reference_summary(
        [
            (athlete_refs, "名运动员"),
            (team_refs, "支队伍"),
            (template_refs, "个训练模板"),
        ]
    )
    if reference_summary:
        raise bad_request(f"该项目仍被{reference_summary}引用，请先处理关联数据后再删除。")

    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_sport_{sport_id}")
    db.delete(sport)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_sport",
        object_type="sport",
        object_id=sport_id,
        actor_name=actor_name,
        summary=f"删除项目“{sport.name}”",
        impact_scope={
            "sport_name": sport.name,
            "sport_code": sport.code,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def delete_team(db: Session, team_id: int, *, actor_name: str | None = None) -> None:
    team = db.query(Team).options(joinedload(Team.sport)).filter(Team.id == team_id).first()
    if not team:
        raise not_found("队伍不存在")

    athlete_refs = db.query(Athlete).filter(Athlete.team_id == team_id).count()
    template_refs = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.team_id == team_id).count()
    reference_summary = _build_reference_summary(
        [
            (athlete_refs, "名运动员"),
            (template_refs, "个训练模板"),
        ]
    )
    if reference_summary:
        raise bad_request(f"该队伍仍被{reference_summary}引用，请先处理关联数据后再删除。")

    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_team_{team_id}")
    db.delete(team)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_team",
        object_type="team",
        object_id=team_id,
        actor_name=actor_name,
        summary=f"删除队伍“{team.name}”",
        impact_scope={
            "team_name": team.name,
            "team_code": team.code,
            "sport_name": team.sport.name if team.sport else None,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def _require_text(value: str | None, *, field_label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise bad_request(f"{field_label}不能为空")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _normalize_optional_code(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None


def build_athlete_code(athlete_id: int) -> str:
    return f"{ATHLETE_CODE_PREFIX}-{athlete_id:0{ATHLETE_CODE_WIDTH}d}"


def _build_temporary_athlete_code() -> str:
    return f"TMP-{ATHLETE_CODE_PREFIX}-{uuid4().hex[:12].upper()}"


def _commit_or_raise(db: Session, *, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(conflict_message) from exc


def _build_reference_summary(reference_pairs: list[tuple[int, str]]) -> str:
    parts = [f"{count}{label}" for count, label in reference_pairs if count]
    return "、".join(parts)


def _resolve_athlete_scope(
    db: Session,
    *,
    sport_id: int | None,
    team_id: int | None,
) -> tuple[int | None, int | None]:
    if team_id is not None:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise bad_request("所属队伍不存在，请先刷新后重试。")
        if sport_id is not None and sport_id != team.sport_id:
            raise bad_request("所选队伍与所属项目不一致，请重新选择。")
        return team.sport_id, team.id

    if sport_id is not None:
        sport = db.query(Sport).filter(Sport.id == sport_id).first()
        if not sport:
            raise bad_request("所属项目不存在，请先刷新后重试。")
        return sport.id, None

    return None, None
