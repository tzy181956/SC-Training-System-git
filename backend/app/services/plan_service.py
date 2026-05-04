from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import Exercise, TrainingPlanTemplate, TrainingPlanTemplateItem
from app.schemas.training_plan import (
    PlanTemplateCreate,
    PlanTemplateItemCreate,
    PlanTemplateItemUpdate,
    PlanTemplateUpdate,
)
from app.services import backup_service, content_change_log_service, dangerous_operation_service


def list_templates(db: Session) -> list[TrainingPlanTemplate]:
    return (
        db.query(TrainingPlanTemplate)
        .options(joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise))
        .order_by(TrainingPlanTemplate.name)
        .all()
    )


def get_template(db: Session, template_id: int) -> TrainingPlanTemplate:
    template = (
        db.query(TrainingPlanTemplate)
        .options(joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise))
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("Training template not found")
    return template


def create_template(
    db: Session,
    payload: PlanTemplateCreate,
    created_by: int | None,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    template = TrainingPlanTemplate(**payload.model_dump(), created_by=created_by)
    db.add(template)
    db.flush()
    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="training_plan_template",
        object_id=template.id,
        object_label=template.name,
        actor_name=actor_name,
        team_id=template.team_id,
        summary=f"新建训练模板“{template.name}”",
        after_snapshot=_serialize_template(template),
    )
    db.commit()
    db.refresh(template)
    return get_template(db, template.id)


def update_template(
    db: Session,
    template_id: int,
    payload: PlanTemplateUpdate,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("Training template not found")

    before_snapshot = _serialize_template(template)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.flush()
    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="training_plan_template",
        object_id=template.id,
        object_label=template.name,
        actor_name=actor_name,
        team_id=template.team_id,
        summary=f"更新训练模板“{template.name}”",
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_template(template),
    )
    db.commit()
    return get_template(db, template_id)


def add_template_item(
    db: Session,
    template_id: int,
    payload: PlanTemplateItemCreate,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("Training template not found")

    item = TrainingPlanTemplateItem(template_id=template_id, **payload.model_dump())
    db.add(item)
    db.flush()
    exercise = db.query(Exercise).filter(Exercise.id == item.exercise_id).first()
    exercise_label = exercise.name if exercise else f"动作 {item.exercise_id}"
    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="training_plan_template_item",
        object_id=item.id,
        object_label=f"{template.name} / {exercise_label}",
        actor_name=actor_name,
        team_id=template.team_id,
        summary=f"模板“{template.name}”新增动作“{exercise_label}”",
        after_snapshot=_serialize_template_item(item, exercise_name=exercise.name if exercise else None),
        extra_context={
            "template_id": template.id,
            "template_name": template.name,
        },
    )
    db.commit()
    return get_template(db, template_id)


def update_template_item(
    db: Session,
    item_id: int,
    payload: PlanTemplateItemUpdate,
    actor_name: str | None = None,
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

    before_snapshot = _serialize_template_item(item, exercise_name=item.exercise.name if item.exercise else None)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.flush()
    refreshed_item = (
        db.query(TrainingPlanTemplateItem)
        .options(
            joinedload(TrainingPlanTemplateItem.template),
            joinedload(TrainingPlanTemplateItem.exercise),
        )
        .filter(TrainingPlanTemplateItem.id == item_id)
        .first()
    )
    if not refreshed_item:
        raise not_found("Template item not found after update")

    exercise_label = refreshed_item.exercise.name if refreshed_item.exercise else f"动作 {refreshed_item.exercise_id}"
    template = refreshed_item.template
    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="training_plan_template_item",
        object_id=refreshed_item.id,
        object_label=f"{template.name if template else refreshed_item.template_id} / {exercise_label}",
        actor_name=actor_name,
        team_id=template.team_id if template else None,
        summary=f"模板“{template.name if template else refreshed_item.template_id}”更新动作“{exercise_label}”配置",
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_template_item(refreshed_item, exercise_name=refreshed_item.exercise.name if refreshed_item.exercise else None),
        extra_context={
            "template_id": template.id if template else refreshed_item.template_id,
            "template_name": template.name if template else None,
        },
    )
    db.commit()
    db.refresh(refreshed_item)
    return refreshed_item


def delete_template_item(db: Session, item_id: int, *, actor_name: str | None = None) -> None:
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

    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_template_item_{item_id}")
    template_name = item.template.name if item.template else f"模板 {item.template_id}"
    exercise_name = item.exercise.name if item.exercise else f"动作 {item.exercise_id}"
    team = item.template.team if item.template and hasattr(item.template, "team") else None

    db.delete(item)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_template_item",
        object_type="training_plan_template_item",
        object_id=item_id,
        actor_name=actor_name,
        summary=f"从模板“{template_name}”删除动作“{exercise_name}”",
        impact_scope={
            "template_id": item.template_id,
            "template_name": template_name,
            "team_id": item.template.team_id if item.template else None,
            "team_name": team.name if team else None,
            "exercise_id": item.exercise_id,
            "exercise_name": exercise_name,
            "sort_order": item.sort_order,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def delete_template(db: Session, template_id: int, *, actor_name: str | None = None) -> None:
    template = (
        db.query(TrainingPlanTemplate)
        .options(joinedload(TrainingPlanTemplate.items))
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("Training template not found")

    item_count = len(template.items or [])
    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_template_{template_id}")

    db.delete(template)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_template",
        object_type="training_plan_template",
        object_id=template_id,
        actor_name=actor_name,
        summary=f"删除训练模板“{template.name}”",
        impact_scope={
            "template_name": template.name,
            "team_id": template.team_id,
            "template_item_count": item_count,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def _serialize_template(template: TrainingPlanTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "sport_id": template.sport_id,
        "team_id": template.team_id,
        "is_active": template.is_active,
    }


def _serialize_template_item(item: TrainingPlanTemplateItem, *, exercise_name: str | None) -> dict:
    return {
        "id": item.id,
        "template_id": item.template_id,
        "exercise_id": item.exercise_id,
        "exercise_name": exercise_name,
        "sort_order": item.sort_order,
        "prescribed_sets": item.prescribed_sets,
        "prescribed_reps": item.prescribed_reps,
        "target_note": item.target_note,
        "is_main_lift": item.is_main_lift,
        "enable_auto_load": item.enable_auto_load,
        "initial_load_mode": item.initial_load_mode,
        "initial_load_value": item.initial_load_value,
        "progression_goal": item.progression_goal,
        "progression_rules": item.progression_rules,
        "ai_adjust_enabled": item.ai_adjust_enabled,
    }
