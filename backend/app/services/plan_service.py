from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import (
    Exercise,
    Sport,
    Team,
    TestMetricDefinition,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
    User,
)
from app.models.training_plan import TEMPLATE_VISIBILITY_PRIVATE, TEMPLATE_VISIBILITY_PUBLIC
from app.schemas.training_plan import (
    PlanTemplateCopyPayload,
    PlanTemplateCreate,
    PlanTemplateItemCreate,
    PlanTemplateItemUpdate,
    PlanTemplateModuleCreate,
    PlanTemplateModuleUpdate,
    PlanTemplateUpdate,
)
from app.services import (
    access_control_service,
    backup_service,
    content_change_log_service,
    dangerous_operation_service,
    exercise_service,
)


MAX_TEMPLATE_NAME_LENGTH = 120
VALID_TEMPLATE_VISIBILITIES = {TEMPLATE_VISIBILITY_PUBLIC, TEMPLATE_VISIBILITY_PRIVATE}

TEMPLATE_DETAIL_OPTIONS = (
    joinedload(TrainingPlanTemplate.owner_user),
    joinedload(TrainingPlanTemplate.created_by_user),
    joinedload(TrainingPlanTemplate.source_template),
    joinedload(TrainingPlanTemplate.modules)
    .joinedload(TrainingPlanTemplateModule.items)
    .joinedload(TrainingPlanTemplateItem.exercise),
    joinedload(TrainingPlanTemplate.modules)
    .joinedload(TrainingPlanTemplateModule.items)
    .joinedload(TrainingPlanTemplateItem.initial_load_test_metric_definition)
    .joinedload(TestMetricDefinition.test_type),
    joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise),
    joinedload(TrainingPlanTemplate.items)
    .joinedload(TrainingPlanTemplateItem.initial_load_test_metric_definition)
    .joinedload(TestMetricDefinition.test_type),
    joinedload(TrainingPlanTemplate.items)
    .joinedload(TrainingPlanTemplateItem.module)
    .joinedload(TrainingPlanTemplateModule.items),
)

ITEM_DETAIL_OPTIONS = (
    joinedload(TrainingPlanTemplateItem.template),
    joinedload(TrainingPlanTemplateItem.template).joinedload(TrainingPlanTemplate.owner_user),
    joinedload(TrainingPlanTemplateItem.template).joinedload(TrainingPlanTemplate.source_template),
    joinedload(TrainingPlanTemplateItem.exercise),
    joinedload(TrainingPlanTemplateItem.initial_load_test_metric_definition).joinedload(TestMetricDefinition.test_type),
    joinedload(TrainingPlanTemplateItem.module).joinedload(TrainingPlanTemplateModule.items),
)

MODULE_DETAIL_OPTIONS = (
    joinedload(TrainingPlanTemplateModule.template).joinedload(TrainingPlanTemplate.items),
    joinedload(TrainingPlanTemplateModule.template).joinedload(TrainingPlanTemplate.owner_user),
    joinedload(TrainingPlanTemplateModule.template).joinedload(TrainingPlanTemplate.source_template),
    joinedload(TrainingPlanTemplateModule.items).joinedload(TrainingPlanTemplateItem.exercise),
)


def list_templates(
    db: Session,
    *,
    current_user: User,
    visibility: str | None = None,
    owner_user_id: int | None = None,
) -> list[dict]:
    module_counts = (
        db.query(
            TrainingPlanTemplateModule.template_id.label("template_id"),
            func.count(TrainingPlanTemplateModule.id).label("modules_count"),
        )
        .group_by(TrainingPlanTemplateModule.template_id)
        .subquery()
    )
    item_counts = (
        db.query(
            TrainingPlanTemplateItem.template_id.label("template_id"),
            func.count(TrainingPlanTemplateItem.id).label("items_count"),
        )
        .group_by(TrainingPlanTemplateItem.template_id)
        .subquery()
    )
    query = (
        db.query(
            TrainingPlanTemplate,
            func.coalesce(module_counts.c.modules_count, 0).label("modules_count"),
            func.coalesce(item_counts.c.items_count, 0).label("items_count"),
        )
        .options(
            joinedload(TrainingPlanTemplate.owner_user),
            joinedload(TrainingPlanTemplate.source_template),
        )
        .outerjoin(module_counts, module_counts.c.template_id == TrainingPlanTemplate.id)
        .outerjoin(item_counts, item_counts.c.template_id == TrainingPlanTemplate.id)
        .order_by(TrainingPlanTemplate.name)
    )
    visibility_key = _normalize_visibility_filter(visibility)

    if access_control_service.is_admin(current_user):
        if visibility_key != "all":
            query = query.filter(TrainingPlanTemplate.visibility == visibility_key)
        if owner_user_id is not None:
            query = query.filter(TrainingPlanTemplate.owner_user_id == owner_user_id)
        return [
            _serialize_template_list_row(template, modules_count, items_count, current_user)
            for template, modules_count, items_count in query.all()
        ]

    if owner_user_id is not None and owner_user_id != current_user.id:
        raise bad_request("教练账号不能查看其他教练的自建模板")

    visible_filter = or_(
        TrainingPlanTemplate.visibility == TEMPLATE_VISIBILITY_PUBLIC,
        and_(
            TrainingPlanTemplate.visibility == TEMPLATE_VISIBILITY_PRIVATE,
            TrainingPlanTemplate.owner_user_id == current_user.id,
        ),
    )
    query = query.filter(visible_filter)
    if visibility_key == TEMPLATE_VISIBILITY_PUBLIC:
        query = query.filter(TrainingPlanTemplate.visibility == TEMPLATE_VISIBILITY_PUBLIC)
    elif visibility_key == TEMPLATE_VISIBILITY_PRIVATE:
        query = query.filter(
            TrainingPlanTemplate.visibility == TEMPLATE_VISIBILITY_PRIVATE,
            TrainingPlanTemplate.owner_user_id == current_user.id,
        )
    return [
        _serialize_template_list_row(template, modules_count, items_count, current_user)
        for template, modules_count, items_count in query.all()
    ]


def _serialize_template_list_row(
    template: TrainingPlanTemplate,
    modules_count: int,
    items_count: int,
    current_user: User,
) -> dict:
    can_edit = access_control_service.can_edit_template(current_user, template)
    can_copy = access_control_service.can_copy_template(current_user, template)
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "sport_id": template.sport_id,
        "team_id": template.team_id,
        "is_active": template.is_active,
        "created_by": template.created_by,
        "visibility": template.visibility,
        "owner_user_id": template.owner_user_id,
        "created_by_user_id": template.created_by_user_id,
        "source_template_id": template.source_template_id,
        "visibility_label": template.visibility_label,
        "owner_name": template.owner_name,
        "source_template_name": template.source_template_name,
        "modules_count": int(modules_count or 0),
        "items_count": int(items_count or 0),
        "can_edit": can_edit,
        "can_copy": can_copy,
        "edit_lock_reason": _resolve_template_edit_lock_reason(template, can_edit=can_edit),
    }


def _resolve_template_edit_lock_reason(template: TrainingPlanTemplate, *, can_edit: bool) -> str | None:
    if can_edit:
        return None
    visibility = (template.visibility or TEMPLATE_VISIBILITY_PRIVATE).strip().lower()
    if visibility == TEMPLATE_VISIBILITY_PUBLIC:
        return access_control_service.PUBLIC_TEMPLATE_EDIT_DENIED_DETAIL
    return access_control_service.TEMPLATE_ACCESS_DENIED_DETAIL


def get_template(db: Session, template_id: int) -> TrainingPlanTemplate:
    template = (
        db.query(TrainingPlanTemplate)
        .options(*TEMPLATE_DETAIL_OPTIONS)
        .populate_existing()
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("Training template not found")
    return template


def create_template(
    db: Session,
    payload: PlanTemplateCreate,
    current_user: User,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    payload_data = payload.model_dump(exclude={"visibility", "owner_user_id"})
    ownership_data = _resolve_create_ownership(db, payload, current_user)
    template = TrainingPlanTemplate(
        **_normalize_template_scope(db, payload_data),
        created_by=current_user.id,
        created_by_user_id=current_user.id,
        **ownership_data,
    )
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
    current_user: User,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("Training template not found")

    before_snapshot = _serialize_template(template)
    raw_updates = payload.model_dump(exclude_unset=True)
    scope_updates = {
        key: value
        for key, value in raw_updates.items()
        if key not in {"visibility", "owner_user_id"}
    }
    updates = _normalize_template_scope(
        db,
        scope_updates,
        current_sport_id=template.sport_id,
        current_team_id=template.team_id,
    )
    if access_control_service.is_admin(current_user):
        updates.update(_resolve_update_ownership(db, template, raw_updates))

    for key, value in updates.items():
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


def copy_template(
    db: Session,
    template_id: int,
    payload: PlanTemplateCopyPayload,
    current_user: User,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    source = get_template(db, template_id)
    if not access_control_service.can_copy_template(current_user, source):
        raise bad_request("第一阶段只允许复制可见的公共模板")
    if not source.is_active:
        raise bad_request("停用模板不能复制，请先启用或选择其他公共模板")

    if access_control_service.is_admin(current_user):
        if payload.target_owner_user_id is None:
            raise bad_request("管理员复制公共模板时必须选择目标教练")
        owner = _get_active_coach_user(db, payload.target_owner_user_id)
        default_suffix = "教练副本"
    else:
        if payload.target_owner_user_id is not None and payload.target_owner_user_id != current_user.id:
            raise bad_request("教练只能把公共模板复制到自己的模板")
        owner = _get_active_coach_user(db, current_user.id)
        default_suffix = "我的副本"

    copy_name = _resolve_copy_name(source.name, payload.name, default_suffix)
    copied = TrainingPlanTemplate(
        name=copy_name,
        description=source.description,
        sport_id=source.sport_id,
        team_id=source.team_id,
        is_active=source.is_active,
        created_by=current_user.id,
        visibility=TEMPLATE_VISIBILITY_PRIVATE,
        owner_user_id=owner.id,
        created_by_user_id=current_user.id,
        source_template_id=source.id,
    )
    db.add(copied)
    db.flush()

    module_id_map: dict[int, int] = {}
    source_modules = sorted(source.modules or [], key=lambda module: (module.sort_order, module.id or 0))
    for module in source_modules:
        copied_module = TrainingPlanTemplateModule(
            template_id=copied.id,
            sort_order=module.sort_order,
            title=module.title,
            note=module.note,
        )
        db.add(copied_module)
        db.flush()
        module_id_map[module.id] = copied_module.id

    source_items = sorted(source.items or [], key=lambda item: (item.sort_order, item.id or 0))
    for item in source_items:
        copied_module_id = module_id_map.get(item.module_id)
        if copied_module_id is None:
            continue
        db.add(
            TrainingPlanTemplateItem(
                template_id=copied.id,
                module_id=copied_module_id,
                exercise_id=item.exercise_id,
                sort_order=item.sort_order,
                prescribed_sets=item.prescribed_sets,
                prescribed_reps=item.prescribed_reps,
                target_note=item.target_note,
                is_main_lift=item.is_main_lift,
                enable_auto_load=item.enable_auto_load,
                initial_load_mode=item.initial_load_mode,
                initial_load_value=item.initial_load_value,
                initial_load_test_metric_definition_id=item.initial_load_test_metric_definition_id,
                progression_goal=item.progression_goal,
                progression_rules=dict(item.progression_rules or {}),
                ai_adjust_enabled=item.ai_adjust_enabled,
            )
        )

    content_change_log_service.log_content_change(
        db,
        action_type="copy",
        object_type="training_plan_template",
        object_id=copied.id,
        object_label=copied.name,
        actor_name=actor_name,
        team_id=copied.team_id,
        summary=f"复制公共模板“{source.name}”为“{copied.name}”",
        after_snapshot=_serialize_template(copied),
        extra_context={
            "source_template_id": source.id,
            "source_template_name": source.name,
            "owner_user_id": owner.id,
            "owner_name": owner.display_name,
        },
    )
    db.commit()
    return get_template(db, copied.id)


def add_template_module(
    db: Session,
    template_id: int,
    payload: PlanTemplateModuleCreate,
    actor_name: str | None = None,
) -> TrainingPlanTemplateModule:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("Training template not found")

    module = TrainingPlanTemplateModule(template_id=template_id, **payload.model_dump())
    db.add(module)
    db.flush()
    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="training_plan_template_module",
        object_id=module.id,
        object_label=f"{template.name} / {module.display_label}",
        actor_name=actor_name,
        team_id=template.team_id,
        summary=f"模板“{template.name}”新增{module.display_label}",
        after_snapshot=_serialize_template_module(module),
        extra_context={
            "template_id": template.id,
            "template_name": template.name,
        },
    )
    db.commit()
    return get_template_module(db, module.id)


def update_template_module(
    db: Session,
    module_id: int,
    payload: PlanTemplateModuleUpdate,
    actor_name: str | None = None,
) -> TrainingPlanTemplateModule:
    module = (
        db.query(TrainingPlanTemplateModule)
        .options(*MODULE_DETAIL_OPTIONS)
        .filter(TrainingPlanTemplateModule.id == module_id)
        .first()
    )
    if not module:
        raise not_found("Template module not found")

    before_snapshot = _serialize_template_module(module)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(module, key, value)

    db.flush()
    refreshed_module = get_template_module(db, module_id)
    template = refreshed_module.template
    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="training_plan_template_module",
        object_id=refreshed_module.id,
        object_label=f"{template.name if template else refreshed_module.template_id} / {refreshed_module.display_label}",
        actor_name=actor_name,
        team_id=template.team_id if template else None,
        summary=f"模板“{template.name if template else refreshed_module.template_id}”更新{refreshed_module.display_label}",
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_template_module(refreshed_module),
        extra_context={
            "template_id": template.id if template else refreshed_module.template_id,
            "template_name": template.name if template else None,
        },
    )
    db.commit()
    return get_template_module(db, module_id)


def delete_template_module(db: Session, module_id: int, *, actor_name: str | None = None) -> None:
    module = (
        db.query(TrainingPlanTemplateModule)
        .options(*MODULE_DETAIL_OPTIONS)
        .filter(TrainingPlanTemplateModule.id == module_id)
        .first()
    )
    if not module:
        raise not_found("Template module not found")

    template = module.template
    template_name = template.name if template else f"模板 {module.template_id}"
    deleted_item_count = len(module.items or [])
    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_template_module_{module_id}")

    db.delete(module)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_template_module",
        object_type="training_plan_template_module",
        object_id=module_id,
        actor_name=actor_name,
        summary=f"从模板“{template_name}”删除{module.display_label}",
        impact_scope={
            "template_id": module.template_id,
            "template_name": template_name,
            "team_id": template.team_id if template else None,
            "module_sort_order": module.sort_order,
            "module_code": module.module_code,
            "module_title": module.title,
            "deleted_item_count": deleted_item_count,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def add_template_item(
    db: Session,
    template_id: int,
    payload: PlanTemplateItemCreate,
    current_user: User,
    actor_name: str | None = None,
) -> TrainingPlanTemplate:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("Training template not found")

    module = _get_template_module_for_template(db, template_id, payload.module_id)
    exercise = _get_template_item_exercise(db, payload.exercise_id, current_user=current_user)
    item = TrainingPlanTemplateItem(template_id=template_id, **payload.model_dump())
    db.add(item)
    db.flush()
    exercise_label = exercise.name if exercise else f"动作 {item.exercise_id}"
    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="training_plan_template_item",
        object_id=item.id,
        object_label=f"{template.name} / {module.display_label} / {exercise_label}",
        actor_name=actor_name,
        team_id=template.team_id,
        summary=f"模板“{template.name}”在{module.display_label}新增动作“{exercise_label}”",
        after_snapshot=_serialize_template_item(item, exercise_name=exercise.name if exercise else None),
        extra_context={
            "template_id": template.id,
            "template_name": template.name,
            "module_id": module.id,
            "module_code": module.module_code,
        },
    )
    db.commit()
    return get_template(db, template_id)


def update_template_item(
    db: Session,
    item_id: int,
    payload: PlanTemplateItemUpdate,
    current_user: User,
    actor_name: str | None = None,
) -> TrainingPlanTemplateItem:
    item = (
        db.query(TrainingPlanTemplateItem)
        .options(*ITEM_DETAIL_OPTIONS)
        .filter(TrainingPlanTemplateItem.id == item_id)
        .first()
    )
    if not item:
        raise not_found("Template item not found")

    if payload.module_id is not None:
        _get_template_module_for_template(db, item.template_id, payload.module_id)
    if payload.exercise_id is not None:
        _get_template_item_exercise(db, payload.exercise_id, current_user=current_user)

    before_snapshot = _serialize_template_item(item, exercise_name=item.exercise.name if item.exercise else None)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.flush()
    refreshed_item = get_template_item(db, item_id)

    exercise_label = refreshed_item.exercise.name if refreshed_item.exercise else f"动作 {refreshed_item.exercise_id}"
    template = refreshed_item.template
    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="training_plan_template_item",
        object_id=refreshed_item.id,
        object_label=(
            f"{template.name if template else refreshed_item.template_id} / "
            f"{refreshed_item.module.display_label if refreshed_item.module else '模块'} / "
            f"{exercise_label}"
        ),
        actor_name=actor_name,
        team_id=template.team_id if template else None,
        summary=(
            f"模板“{template.name if template else refreshed_item.template_id}”更新动作“{exercise_label}”配置"
        ),
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_template_item(
            refreshed_item,
            exercise_name=refreshed_item.exercise.name if refreshed_item.exercise else None,
        ),
        extra_context={
            "template_id": template.id if template else refreshed_item.template_id,
            "template_name": template.name if template else None,
            "module_id": refreshed_item.module_id,
            "module_code": refreshed_item.module_code,
        },
    )
    db.commit()
    return get_template_item(db, item_id)


def delete_template_item(db: Session, item_id: int, *, actor_name: str | None = None) -> None:
    item = get_template_item(db, item_id)

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
            "module_id": item.module_id,
            "module_code": item.module_code,
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
        .options(joinedload(TrainingPlanTemplate.items), joinedload(TrainingPlanTemplate.modules))
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("Training template not found")

    item_count = len(template.items or [])
    module_count = len(template.modules or [])
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
            "template_module_count": module_count,
            "template_item_count": item_count,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def get_template_module(db: Session, module_id: int) -> TrainingPlanTemplateModule:
    module = (
        db.query(TrainingPlanTemplateModule)
        .options(*MODULE_DETAIL_OPTIONS)
        .filter(TrainingPlanTemplateModule.id == module_id)
        .first()
    )
    if not module:
        raise not_found("Template module not found")
    return module


def get_template_item(db: Session, item_id: int) -> TrainingPlanTemplateItem:
    item = db.query(TrainingPlanTemplateItem).options(*ITEM_DETAIL_OPTIONS).filter(TrainingPlanTemplateItem.id == item_id).first()
    if not item:
        raise not_found("Template item not found")
    return item


def _serialize_template(template: TrainingPlanTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "sport_id": template.sport_id,
        "team_id": template.team_id,
        "is_active": template.is_active,
        "visibility": template.visibility,
        "owner_user_id": template.owner_user_id,
        "owner_name": template.owner_name,
        "created_by_user_id": template.created_by_user_id,
        "source_template_id": template.source_template_id,
        "source_template_name": template.source_template_name,
    }


def _serialize_template_module(module: TrainingPlanTemplateModule) -> dict:
    return {
        "id": module.id,
        "template_id": module.template_id,
        "sort_order": module.sort_order,
        "module_code": module.module_code,
        "title": module.title,
        "note": module.note,
        "display_label": module.display_label,
        "item_count": len(module.items or []),
    }


def _serialize_template_item(item: TrainingPlanTemplateItem, *, exercise_name: str | None) -> dict:
    return {
        "id": item.id,
        "template_id": item.template_id,
        "module_id": item.module_id,
        "module_code": item.module_code,
        "display_code": item.display_code,
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
        "initial_load_test_metric_definition_id": item.initial_load_test_metric_definition_id,
        "initial_load_test_metric_definition_name": item.initial_load_test_metric_definition_name,
        "initial_load_test_type_name": item.initial_load_test_type_name,
        "progression_goal": item.progression_goal,
        "progression_rules": item.progression_rules,
        "ai_adjust_enabled": item.ai_adjust_enabled,
    }


def _normalize_template_scope(
    db: Session,
    payload_data: dict,
    *,
    current_sport_id: int | None = None,
    current_team_id: int | None = None,
) -> dict:
    normalized = dict(payload_data)
    target_team_id = normalized.get("team_id", current_team_id)
    target_sport_id = normalized.get("sport_id", current_sport_id)

    if target_team_id is not None:
        team = db.query(Team).filter(Team.id == target_team_id).first()
        if not team:
            raise bad_request("模板关联队伍不存在，请先刷新后重试。")
        if target_sport_id is not None and target_sport_id != team.sport_id:
            raise bad_request("模板关联队伍与项目不一致，请重新选择。")
        normalized["team_id"] = team.id
        normalized["sport_id"] = team.sport_id
        return normalized

    if target_sport_id is not None:
        sport = db.query(Sport).filter(Sport.id == target_sport_id).first()
        if not sport:
            raise bad_request("模板归属项目不存在，请先刷新后重试。")
        normalized["sport_id"] = sport.id
        normalized["team_id"] = None
        return normalized

    normalized["sport_id"] = None
    normalized["team_id"] = None
    return normalized


def _normalize_visibility_filter(value: str | None) -> str:
    normalized = (value or "all").strip().lower()
    if normalized in {"", "all"}:
        return "all"
    if normalized not in VALID_TEMPLATE_VISIBILITIES:
        raise bad_request("模板可见性筛选不受支持")
    return normalized


def _normalize_visibility(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in VALID_TEMPLATE_VISIBILITIES:
        raise bad_request("模板可见性不受支持")
    return normalized


def _resolve_create_ownership(db: Session, payload: PlanTemplateCreate, current_user: User) -> dict:
    if access_control_service.is_admin(current_user):
        visibility = _normalize_visibility(payload.visibility or TEMPLATE_VISIBILITY_PUBLIC)
        if visibility == TEMPLATE_VISIBILITY_PUBLIC:
            if payload.owner_user_id is not None:
                raise bad_request("公共模板不能指定归属教练")
            return {"visibility": TEMPLATE_VISIBILITY_PUBLIC, "owner_user_id": None, "source_template_id": None}

        if payload.owner_user_id is None:
            raise bad_request("管理员创建自建模板时必须选择归属教练")
        owner = _get_active_coach_user(db, payload.owner_user_id)
        return {"visibility": TEMPLATE_VISIBILITY_PRIVATE, "owner_user_id": owner.id, "source_template_id": None}

    return {
        "visibility": TEMPLATE_VISIBILITY_PRIVATE,
        "owner_user_id": current_user.id,
        "source_template_id": None,
    }


def _resolve_update_ownership(db: Session, template: TrainingPlanTemplate, updates: dict) -> dict:
    if "visibility" not in updates and "owner_user_id" not in updates:
        return {}

    next_visibility = _normalize_visibility(updates.get("visibility") or template.visibility)
    if next_visibility == TEMPLATE_VISIBILITY_PUBLIC:
        if updates.get("owner_user_id") is not None:
            raise bad_request("公共模板不能指定归属教练")
        return {"visibility": TEMPLATE_VISIBILITY_PUBLIC, "owner_user_id": None}

    owner_user_id = updates.get("owner_user_id", template.owner_user_id)
    if owner_user_id is None:
        raise bad_request("自建模板必须指定归属教练")
    owner = _get_active_coach_user(db, owner_user_id)
    return {"visibility": TEMPLATE_VISIBILITY_PRIVATE, "owner_user_id": owner.id}


def _get_active_coach_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise bad_request("目标教练账号不存在或未启用")
    if access_control_service.normalize_role_code(user.role_code) != "coach":
        raise bad_request("目标归属用户必须是教练账号")
    return user


def _resolve_copy_name(source_name: str, requested_name: str | None, suffix: str) -> str:
    base_name = (requested_name or "").strip()
    if not base_name:
        base_name = f"{source_name} - {suffix}"
    if len(base_name) > MAX_TEMPLATE_NAME_LENGTH:
        base_name = base_name[:MAX_TEMPLATE_NAME_LENGTH].rstrip()
    if not base_name:
        raise bad_request("模板名称不能为空")
    return base_name


def _get_template_module_for_template(db: Session, template_id: int, module_id: int) -> TrainingPlanTemplateModule:
    module = (
        db.query(TrainingPlanTemplateModule)
        .filter(
            TrainingPlanTemplateModule.id == module_id,
            TrainingPlanTemplateModule.template_id == template_id,
        )
        .first()
    )
    if not module:
        raise bad_request("模板模块不存在，请先刷新后重试。")
    return module


def _get_template_item_exercise(db: Session, exercise_id: int | None, *, current_user: User) -> Exercise:
    if not exercise_id or exercise_id <= 0:
        raise bad_request("模板动作还没有选择训练动作，请先补全后再保存。")

    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise bad_request("所选动作不存在，请重新选择后再保存。")
    if not access_control_service.is_admin(current_user) and not exercise_service.can_view_exercise(current_user, exercise):
        raise bad_request("无权使用其他教练的自建动作，请重新选择。")
    return exercise
