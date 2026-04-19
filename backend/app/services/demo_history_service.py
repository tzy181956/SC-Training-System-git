from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models import AthletePlanAssignment, SetRecord, TrainingSession, TrainingSessionItem


def seed_training_demo_history(db: Session) -> None:
    """Create coach-visible demo training history so report pages have meaningful data."""
    if db.query(SetRecord).first():
        return

    assignments = (
        db.query(AthletePlanAssignment)
        .filter(AthletePlanAssignment.status == "active")
        .order_by(AthletePlanAssignment.id.asc())
        .all()
    )
    if not assignments:
        return

    assignment_map = {
        (assignment.athlete.full_name, assignment.template.name): assignment
        for assignment in assignments
        if assignment.athlete and assignment.template
    }

    _create_session(
        db,
        assignment_map.get(("王浩", "力量训练 A")),
        date.today() - timedelta(days=8),
        "completed",
        [
            [(118, 5, 2, 123), (123, 5, 2, 128), (128, 5, 1, 128), (126, 5, 1, 123)],
            [(72, 6, 2, 74.5), (74.5, 6, 2, 77), (77, 5, 1, 74.5), (74.5, 6, 2, 74.5)],
            [(0, 45, 4, 0), (0, 45, 4, 0), (0, 40, 3, 0)],
        ],
    )
    _create_session(
        db,
        assignment_map.get(("王浩", "力量训练 A")),
        date.today() - timedelta(days=3),
        "completed",
        [
            [(120, 5, 3, 125), (125, 5, 2, 130), (130, 4, 1, 127.5), (127.5, 5, 2, 127.5)],
            [(75, 6, 3, 77.5), (77.5, 6, 2, 77.5), (77.5, 6, 1, 75)],
            [(0, 45, 4, 0), (0, 45, 4, 0), (0, 45, 4, 0)],
        ],
    )
    _create_session(
        db,
        assignment_map.get(("赵磊", "力量训练 A")),
        date.today() - timedelta(days=6),
        "in_progress",
        [
            [(130, 5, 2, 135), (135, 5, 1, 132.5)],
            [(80, 6, 2, 82.5), (82.5, 5, 1, 80)],
            [(0, 45, 4, 0)],
        ],
    )
    _create_session(
        db,
        assignment_map.get(("高远", "排球力量基础")),
        date.today() - timedelta(days=2),
        "completed",
        [
            [(112.5, 4, 3, 115), (115, 4, 2, 117.5), (117.5, 4, 1, 115), (115, 4, 2, 115)],
            [(14, 8, 3, 16), (16, 8, 2, 16), (16, 8, 2, 18)],
            [(0, 10, 3, 0), (0, 10, 2, 0), (0, 9, 1, 0)],
        ],
    )

    db.flush()


def _create_session(
    db: Session,
    assignment: AthletePlanAssignment | None,
    session_date: date,
    status: str,
    set_matrix: list[list[tuple[float, int, int, float]]],
) -> None:
    if not assignment or not assignment.template:
        return

    session = TrainingSession(
        athlete_id=assignment.athlete_id,
        assignment_id=assignment.id,
        template_id=assignment.template_id,
        session_date=session_date,
        status=status,
        started_at=datetime.combine(session_date, time(hour=15, minute=0)),
        completed_at=datetime.combine(session_date, time(hour=16, minute=10)) if status == "completed" else None,
        coach_note="示例训练记录",
        athlete_note="用于训练数据查看模块演示",
    )
    db.add(session)
    db.flush()

    for index, template_item in enumerate(assignment.template.items):
        item = TrainingSessionItem(
            session_id=session.id,
            template_item_id=template_item.id,
            exercise_id=template_item.exercise_id,
            sort_order=template_item.sort_order,
            prescribed_sets=template_item.prescribed_sets,
            prescribed_reps=template_item.prescribed_reps,
            target_note=template_item.target_note,
            is_main_lift=template_item.is_main_lift,
            enable_auto_load=template_item.enable_auto_load,
            initial_load=template_item.initial_load_value,
            status="completed" if index < len(set_matrix) and len(set_matrix[index]) >= template_item.prescribed_sets else "in_progress",
        )
        db.add(item)
        db.flush()

        records = set_matrix[index] if index < len(set_matrix) else []
        for set_number, (actual_weight, actual_reps, actual_rir, next_suggestion) in enumerate(records, start=1):
            target_weight = _resolve_target_weight(item, actual_weight, set_number)
            final_weight = actual_weight
            decision = "accepted"
            if set_number > 1:
                previous_suggestion = records[set_number - 2][3]
                if final_weight != previous_suggestion:
                    decision = "modified"
            elif item.initial_load is not None and final_weight != item.initial_load:
                decision = "modified"

            db.add(
                SetRecord(
                    session_item_id=item.id,
                    set_number=set_number,
                    target_weight=target_weight,
                    target_reps=item.prescribed_reps,
                    actual_weight=actual_weight,
                    actual_reps=actual_reps,
                    actual_rir=actual_rir,
                    suggestion_weight=next_suggestion,
                    suggestion_reason="示例建议",
                    user_decision=decision,
                    final_weight=final_weight,
                    completed_at=datetime.combine(session_date, time(hour=15, minute=10 + set_number * 6)),
                    notes="示例数据",
                )
            )


def _resolve_target_weight(item: TrainingSessionItem, actual_weight: float, set_number: int) -> float:
    if set_number == 1:
        return item.initial_load if item.initial_load is not None else actual_weight
    return actual_weight
