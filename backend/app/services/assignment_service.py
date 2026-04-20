from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import Athlete, AssignmentItemOverride, AthletePlanAssignment, TrainingPlanTemplate, TrainingPlanTemplateItem
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentOverrideCreate,
    AssignmentOverrideUpdate,
    AssignmentUpdate,
    BatchAssignmentCancel,
    BatchAssignmentCreate,
)
from app.services import athlete_service
from app.services.load_prescription_service import build_assignment_item_override, describe_load_mode


def _validate_window(db: Session, athlete_id: int, start_date: date, end_date: date, ignore_id: int | None = None) -> None:
    if start_date > end_date:
        raise bad_request("开始日期不能晚于结束日期")


def list_assignments(db: Session) -> list[AthletePlanAssignment]:
    return (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.template).joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise),
            joinedload(AthletePlanAssignment.overrides),
        )
        .order_by(AthletePlanAssignment.start_date.desc(), AthletePlanAssignment.id.desc())
        .all()
    )


def get_assignment(db: Session, assignment_id: int) -> AthletePlanAssignment:
    assignment = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.template).joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise),
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(AthletePlanAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise not_found("未找到计划分配记录")
    return assignment


def create_assignment(db: Session, payload: AssignmentCreate) -> AthletePlanAssignment:
    _validate_window(db, payload.athlete_id, payload.start_date, payload.end_date)
    assignment = AthletePlanAssignment(**payload.model_dump(exclude={"overrides"}))
    db.add(assignment)
    db.flush()
    for override in payload.overrides:
        db.add(
            AssignmentItemOverride(
                assignment_id=assignment.id,
                template_item_id=override.template_item_id,
                initial_load_override=override.initial_load_override,
            )
        )
    db.commit()
    return get_assignment(db, assignment.id)


def update_assignment(db: Session, assignment_id: int, payload: AssignmentUpdate) -> AthletePlanAssignment:
    assignment = db.query(AthletePlanAssignment).filter(AthletePlanAssignment.id == assignment_id).first()
    if not assignment:
        raise not_found("未找到计划分配记录")

    updates = payload.model_dump(exclude_unset=True)
    start_date = updates.get("start_date", assignment.start_date)
    end_date = updates.get("end_date", assignment.end_date)
    _validate_window(db, assignment.athlete_id, start_date, end_date, assignment_id)

    for key, value in updates.items():
        setattr(assignment, key, value)

    db.commit()
    return get_assignment(db, assignment_id)


def create_override(db: Session, assignment_id: int, payload: AssignmentOverrideCreate) -> AthletePlanAssignment:
    assignment = db.query(AthletePlanAssignment).filter(AthletePlanAssignment.id == assignment_id).first()
    if not assignment:
        raise not_found("未找到计划分配记录")

    override = (
        db.query(AssignmentItemOverride)
        .filter(
            AssignmentItemOverride.assignment_id == assignment_id,
            AssignmentItemOverride.template_item_id == payload.template_item_id,
        )
        .first()
    )
    if override:
        override.initial_load_override = payload.initial_load_override
    else:
        db.add(AssignmentItemOverride(assignment_id=assignment_id, **payload.model_dump()))

    db.commit()
    return get_assignment(db, assignment_id)


def update_override(db: Session, override_id: int, payload: AssignmentOverrideUpdate) -> AssignmentItemOverride:
    override = db.query(AssignmentItemOverride).filter(AssignmentItemOverride.id == override_id).first()
    if not override:
        raise not_found("未找到负荷覆盖项")

    override.initial_load_override = payload.initial_load_override
    db.commit()
    db.refresh(override)
    return override


def get_active_assignment_for_date(db: Session, athlete_id: int, target_date: date) -> AthletePlanAssignment | None:
    assignments = list_active_assignments_for_date(db, athlete_id, target_date)
    return assignments[0] if assignments else None


def list_active_assignments_for_date(db: Session, athlete_id: int, target_date: date) -> list[AthletePlanAssignment]:
    return (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.template).joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise),
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(
            AthletePlanAssignment.athlete_id == athlete_id,
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.start_date <= target_date,
            AthletePlanAssignment.end_date >= target_date,
        )
        .order_by(AthletePlanAssignment.assigned_date.desc(), AthletePlanAssignment.id.desc())
        .all()
    )


def preview_batch_assignments(db: Session, payload: BatchAssignmentCreate) -> dict:
    template = _get_template_for_assignment(db, payload.template_id)
    rows = []
    for athlete_id in payload.athlete_ids:
        athlete = athlete_service.get_athlete(db, athlete_id)
        items = []
        for item in template.items:
            override = build_assignment_item_override(db, athlete.id, item)
            is_manual_load = item.initial_load_mode == "percent_1rm" and not override
            items.append(
                {
                    "template_item_id": item.id,
                    "exercise_name": item.exercise.name,
                    "load_mode_label": describe_load_mode(item),
                    "computed_load": override["initial_load_override"] if override else None,
                    "basis_label": "训练时录入" if is_manual_load else (override["basis_label"] if override else None),
                    "status": "missing_basis" if is_manual_load else "assignable",
                }
            )
        rows.append({"athlete": athlete, "items": items})

    return {
        "template": template,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "rows": rows,
    }


def create_batch_assignments(db: Session, payload: BatchAssignmentCreate) -> list[AthletePlanAssignment]:
    preview = preview_batch_assignments(db, payload)
    created_ids: list[int] = []

    for athlete_id in payload.athlete_ids:
        _validate_window(db, athlete_id, payload.start_date, payload.end_date)
        assignment = AthletePlanAssignment(
            athlete_id=athlete_id,
            template_id=payload.template_id,
            assigned_date=payload.assigned_date,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=payload.status,
            notes=payload.notes,
        )
        db.add(assignment)
        db.flush()

        template = preview["template"]
        for item in template.items:
            override = build_assignment_item_override(db, athlete_id, item)
            if override:
                db.add(
                    AssignmentItemOverride(
                        assignment_id=assignment.id,
                        template_item_id=override["template_item_id"],
                        initial_load_override=override["initial_load_override"],
                    )
                )

        created_ids.append(assignment.id)

    db.commit()
    return [get_assignment(db, assignment_id) for assignment_id in created_ids]


def cancel_batch_assignments(db: Session, payload: BatchAssignmentCancel) -> list[AthletePlanAssignment]:
    if not payload.assignment_ids:
        raise bad_request("请先选择要取消的计划分配")

    assignments = (
        db.query(AthletePlanAssignment)
        .filter(AthletePlanAssignment.id.in_(payload.assignment_ids))
        .all()
    )
    if len(assignments) != len(set(payload.assignment_ids)):
        raise not_found("存在未找到的计划分配记录")

    for assignment in assignments:
        assignment.status = "cancelled"

    db.commit()
    return [get_assignment(db, assignment.id) for assignment in assignments]


def assignment_overview(db: Session, target_date: date) -> dict:
    assignments = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            joinedload(AthletePlanAssignment.template).joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise),
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.start_date <= target_date,
            AthletePlanAssignment.end_date >= target_date,
        )
        .order_by(AthletePlanAssignment.start_date.desc(), AthletePlanAssignment.id.desc())
        .all()
    )

    grouped: dict[tuple[int, date, date], dict] = {}
    for assignment in assignments:
        group_key = (assignment.template_id, assignment.start_date, assignment.end_date)
        group = grouped.setdefault(
            group_key,
            {
                "template": assignment.template,
                "start_date": assignment.start_date,
                "end_date": assignment.end_date,
                "entries": [],
                "athletes": [],
                "assignment_ids": [],
                "notes": [],
            },
        )
        group["entries"].append(
            {
                "assignment_id": assignment.id,
                "athlete": assignment.athlete,
                "notes": assignment.notes,
            }
        )
        group["athletes"].append(assignment.athlete)
        group["assignment_ids"].append(assignment.id)
        if assignment.notes:
            group["notes"].append(assignment.notes)

    assignment_groups = []
    for group in grouped.values():
        group["entries"].sort(key=lambda entry: entry["athlete"].full_name)
        group["athletes"].sort(key=lambda athlete: athlete.full_name)
        group["notes"] = sorted(set(group["notes"]))
        group["athlete_count"] = len(group["athletes"])
        assignment_groups.append(group)

    assignment_groups.sort(
        key=lambda group: (
            group["start_date"],
            group["end_date"],
            group["template"].name.lower(),
        ),
        reverse=True,
    )

    assigned_ids = {assignment.athlete_id for assignment in assignments}
    unassigned = [
        athlete
        for athlete in athlete_service.list_athletes(db)
        if athlete.is_active and athlete.id not in assigned_ids
    ]
    return {
        "assignment_groups": assignment_groups,
        "unassigned_athletes": unassigned,
        "assigned_count": len(assigned_ids),
        "unassigned_count": len(unassigned),
        "group_count": len(assignment_groups),
    }


def _get_template_for_assignment(db: Session, template_id: int) -> TrainingPlanTemplate:
    template = (
        db.query(TrainingPlanTemplate)
        .options(joinedload(TrainingPlanTemplate.items).joinedload(TrainingPlanTemplateItem.exercise))
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("未找到训练模板")
    return template
