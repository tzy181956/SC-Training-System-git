from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import (
    AssignmentItemOverride,
    Athlete,
    AthletePlanAssignment,
    SetRecord,
    Team,
    TestMetricDefinition,
    TestRecord,
    TestTypeDefinition,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
    TrainingSession,
    TrainingSessionItem,
    TrainingSyncIssue,
    User,
)


SPORT_BINDING_REQUIRED_DETAIL = "当前账号未绑定项目"
SPORT_ACCESS_DENIED_DETAIL = "无权访问其他项目数据"
TEAM_ACCESS_DENIED_DETAIL = "无权访问其他项目下的队伍"
GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL = "无权修改系统训练模板"
GLOBAL_TEMPLATE_ASSIGN_DENIED_DETAIL = "无权使用其他项目训练模板"
GLOBAL_TEST_DEFINITION_EDIT_DENIED_DETAIL = "无权修改系统测试项目"


def normalize_role_code(role_code: str | None) -> str:
    return (role_code or "").strip().lower()


def is_admin(user: User | None) -> bool:
    return normalize_role_code(getattr(user, "role_code", None)) == "admin"


def is_coach(user: User | None) -> bool:
    return normalize_role_code(getattr(user, "role_code", None)) == "coach"


def ensure_sport_bound_user(user: User) -> int:
    if is_admin(user):
        raise RuntimeError("Admin users do not require a bound sport")
    if user.sport_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_BINDING_REQUIRED_DETAIL)
    return user.sport_id


def ensure_sport_access(user: User, sport_id: int | None) -> None:
    if is_admin(user):
        return
    scoped_sport_id = ensure_sport_bound_user(user)
    if sport_id != scoped_sport_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_ACCESS_DENIED_DETAIL)


def resolve_visible_sport_id(user: User, requested_sport_id: int | None = None) -> int | None:
    if is_admin(user):
        return requested_sport_id
    scoped_sport_id = ensure_sport_bound_user(user)
    if requested_sport_id is not None and requested_sport_id != scoped_sport_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_ACCESS_DENIED_DETAIL)
    return scoped_sport_id


def get_accessible_team(db: Session, user: User, team_id: int) -> Team:
    team = db.query(Team).options(joinedload(Team.sport)).filter(Team.id == team_id).first()
    if not team:
        raise not_found("队伍不存在")
    ensure_sport_access(user, team.sport_id)
    return team


def resolve_visible_team_id(db: Session, user: User, requested_team_id: int | None = None) -> int | None:
    if is_admin(user):
        return requested_team_id
    if requested_team_id is None:
        return None
    team = get_accessible_team(db, user, requested_team_id)
    return team.id


def filter_visible_athletes(athletes: list[Athlete], user: User) -> list[Athlete]:
    if is_admin(user):
        return athletes
    scoped_sport_id = ensure_sport_bound_user(user)
    return [athlete for athlete in athletes if athlete.sport_id == scoped_sport_id]


def filter_visible_templates(templates: list[TrainingPlanTemplate], user: User) -> list[TrainingPlanTemplate]:
    if is_admin(user):
        return templates
    scoped_sport_id = ensure_sport_bound_user(user)
    return [template for template in templates if template.sport_id in {None, scoped_sport_id}]


def filter_visible_assignments(assignments: list[AthletePlanAssignment], user: User) -> list[AthletePlanAssignment]:
    if is_admin(user):
        return assignments
    scoped_sport_id = ensure_sport_bound_user(user)
    return [assignment for assignment in assignments if getattr(assignment.athlete, "sport_id", None) == scoped_sport_id]


def get_accessible_athlete(db: Session, user: User, athlete_id: int) -> Athlete:
    athlete = (
        db.query(Athlete)
        .options(joinedload(Athlete.sport), joinedload(Athlete.team))
        .filter(Athlete.id == athlete_id)
        .first()
    )
    if not athlete:
        raise not_found("Athlete not found")
    ensure_sport_access(user, athlete.sport_id)
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
        .options(
            joinedload(TrainingPlanTemplate.sport),
            joinedload(TrainingPlanTemplate.team),
            joinedload(TrainingPlanTemplate.modules),
            joinedload(TrainingPlanTemplate.items),
        )
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("Training template not found")

    if is_admin(user):
        return template

    scoped_sport_id = ensure_sport_bound_user(user)
    if template.sport_id is None:
        if allow_global_write or allow_global_read:
            return template
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL)
    if template.sport_id != scoped_sport_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_ACCESS_DENIED_DETAIL)
    return template


def ensure_template_assignable_to_athlete(
    db: Session,
    user: User,
    template_id: int,
    athlete: Athlete,
) -> TrainingPlanTemplate:
    template = get_accessible_template(db, user, template_id, allow_global_read=True, allow_global_write=False)
    if not is_admin(user) and template.sport_id not in {None, athlete.sport_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_ASSIGN_DENIED_DETAIL)
    return template


def get_accessible_assignment(db: Session, user: User, assignment_id: int) -> AthletePlanAssignment:
    assignment = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.template),
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(AthletePlanAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise not_found("未找到计划分配记录")
    ensure_sport_access(user, assignment.athlete.sport_id if assignment.athlete else None)
    if not is_admin(user):
        template_sport_id = assignment.template.sport_id if assignment.template else None
        scoped_sport_id = ensure_sport_bound_user(user)
        if template_sport_id not in {None, scoped_sport_id}:
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
            joinedload(TrainingPlanTemplateItem.template).joinedload(TrainingPlanTemplate.sport),
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

    scoped_sport_id = ensure_sport_bound_user(user)
    if template.sport_id is None:
        if allow_global_write or allow_global_read:
            return item
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL)
    if template.sport_id != scoped_sport_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_ACCESS_DENIED_DETAIL)
    return item


def get_accessible_template_module(
    db: Session,
    user: User,
    module_id: int,
    *,
    allow_global_read: bool = True,
    allow_global_write: bool = False,
) -> TrainingPlanTemplateModule:
    module = (
        db.query(TrainingPlanTemplateModule)
        .options(
            joinedload(TrainingPlanTemplateModule.template).joinedload(TrainingPlanTemplate.sport),
            joinedload(TrainingPlanTemplateModule.items),
        )
        .filter(TrainingPlanTemplateModule.id == module_id)
        .first()
    )
    if not module:
        raise not_found("Template module not found")
    template = module.template
    if template is None:
        raise not_found("Training template not found")
    if is_admin(user):
        return module

    scoped_sport_id = ensure_sport_bound_user(user)
    if template.sport_id is None:
        if allow_global_write or allow_global_read:
            return module
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEMPLATE_EDIT_DENIED_DETAIL)
    if template.sport_id != scoped_sport_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_ACCESS_DENIED_DETAIL)
    return module


def get_accessible_override(db: Session, user: User, override_id: int) -> AssignmentItemOverride:
    override = (
        db.query(AssignmentItemOverride)
        .options(
            joinedload(AssignmentItemOverride.assignment)
            .joinedload(AthletePlanAssignment.athlete)
            .joinedload(Athlete.team),
            joinedload(AssignmentItemOverride.assignment)
            .joinedload(AthletePlanAssignment.athlete)
            .joinedload(Athlete.sport),
        )
        .filter(AssignmentItemOverride.id == override_id)
        .first()
    )
    if not override:
        raise not_found("未找到负荷覆盖项")
    assignment = override.assignment
    ensure_sport_access(user, assignment.athlete.sport_id if assignment and assignment.athlete else None)
    return override


def get_accessible_session(db: Session, user: User, session_id: int) -> TrainingSession:
    session = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.athlete).joinedload(Athlete.team),
            joinedload(TrainingSession.athlete).joinedload(Athlete.sport),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
        )
        .filter(TrainingSession.id == session_id)
        .first()
    )
    if not session:
        raise not_found("Training session not found")
    ensure_sport_access(user, session.athlete.sport_id if session.athlete else None)
    return session


def get_accessible_session_item(db: Session, user: User, item_id: int) -> TrainingSessionItem:
    item = (
        db.query(TrainingSessionItem)
        .options(
            joinedload(TrainingSessionItem.session).joinedload(TrainingSession.athlete).joinedload(Athlete.team),
            joinedload(TrainingSessionItem.session).joinedload(TrainingSession.athlete).joinedload(Athlete.sport),
            joinedload(TrainingSessionItem.records),
            joinedload(TrainingSessionItem.exercise),
        )
        .filter(TrainingSessionItem.id == item_id)
        .first()
    )
    if not item:
        raise not_found("Training session item not found")
    ensure_sport_access(user, item.session.athlete.sport_id if item.session and item.session.athlete else None)
    return item


def get_accessible_set_record(db: Session, user: User, record_id: int) -> SetRecord:
    record = (
        db.query(SetRecord)
        .options(
            joinedload(SetRecord.session_item)
            .joinedload(TrainingSessionItem.session)
            .joinedload(TrainingSession.athlete)
            .joinedload(Athlete.team),
            joinedload(SetRecord.session_item)
            .joinedload(TrainingSessionItem.session)
            .joinedload(TrainingSession.athlete)
            .joinedload(Athlete.sport),
            joinedload(SetRecord.session_item).joinedload(TrainingSessionItem.exercise),
        )
        .filter(SetRecord.id == record_id)
        .first()
    )
    if not record:
        raise not_found("Set record not found")
    session = record.session_item.session if record.session_item else None
    ensure_sport_access(user, session.athlete.sport_id if session and session.athlete else None)
    return record


def get_accessible_sync_issue(db: Session, user: User, issue_id: int) -> TrainingSyncIssue:
    issue = db.get(TrainingSyncIssue, issue_id)
    if not issue:
        raise not_found("未找到同步异常记录")
    athlete = get_accessible_athlete(db, user, issue.athlete_id)
    ensure_sport_access(user, athlete.sport_id)
    return issue


def get_accessible_test_type_definition(
    db: Session,
    user: User,
    definition_id: int,
    *,
    allow_system_read: bool = True,
    allow_system_write: bool = False,
) -> TestTypeDefinition:
    definition = (
        db.query(TestTypeDefinition)
        .options(joinedload(TestTypeDefinition.sport), joinedload(TestTypeDefinition.metrics))
        .filter(TestTypeDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise not_found("Test type definition not found")

    _ensure_test_type_access(
        user,
        definition,
        allow_system_read=allow_system_read,
        allow_system_write=allow_system_write,
    )
    return definition


def get_accessible_test_metric_definition(
    db: Session,
    user: User,
    definition_id: int,
    *,
    allow_system_read: bool = True,
    allow_system_write: bool = False,
) -> TestMetricDefinition:
    definition = (
        db.query(TestMetricDefinition)
        .options(joinedload(TestMetricDefinition.test_type).joinedload(TestTypeDefinition.sport))
        .filter(TestMetricDefinition.id == definition_id)
        .first()
    )
    if not definition:
        raise not_found("Test metric definition not found")
    if definition.test_type is None:
        raise not_found("Test type definition not found")

    _ensure_test_type_access(
        user,
        definition.test_type,
        allow_system_read=allow_system_read,
        allow_system_write=allow_system_write,
    )
    return definition


def ensure_test_type_writable(user: User, definition: TestTypeDefinition) -> TestTypeDefinition:
    _ensure_test_type_access(user, definition, allow_system_read=False, allow_system_write=False)
    return definition


def get_accessible_test_record(db: Session, user: User, record_id: int) -> TestRecord:
    record = (
        db.query(TestRecord)
        .options(
            joinedload(TestRecord.athlete).joinedload(Athlete.team),
            joinedload(TestRecord.athlete).joinedload(Athlete.sport),
        )
        .filter(TestRecord.id == record_id)
        .first()
    )
    if not record:
        raise not_found("Test record not found")
    ensure_sport_access(user, record.athlete.sport_id if record.athlete else None)
    return record


def _ensure_test_type_access(
    user: User,
    definition: TestTypeDefinition,
    *,
    allow_system_read: bool,
    allow_system_write: bool,
) -> None:
    if is_admin(user):
        return

    scoped_sport_id = ensure_sport_bound_user(user)
    if definition.sport_id is None:
        if allow_system_write or allow_system_read:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=GLOBAL_TEST_DEFINITION_EDIT_DENIED_DETAIL)
    if definition.sport_id != scoped_sport_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SPORT_ACCESS_DENIED_DETAIL)
