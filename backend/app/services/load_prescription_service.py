from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Exercise, TestRecord, TrainingPlanTemplateItem


def build_assignment_item_override(db: Session, athlete_id: int, item: TrainingPlanTemplateItem) -> dict | None:
    """Build one athlete-specific initial load override for a template item."""
    if item.initial_load_mode == "percent_1rm":
        basis = find_latest_reference_test(db, athlete_id, item.exercise)
        if not basis:
            return None
        percent = (item.initial_load_value or 0) / 100
        return {
            "template_item_id": item.id,
            "initial_load_override": round(basis.result_value * percent, 2),
            "basis_label": f"{basis.metric_name}（{basis.test_date}）",
        }

    if item.initial_load_mode == "fixed_weight" and item.initial_load_value is not None:
        return {
            "template_item_id": item.id,
            "initial_load_override": item.initial_load_value,
            "basis_label": "固定重量",
        }

    return None


def find_latest_reference_test(db: Session, athlete_id: int, exercise: Exercise) -> TestRecord | None:
    """Match the latest usable test record for one exercise."""
    keywords = _match_keywords(exercise)
    records = (
        db.query(TestRecord)
        .filter(TestRecord.athlete_id == athlete_id)
        .order_by(TestRecord.test_date.desc(), TestRecord.id.desc())
        .all()
    )
    for record in records:
        haystack = f"{record.metric_name} {record.test_type} {record.notes or ''}".lower()
        if any(keyword in haystack for keyword in keywords):
            return record
    return None


def describe_load_mode(item: TrainingPlanTemplateItem) -> str:
    """Return a Chinese label for the template item's load source."""
    if item.initial_load_mode == "percent_1rm":
        return f"按最近测试的 {item.initial_load_value or 0:.0f}% 计算"
    if item.initial_load_mode == "fixed_weight":
        return f"固定重量 {item.initial_load_value or 0:g} 公斤"
    return "分配时设置"


def _match_keywords(exercise: Exercise) -> list[str]:
    name_blob = f"{exercise.name} {exercise.alias or ''}".lower()
    if "深蹲" in name_blob or "squat" in name_blob:
        return ["深蹲", "squat"]
    if "卧推" in name_blob or "bench" in name_blob:
        return ["卧推", "bench"]
    if "硬拉" in name_blob or "deadlift" in name_blob:
        return ["硬拉", "deadlift"]
    if "推举" in name_blob or "press" in name_blob:
        return ["推举", "press", "哑铃推举"]
    if "跳" in name_blob:
        return ["反向纵跳", "垂直纵跳", "跳", "cmj"]
    return [exercise.name.lower(), (exercise.alias or "").lower()]
