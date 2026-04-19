from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import TrainingPlanTemplate, TrainingPlanTemplateItem
from app.schemas.training_plan import PlanTemplateCreate, PlanTemplateItemCreate, PlanTemplateItemUpdate, PlanTemplateUpdate


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
        raise not_found("未找到训练模板")
    return template


def create_template(db: Session, payload: PlanTemplateCreate, created_by: int | None) -> TrainingPlanTemplate:
    template = TrainingPlanTemplate(**payload.model_dump(), created_by=created_by)
    db.add(template)
    db.commit()
    db.refresh(template)
    return get_template(db, template.id)


def update_template(db: Session, template_id: int, payload: PlanTemplateUpdate) -> TrainingPlanTemplate:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("未找到训练模板")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.commit()
    return get_template(db, template_id)


def add_template_item(db: Session, template_id: int, payload: PlanTemplateItemCreate) -> TrainingPlanTemplate:
    db.add(TrainingPlanTemplateItem(template_id=template_id, **payload.model_dump()))
    db.commit()
    return get_template(db, template_id)


def update_template_item(db: Session, item_id: int, payload: PlanTemplateItemUpdate) -> TrainingPlanTemplateItem:
    item = db.query(TrainingPlanTemplateItem).filter(TrainingPlanTemplateItem.id == item_id).first()
    if not item:
        raise not_found("未找到模板动作")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_template_item(db: Session, item_id: int) -> None:
    item = db.query(TrainingPlanTemplateItem).filter(TrainingPlanTemplateItem.id == item_id).first()
    if not item:
        raise not_found("未找到模板动作")
    db.delete(item)
    db.commit()


def delete_template(db: Session, template_id: int) -> None:
    template = db.query(TrainingPlanTemplate).filter(TrainingPlanTemplate.id == template_id).first()
    if not template:
        raise not_found("未找到训练模板")
    db.delete(template)
    db.commit()
