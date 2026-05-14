from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.training_plan import (
    PlanTemplateCreate,
    PlanTemplateCopyPayload,
    PlanTemplateItemCreate,
    PlanTemplateItemRead,
    PlanTemplateItemUpdate,
    PlanTemplateListRead,
    PlanTemplateModuleCreate,
    PlanTemplateModuleRead,
    PlanTemplateModuleUpdate,
    PlanTemplateRead,
    PlanTemplateUpdate,
)
from app.services import access_control_service, dangerous_operation_service, plan_service


router = APIRouter(prefix="/plan-templates", tags=["plan-templates"])


@router.get("", response_model=list[PlanTemplateListRead])
def list_templates(
    visibility: str | None = Query(default="all"),
    owner_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    return plan_service.list_templates(
        db,
        current_user=current_user,
        visibility=visibility,
        owner_user_id=owner_user_id,
    )


@router.post("", response_model=PlanTemplateRead)
def create_template(
    payload: PlanTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    if not access_control_service.is_admin(current_user):
        if payload.team_id is not None:
            access_control_service.get_accessible_team(db, current_user, payload.team_id)
        payload = payload.model_copy(update={"sport_id": access_control_service.ensure_sport_bound_user(current_user)})
    return plan_service.create_template(db, payload, current_user, actor_name=current_user.display_name)


@router.get("/{template_id}", response_model=PlanTemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template(db, current_user, template_id, allow_global_read=True, allow_global_write=False)
    return plan_service.get_template(db, template_id)


@router.patch("/{template_id}", response_model=PlanTemplateRead)
def update_template(
    template_id: int,
    payload: PlanTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template(db, current_user, template_id, allow_global_read=False, allow_global_write=False)
    if not access_control_service.is_admin(current_user):
        if payload.team_id is not None:
            access_control_service.get_accessible_team(db, current_user, payload.team_id)
        payload = payload.model_copy(update={"sport_id": access_control_service.ensure_sport_bound_user(current_user)})
    return plan_service.update_template(db, template_id, payload, current_user, actor_name=current_user.display_name)


@router.post("/{template_id}/copy", response_model=PlanTemplateRead)
def copy_template(
    template_id: int,
    payload: PlanTemplateCopyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template(db, current_user, template_id, allow_global_read=True, allow_global_write=False)
    return plan_service.copy_template(db, template_id, payload, current_user, actor_name=current_user.display_name)


@router.post("/{template_id}/items", response_model=PlanTemplateRead)
def add_item(
    template_id: int,
    payload: PlanTemplateItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template(db, current_user, template_id, allow_global_read=False, allow_global_write=False)
    return plan_service.add_template_item(db, template_id, payload, current_user=current_user, actor_name=current_user.display_name)


@router.post("/{template_id}/modules", response_model=PlanTemplateModuleRead)
def add_module(
    template_id: int,
    payload: PlanTemplateModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template(db, current_user, template_id, allow_global_read=False, allow_global_write=False)
    return plan_service.add_template_module(db, template_id, payload, actor_name=current_user.display_name)


@router.patch("/items/{item_id}", response_model=PlanTemplateItemRead)
def update_item(
    item_id: int,
    payload: PlanTemplateItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template_item(db, current_user, item_id, allow_global_read=False, allow_global_write=False)
    return plan_service.update_template_item(db, item_id, payload, current_user=current_user, actor_name=current_user.display_name)


@router.patch("/modules/{module_id}", response_model=PlanTemplateModuleRead)
def update_module(
    module_id: int,
    payload: PlanTemplateModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    access_control_service.get_accessible_template_module(db, current_user, module_id, allow_global_read=False, allow_global_write=False)
    return plan_service.update_template_module(db, module_id, payload, actor_name=current_user.display_name)


@router.delete("/items/{item_id}", response_model=dict[str, str])
def delete_item(
    item_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除模板动作")
    access_control_service.get_accessible_template_item(db, current_user, item_id, allow_global_read=False, allow_global_write=False)
    plan_service.delete_template_item(db, item_id, actor_name=payload.actor_name or current_user.display_name)
    return {"message": "deleted"}


@router.delete("/modules/{module_id}", response_model=dict[str, str])
def delete_module(
    module_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除模板模块")
    access_control_service.get_accessible_template_module(db, current_user, module_id, allow_global_read=False, allow_global_write=False)
    plan_service.delete_template_module(db, module_id, actor_name=payload.actor_name or current_user.display_name)
    return {"message": "deleted"}


@router.delete("/{template_id}", response_model=dict[str, str])
def delete_template(
    template_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除训练模板")
    access_control_service.get_accessible_template(db, current_user, template_id, allow_global_read=False, allow_global_write=False)
    plan_service.delete_template(db, template_id, actor_name=payload.actor_name or current_user.display_name)
    return {"message": "deleted"}
