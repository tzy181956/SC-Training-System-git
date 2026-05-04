from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import (
    AssignmentItemOverride,
    Athlete,
    AthletePlanAssignment,
    SetRecord,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingSession,
    TrainingSessionItem,
    TrainingSyncIssue,
    User,
)


TEAM_BINDING_REQUIRED_DETAIL = "当前账号未绑定队伍"
TEAM_ACCESS_DENIED_DETAIL = "无权访问其他队伍数据"
GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL = "无权修改全局模板"
GLOBAL_TEMPLATE_ASSIGN_DENIED_DETAIL = "无权分配其他队伍模板"


def normalize_role_code(role_code: str | None) -> str:
    return (role_code or "").strip().lower()


def is_admin(user: User | None) -> bool:
    return normalize_role_code(getattr(user, "role_code", None)) == "admin"


def is_coach(user: User | None) -> bool:
    return normalize_role_code(getattr(user, "role_code", None)) == "coach"


def is_training(user: User | None) -> bool:
    return normalize_role_code(getattr(user, "role_code", None)) == "training"


def ensure_team_bound_user(user: User) -> int:
    if is_admin(user):
        raise RuntimeError("Admin users do not require a bound team")
    if user.team_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TEAM_BINDING_REQUIRED_DETAIL)
    return user.team_id


def ensure_team_access(user: User, team_id: int | None) -> None:
    if is_admin(user):
        return
    scoped_team_id = ensure_team_bound_user(user)
    if team_id != scoped_team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TEAM_ACCESS_DENIED_DETAIL)


def resolve_visible_team_id(user: User, requested_team_id: int | None = None) -> int | None:
    if is_admin(user):
        return requested_team_id
    scoped_team_id = ensure_team_bound_user(user)
    if requested_team_id is not None and requested_team_id != scoped_team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TEAM_ACCESS_DENIED_DETAIL)
    return scoped_team_id


def filter_visible_athletes(athletes: list[Athlete], user: User) -> list[Athlete]:
    if is_admin(user):
        return athletes
    scoped_team_id = ensure_team_bound_user(user)
    return [athlete for athlete in athletes if athlete.team_id == scoped_team_id]


def filter_visible_templates(templates: list[TrainingPlanTemplate], user: User) -> list[TrainingPlanTemplate]:
    if is_admin(user):
        return templates
    scoped_team_id = ensure_team_bound_user(user)
    return [template for template in templates if template.team_id in {None, scoped_team_id}]


def filter_visible_assignments(assignments: list[AthletePlanAssignment], user: User) -> list[AthletePlanAssignment]:
    if is_admin(user):
        return assignments
    scoped_team_id = ensure_team_bound_user(user)
    return [assignment for assignment in assignments if getattr(assignment.athlete, "team_id", None) == scoped_team_id]


def get_accessible_athlete(db: Session, user: User, athlete_id: int) -> Athlete:
    athlete = (
        db.query(Athlete)
        .options(joinedload(Athlete.sport), joinedload(Athlete.team))
        .filter(Athlete.id == athlete_id)
        .first()
    )
    if not athlete:
        raise not_found("Athlete not found")
    ensure_team_access(user, athlete.team_id)
    return athlete


def get_accessible_template(
    db: Session,
    user: User,
    template_id: int,
    *,
    allow_global_read: bool = True,
    allow_global_write: bool = False,
) -> TrainingPlanTemplate:
    template = (
        db.query(TrainingPlanTemplate)
        .options(joinedload(TrainingPlanTemplate.items))
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("Training template not found")

    if is_admin(user):
        return template

    scoped_team_id = ensure_team_bound_user(user)
    if template.team_id is None:
        if allow_global_write:
            return template
        if allow_global_read:
            return template
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL)
    if template.team_id != scoped_team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TEAM_ACCESS_DENIED_DETAIL)
    return template


def ensure_template_assignable_to_athlete(
    db: Session,
    user: User,
    template_id: int,
    athlete: Athlete,
) -> TrainingPlanTemplate:
    template = get_accessible_template(db, user, template_id, allow_global_read=True, allow_global_write=False)
    if not is_admin(user) and template.team_id not in {None, athlete.team_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_ASSIGN_DENIED_DETAIL)
    return template


def get_accessible_assignment(db: Session, user: User, assignment_id: int) -> AthletePlanAssignment:
    assignment = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.template),
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(AthletePlanAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise not_found("未找到计划分配记录")
    ensure_team_access(user, assignment.athlete.team_id if assignment.athlete else None)
    if not is_admin(user):
        template_team_id = assignment.template.team_id if assignment.template else None
        scoped_team_id = ensure_team_bound_user(user)
        if template_team_id not in {None, scoped_team_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_ASSIGN_DENIED_DETAIL)
    return assignment


def get_accessible_template_item(
    db: Session,
    user: User,
    item_id: int,
    *,
    allow_global_read: bool = True,
    allow_global_write: bool = False,
) -> TrainingPlanTemplateItem:
    item = (
        db.query(TrainingPlanTemplateItem)
        .options(
            joinedload(TrainingPlanTemplateItem.template),
            joinedload(TrainingPlanTemplateItem.exercise),
        )
        .filter(TrainingPlanTemplateItem.id == item_id)
        .first()
    )
    if not item:
        raise not_found("Template item not found")
    template = item.template
    if template is None:
        raise not_found("Training template not found")
    if is_admin(user):
        return item

    scoped_team_id = ensure_team_bound_user(user)
    if template.team_id is None:
        if allow_global_write or allow_global_read:
            if allow_global_write:
                return item
            if allow_global_read:
                return item
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL)
    if template.team_id != scoped_team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TEAM_ACCESS_DENIED_DETAIL)
    return item


def get_accessible_override(db: Session, user: User, override_id: int) -> AssignmentItemOverride:
    override = (
        db.query(AssignmentItemOverride)
        .options(
            joinedload(AssignmentItemOverride.assignment)
            .joinedload(AthletePlanAssignment.athlete)
            .joinedload(Athlete.team),
        )
        .filter(AssignmentItemOverride.id == override_id)
        .first()
    )
    if not override:
        raise not_found("未找到负荷覆盖项")
    assignment = override.assignment
    ensure_team_access(user, assignment.athlete.team_id if assignment and assignment.athlete else None)
    return override


def get_accessible_session(db: Session, user: User, session_id: int) -> TrainingSession:
    session = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.athlete).joinedload(Athlete.team),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
        )
        .filter(TrainingSession.id == session_id)
        .first()
    )
    if not session:
        raise not_found("Training session not found")
    ensure_team_access(user, session.athlete.team_id if session.athlete else None)
    return session


def get_accessible_session_item(db: Session, user: User, item_id: int) -> TrainingSessionItem:
    item = (
        db.query(TrainingSessionItem)
        .options(
            joinedload(TrainingSessionItem.session).joinedload(TrainingSession.athlete).joinedload(Athlete.team),
            joinedload(TrainingSessionItem.records),
            joinedload(TrainingSessionItem.exercise),
        )
        .filter(TrainingSessionItem.id == item_id)
        .first()
    )
    if not item:
        raise not_found("Training session item not found")
    ensure_team_access(user, item.session.athlete.team_id if item.session and item.session.athlete else None)
    return item


def get_accessible_set_record(db: Session, user: User, record_id: int) -> SetRecord:
    record = (
        db.query(SetRecord)
        .options(
            joinedload(SetRecord.session_item)
            .joinedload(TrainingSessionItem.session)
            .joinedload(TrainingSession.athlete)
            .joinedload(Athlete.team),
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.exercise),
        )
        .filter(SetRecord.id == record_id)
        .first()
    )
    if not record:
        raise not_found("Set record not found")
    session = record.session_item.session if record.session_item else None
    ensure_team_access(user, session.athlete.team_id if session and session.athlete else None)
    return record


def get_accessible_sync_issue(db: Session, user: User, issue_id: int) -> TrainingSyncIssue:
    issue = db.get(TrainingSyncIssue, issue_id)
    if not issue:
        raise not_found("未找到同步异常记录")
    athlete = get_accessible_athlete(db, user, issue.athlete_id)
    ensure_team_access(user, athlete.team_id)
    return issue
