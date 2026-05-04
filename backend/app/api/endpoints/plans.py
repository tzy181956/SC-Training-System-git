from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.schemas.dangerous_action import DangerousActionConfirm
from app.schemas.training_plan import PlanTemplateCreate, PlanTemplateItemCreate, PlanTemplateItemRead, PlanTemplateItemUpdate, PlanTemplateRead, PlanTemplateUpdate
from app.services import dangerous_operation_service, plan_service


router = APIRouter(prefix="/plan-templates", tags=["plan-templates"])


@router.get("", response_model=list[PlanTemplateRead])
def list_templates(db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return plan_service.list_templates(db)


@router.post("", response_model=PlanTemplateRead)
def create_template(payload: PlanTemplateCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return plan_service.create_template(db, payload, None)


@router.get("/{template_id}", response_model=PlanTemplateRead)
def get_template(template_id: int, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return plan_service.get_template(db, template_id)


@router.patch("/{template_id}", response_model=PlanTemplateRead)
def update_template(template_id: int, payload: PlanTemplateUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return plan_service.update_template(db, template_id, payload)


@router.post("/{template_id}/items", response_model=PlanTemplateRead)
def add_item(template_id: int, payload: PlanTemplateItemCreate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return plan_service.add_template_item(db, template_id, payload)


@router.patch("/items/{item_id}", response_model=PlanTemplateItemRead)
def update_item(item_id: int, payload: PlanTemplateItemUpdate, db: Session = Depends(get_db), _=Depends(require_roles("coach"))):
    return plan_service.update_template_item(db, item_id, payload)


@router.delete("/items/{item_id}", response_model=dict[str, str])
def delete_item(
    item_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    _=Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除模板动作")
    plan_service.delete_template_item(db, item_id, actor_name=payload.actor_name)
    return {"message": "deleted"}


@router.delete("/{template_id}", response_model=dict[str, str])
def delete_template(
    template_id: int,
    payload: DangerousActionConfirm,
    db: Session = Depends(get_db),
    _=Depends(require_roles("coach")),
):
    dangerous_operation_service.require_confirmation(payload, action_label="删除训练模板")
    plan_service.delete_template(db, template_id, actor_name=payload.actor_name)
    return {"message": "deleted"}
