from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import (
    Athlete,
    AssignmentItemOverride,
    AthletePlanAssignment,
    TestMetricDefinition,
    TrainingPlanTemplate,
    TrainingPlanTemplateItem,
    TrainingPlanTemplateModule,
)
from app.schemas.assignment import (
    DEFAULT_REPEAT_WEEKDAYS,
    AssignmentCreate,
    AssignmentOverrideCreate,
    AssignmentOverrideUpdate,
    AssignmentUpdate,
    BatchAssignmentCancel,
    BatchAssignmentCreate,
)
from app.services import athlete_service
from app.services.load_prescription_service import build_assignment_item_override, describe_load_mode


ASSIGNMENT_TEMPLATE_LOAD_OPTIONS = (
    joinedload(AthletePlanAssignment.template)
    .joinedload(TrainingPlanTemplate.modules)
    .joinedload(TrainingPlanTemplateModule.items)
    .joinedload(TrainingPlanTemplateItem.exercise),
    joinedload(AthletePlanAssignment.template)
    .joinedload(TrainingPlanTemplate.modules)
    .joinedload(TrainingPlanTemplateModule.items)
    .joinedload(TrainingPlanTemplateItem.initial_load_test_metric_definition)
    .joinedload(TestMetricDefinition.test_type),
    joinedload(AthletePlanAssignment.template)
    .joinedload(TrainingPlanTemplate.items)
    .joinedload(TrainingPlanTemplateItem.exercise),
    joinedload(AthletePlanAssignment.template)
    .joinedload(TrainingPlanTemplate.items)
    .joinedload(TrainingPlanTemplateItem.initial_load_test_metric_definition)
    .joinedload(TestMetricDefinition.test_type),
    joinedload(AthletePlanAssignment.template)
    .joinedload(TrainingPlanTemplate.items)
    .joinedload(TrainingPlanTemplateItem.module)
    .joinedload(TrainingPlanTemplateModule.items),
)


def _normalize_repeat_weekdays(value: list[int] | tuple[int, ...] | None) -> list[int]:
    if value is None:
        return DEFAULT_REPEAT_WEEKDAYS.copy()
    weekdays = sorted({int(day) for day in value if 1 <= int(day) <= 7})
    return weekdays or DEFAULT_REPEAT_WEEKDAYS.copy()


def get_assignment_repeat_weekdays(assignment: AthletePlanAssignment) -> list[int]:
    return _normalize_repeat_weekdays(getattr(assignment, "repeat_weekdays", None))


def is_assignment_scheduled_for_date(assignment: AthletePlanAssignment | None, target_date: date) -> bool:
    if assignment is None:
        return False
    if target_date < assignment.start_date or target_date > assignment.end_date:
        return False
    return target_date.isoweekday() in set(get_assignment_repeat_weekdays(assignment))


def has_assignment_occurrence_on_or_after(assignment: AthletePlanAssignment, target_date: date) -> bool:
    window_start = max(assignment.start_date, target_date)
    if window_start > assignment.end_date:
        return False

    weekdays = get_assignment_repeat_weekdays(assignment)
    if len(weekdays) == 7:
        return True

    current_weekday = window_start.isoweekday()
    for weekday in weekdays:
        delta_days = (weekday - current_weekday) % 7
        candidate_date = window_start + timedelta(days=delta_days)
        if candidate_date <= assignment.end_date:
            return True
    return False


def ensure_assignment_scheduled_for_date(assignment: AthletePlanAssignment, target_date: date) -> None:
    if not is_assignment_scheduled_for_date(assignment, target_date):
        raise bad_request("该计划在所选日期不是应训练日")


def find_assignment_date_conflicts(
    db: Session,
    athlete_id: int,
    start_date: date,
    end_date: date,
    repeat_weekdays: list[int] | None,
    assignment_status: str = "active",
    ignore_id: int | None = None,
) -> list[dict]:
    if assignment_status != "active" or start_date > end_date:
        return []

    candidates = (
        db.query(AthletePlanAssignment)
        .options(joinedload(AthletePlanAssignment.template))
        .filter(
            AthletePlanAssignment.athlete_id == athlete_id,
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.start_date <= end_date,
            AthletePlanAssignment.end_date >= start_date,
        )
    )
    if ignore_id is not None:
        candidates = candidates.filter(AthletePlanAssignment.id != ignore_id)

    target_weekdays = _normalize_repeat_weekdays(repeat_weekdays)
    conflicts = []
    for assignment in candidates.order_by(AthletePlanAssignment.start_date.asc(), AthletePlanAssignment.id.asc()).all():
        conflict_dates = _find_overlapping_scheduled_dates(
            start_date,
            end_date,
            target_weekdays,
            assignment,
        )
        if not conflict_dates:
            continue
        conflicts.append(
            {
                "assignment": assignment,
                "assignment_id": assignment.id,
                "template_id": assignment.template_id,
                "template_name": assignment.template.name if assignment.template else None,
                "start_date": assignment.start_date,
                "end_date": assignment.end_date,
                "repeat_weekdays": get_assignment_repeat_weekdays(assignment),
                "dates": conflict_dates,
            }
        )
    return conflicts


def _validate_window(
    db: Session,
    athlete_id: int,
    start_date: date,
    end_date: date,
    repeat_weekdays: list[int] | None,
    assignment_status: str = "active",
    ignore_id: int | None = None,
) -> None:
    if start_date > end_date:
        raise bad_request("开始日期不能晚于结束日期")

    if assignment_status != "active":
        return

    conflicts = find_assignment_date_conflicts(
        db,
        athlete_id,
        start_date,
        end_date,
        repeat_weekdays,
        assignment_status,
        ignore_id,
    )
    if conflicts:
        raise bad_request(_build_assignment_conflict_message(conflicts))


def _begin_immediate_for_assignment_conflict_check(db: Session) -> bool:
    if db.get_bind().dialect.name != "sqlite":
        return False

    connection = db.connection()
    driver_connection = getattr(connection.connection, "driver_connection", None)
    if driver_connection is not None and getattr(driver_connection, "in_transaction", False):
        return False

    connection.exec_driver_sql("BEGIN IMMEDIATE")
    return True


def list_assignments(db: Session, sport_id: int | None = None) -> list[AthletePlanAssignment]:
    query = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            *ASSIGNMENT_TEMPLATE_LOAD_OPTIONS,
            joinedload(AthletePlanAssignment.overrides),
        )
    )
    if sport_id is not None:
        query = query.join(Athlete, Athlete.id == AthletePlanAssignment.athlete_id).filter(Athlete.sport_id == sport_id)
    return query.order_by(AthletePlanAssignment.start_date.desc(), AthletePlanAssignment.id.desc()).all()


def get_assignment(db: Session, assignment_id: int) -> AthletePlanAssignment:
    assignment = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            *ASSIGNMENT_TEMPLATE_LOAD_OPTIONS,
            joinedload(AthletePlanAssignment.overrides),
        )
        .filter(AthletePlanAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise not_found("未找到计划分配记录")
    return assignment


def create_assignment(db: Session, payload: AssignmentCreate) -> AthletePlanAssignment:
    _begin_immediate_for_assignment_conflict_check(db)
    _validate_window(
        db,
        payload.athlete_id,
        payload.start_date,
        payload.end_date,
        payload.repeat_weekdays,
        payload.status,
    )
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
    repeat_weekdays = updates.get("repeat_weekdays", assignment.repeat_weekdays)
    status = updates.get("status", assignment.status)
    _begin_immediate_for_assignment_conflict_check(db)
    _validate_window(db, assignment.athlete_id, start_date, end_date, repeat_weekdays, status, assignment_id)

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
    assignments = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            *ASSIGNMENT_TEMPLATE_LOAD_OPTIONS,
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
    return [assignment for assignment in assignments if is_assignment_scheduled_for_date(assignment, target_date)]


def preview_batch_assignments(db: Session, payload: BatchAssignmentCreate) -> dict:
    template = _get_template_for_assignment(db, payload.template_id)
    rows = []
    for athlete_id in payload.athlete_ids:
        athlete = athlete_service.get_athlete(db, athlete_id)
        conflicts = find_assignment_date_conflicts(
            db,
            athlete.id,
            payload.start_date,
            payload.end_date,
            payload.repeat_weekdays,
            payload.status,
        )
        conflict_dates = _flatten_conflict_dates(conflicts)
        items = []
        for item in template.items:
            override = build_assignment_item_override(db, athlete.id, item)
            is_manual_load = item.initial_load_mode == "percent_1rm" and not override
            items.append(
                {
                    "template_item_id": item.id,
                    "module_id": item.module_id,
                    "module_code": item.module_code,
                    "module_title": item.module_title,
                    "display_index": item.display_index,
                    "display_code": item.display_code,
                    "exercise_name": item.exercise.name,
                    "load_mode_label": describe_load_mode(item),
                    "computed_load": override["initial_load_override"] if override else None,
                    "basis_label": "控制" if is_manual_load else (override["basis_label"] if override else None),
                    "status": "manual_control" if is_manual_load else "assignable",
                }
            )
        rows.append(
            {
                "athlete": athlete,
                "items": items,
                "conflict_status": "conflict" if conflict_dates else "none",
                "conflict_dates": conflict_dates,
                "conflict_message": _build_assignment_conflict_message(conflicts) if conflict_dates else None,
            }
        )

    return {
        "template": template,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "repeat_weekdays": payload.repeat_weekdays,
        "rows": rows,
    }


def create_batch_assignments(db: Session, payload: BatchAssignmentCreate) -> list[AthletePlanAssignment]:
    _begin_immediate_for_assignment_conflict_check(db)
    preview = preview_batch_assignments(db, payload)
    created_ids: list[int] = []

    for athlete_id in payload.athlete_ids:
        _validate_window(
            db,
            athlete_id,
            payload.start_date,
            payload.end_date,
            payload.repeat_weekdays,
            payload.status,
        )
        assignment = AthletePlanAssignment(
            athlete_id=athlete_id,
            template_id=payload.template_id,
            assigned_date=payload.assigned_date,
            start_date=payload.start_date,
            end_date=payload.end_date,
            repeat_weekdays=payload.repeat_weekdays,
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


def assignment_overview(db: Session, target_date: date, sport_id: int | None = None) -> dict:
    query = (
        db.query(AthletePlanAssignment)
        .options(
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.sport),
            joinedload(AthletePlanAssignment.athlete).joinedload(Athlete.team),
            *ASSIGNMENT_TEMPLATE_LOAD_OPTIONS,
            joinedload(AthletePlanAssignment.overrides),
        )
    )
    if sport_id is not None:
        query = query.join(Athlete, Athlete.id == AthletePlanAssignment.athlete_id).filter(Athlete.sport_id == sport_id)
    assignments = (
        query.filter(
            AthletePlanAssignment.status == "active",
            AthletePlanAssignment.end_date >= target_date,
        )
        .order_by(AthletePlanAssignment.start_date.asc(), AthletePlanAssignment.id.asc())
        .all()
    )
    assignments = [assignment for assignment in assignments if has_assignment_occurrence_on_or_after(assignment, target_date)]

    grouped: dict[tuple[int, date, date, tuple[int, ...]], dict] = {}
    for assignment in assignments:
        repeat_weekdays = get_assignment_repeat_weekdays(assignment)
        group_key = (assignment.template_id, assignment.start_date, assignment.end_date, tuple(repeat_weekdays))
        group = grouped.setdefault(
            group_key,
            {
                "template": assignment.template,
                "start_date": assignment.start_date,
                "end_date": assignment.end_date,
                "repeat_weekdays": repeat_weekdays,
                "group_status": "active_now" if assignment.start_date <= target_date else "upcoming",
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
            0 if group["group_status"] == "active_now" else 1,
            group["start_date"],
            group["template"].name.lower(),
        ),
    )

    assigned_ids = {assignment.athlete_id for assignment in assignments}
    unassigned = [
        athlete
        for athlete in athlete_service.list_athletes(db, sport_id=sport_id)
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
        .options(
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
        .filter(TrainingPlanTemplate.id == template_id)
        .first()
    )
    if not template:
        raise not_found("未找到训练模板")
    return template


def _find_overlapping_scheduled_dates(
    start_date: date,
    end_date: date,
    repeat_weekdays: list[int],
    assignment: AthletePlanAssignment,
) -> list[date]:
    overlap_start = max(start_date, assignment.start_date)
    overlap_end = min(end_date, assignment.end_date)
    if overlap_start > overlap_end:
        return []

    overlapping_weekdays = set(repeat_weekdays) & set(get_assignment_repeat_weekdays(assignment))
    conflict_dates: list[date] = []
    for weekday in sorted(overlapping_weekdays):
        days_until_weekday = (weekday - overlap_start.isoweekday()) % 7
        current = overlap_start + timedelta(days=days_until_weekday)
        while current <= overlap_end:
            conflict_dates.append(current)
            current += timedelta(days=7)
    return sorted(conflict_dates)


def _flatten_conflict_dates(conflicts: list[dict]) -> list[date]:
    return sorted({conflict_date for conflict in conflicts for conflict_date in conflict["dates"]})


def _build_assignment_conflict_message(conflicts: list[dict]) -> str:
    conflict_dates = _flatten_conflict_dates(conflicts)
    if not conflict_dates:
        return ""

    date_text = _format_conflict_dates(conflict_dates)
    template_names = sorted(
        {
            conflict["template_name"]
            for conflict in conflicts
            if conflict.get("template_name")
        }
    )
    template_text = f"（已有计划：{'、'.join(template_names[:3])}）" if template_names else ""
    return f"该队员在 {date_text} 已有有效计划分配{template_text}，同一天最多只能有一个 active 计划。"


def _format_conflict_dates(conflict_dates: list[date], max_visible_dates: int = 6) -> str:
    visible_dates = conflict_dates[:max_visible_dates]
    date_text = "、".join(conflict_date.isoformat() for conflict_date in visible_dates)
    remaining_count = len(conflict_dates) - len(visible_dates)
    if remaining_count > 0:
        date_text = f"{date_text} 等 {len(conflict_dates)} 天"
    return date_text
