from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from sqlalchemy import delete, func, inspect, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    DangerousOperationLog,
    Exercise,
    ExerciseTag,
    TrainingPlanTemplateItem,
    TrainingSessionItem,
)
from app.services import backup_service, dangerous_operation_service


VIBRATION_EQUIPMENT_VALUE = "振动器材"
CONFIRMATION_PHRASE = "DELETE_VIBRATION_EQUIPMENT_EXERCISES"
OPERATION_KEY = "delete_vibration_equipment_exercises"
SAMPLE_LIMIT = 20
DELETE_CHUNK_SIZE = 500


@dataclass(slots=True)
class ExerciseSample:
    id: int
    name: str
    code: str | None
    category_path: str | None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "category_path": self.category_path,
        }


@dataclass(slots=True)
class CleanupPlan:
    target_ids: list[int]
    sample: list[ExerciseSample]
    reference_counts: dict[str, int]

    @property
    def delete_count(self) -> int:
        return len(self.target_ids)

    @property
    def blocking_reference_counts(self) -> dict[str, int]:
        return {
            table_name: count
            for table_name, count in self.reference_counts.items()
            if table_name in {"training_plan_template_items", "training_session_items"} and count > 0
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete exercises whose structured equipment tag is vibration equipment."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print target counts, samples, and reference checks. No data is changed.",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help=f"Required fixed confirmation phrase for execution: {CONFIRMATION_PHRASE}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with SessionLocal() as db:
        plan = build_cleanup_plan(db)
        print_plan(plan, dry_run=args.dry_run)

        if args.dry_run:
            return

        if args.confirm.strip() != CONFIRMATION_PHRASE:
            raise SystemExit(
                "Confirmation mismatch. No data was changed. "
                f"Run with --dry-run first, then execute with --confirm {CONFIRMATION_PHRASE}"
            )

        if plan.blocking_reference_counts:
            log_blocked_attempt(db, plan)
            db.commit()
            raise SystemExit("Referenced exercises were found. No data was changed.")

        if plan.delete_count == 0:
            dangerous_operation_service.log_dangerous_operation(
                db,
                operation_key=OPERATION_KEY,
                object_type="exercise_library",
                actor_name="系统脚本",
                source="script",
                status="completed",
                confirmation_phrase=CONFIRMATION_PHRASE,
                summary="未发现带振动器材标签的动作，无需删除",
                impact_scope=build_impact_scope(plan),
            )
            db.commit()
            print("[CLEANUP] No matching exercises found. Nothing was deleted.")
            return

        backup_result = backup_service.create_pre_dangerous_operation_backup(
            label="delete_vibration_equipment_exercises"
        )
        if backup_result.backup_path:
            print(f"[BACKUP] Backup created before cleanup: {backup_result.backup_path}")

        try:
            deleted_tags = delete_exercise_tags(db, plan.target_ids)
            deleted_exercises = delete_exercises(db, plan.target_ids)
            dangerous_operation_service.log_dangerous_operation(
                db,
                operation_key=OPERATION_KEY,
                object_type="exercise_library",
                actor_name="系统脚本",
                source="script",
                status="completed",
                confirmation_phrase=CONFIRMATION_PHRASE,
                summary=f"批量删除 {deleted_exercises} 个带振动器材标签的动作",
                impact_scope={
                    **build_impact_scope(plan),
                    "deleted_exercise_tags": deleted_tags,
                    "deleted_exercises": deleted_exercises,
                },
                backup_path=backup_result.backup_path,
                extra_data={"rollback_note": "如需恢复，请使用本次危险操作前备份恢复数据库。"},
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            dangerous_operation_service.log_dangerous_operation(
                db,
                operation_key=OPERATION_KEY,
                object_type="exercise_library",
                actor_name="系统脚本",
                source="script",
                status="failed",
                confirmation_phrase=CONFIRMATION_PHRASE,
                summary="批量删除带振动器材标签的动作失败，已回滚数据库事务",
                impact_scope=build_impact_scope(plan),
                backup_path=backup_result.backup_path,
                extra_data={"error": str(exc)},
            )
            db.commit()
            raise

    print(f"[CLEANUP] Deleted {plan.delete_count} vibration equipment exercises.")


def build_cleanup_plan(db: Session) -> CleanupPlan:
    table_names = set(inspect(db.bind).get_table_names())
    if "exercises" not in table_names:
        return CleanupPlan(target_ids=[], sample=[], reference_counts={})

    exercises = db.scalars(select(Exercise).order_by(Exercise.id)).all()
    targets = [exercise for exercise in exercises if has_vibration_equipment(exercise.structured_tags)]
    target_ids = [int(exercise.id) for exercise in targets]
    sample = [
        ExerciseSample(
            id=int(exercise.id),
            name=exercise.name,
            code=exercise.code,
            category_path=exercise.category_path,
        )
        for exercise in targets[:SAMPLE_LIMIT]
    ]
    return CleanupPlan(
        target_ids=target_ids,
        sample=sample,
        reference_counts=count_references(db, table_names, target_ids),
    )


def has_vibration_equipment(structured_tags: object) -> bool:
    tags = load_json_object(structured_tags)
    equipment = tags.get("equipment")
    if not isinstance(equipment, list):
        return False
    return any(str(value or "").strip() == VIBRATION_EQUIPMENT_VALUE for value in equipment)


def load_json_object(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def count_references(db: Session, table_names: set[str], target_ids: list[int]) -> dict[str, int]:
    if not target_ids:
        return {
            "exercise_tags": 0 if "exercise_tags" in table_names else -1,
            "training_plan_template_items": 0 if "training_plan_template_items" in table_names else -1,
            "training_session_items": 0 if "training_session_items" in table_names else -1,
        }

    return {
        "exercise_tags": count_table_refs(db, ExerciseTag.exercise_id, target_ids)
        if "exercise_tags" in table_names
        else -1,
        "training_plan_template_items": count_table_refs(db, TrainingPlanTemplateItem.exercise_id, target_ids)
        if "training_plan_template_items" in table_names
        else -1,
        "training_session_items": count_table_refs(db, TrainingSessionItem.exercise_id, target_ids)
        if "training_session_items" in table_names
        else -1,
    }


def count_table_refs(db: Session, column, target_ids: list[int]) -> int:
    total = 0
    for chunk in chunks(target_ids, DELETE_CHUNK_SIZE):
        total += int(db.scalar(select(func.count()).where(column.in_(chunk))) or 0)
    return total


def delete_exercise_tags(db: Session, target_ids: list[int]) -> int:
    deleted_count = 0
    for chunk in chunks(target_ids, DELETE_CHUNK_SIZE):
        result = db.execute(delete(ExerciseTag).where(ExerciseTag.exercise_id.in_(chunk)))
        deleted_count += int(result.rowcount or 0)
    return deleted_count


def delete_exercises(db: Session, target_ids: list[int]) -> int:
    deleted_count = 0
    for chunk in chunks(target_ids, DELETE_CHUNK_SIZE):
        result = db.execute(delete(Exercise).where(Exercise.id.in_(chunk)))
        deleted_count += int(result.rowcount or 0)
    return deleted_count


def chunks(values: list[int], chunk_size: int) -> Iterable[list[int]]:
    for index in range(0, len(values), chunk_size):
        yield values[index:index + chunk_size]


def print_plan(plan: CleanupPlan, *, dry_run: bool) -> None:
    prefix = "[DRY-RUN]" if dry_run else "[PLAN]"
    print(f"{prefix} Target equipment tag: {VIBRATION_EQUIPMENT_VALUE}")
    print(f"{prefix} Exercises that would be deleted: {plan.delete_count}")
    print(f"{prefix} Reference check:")
    for table_name, count in plan.reference_counts.items():
        display_count = "table missing" if count < 0 else str(count)
        marker = " BLOCKING" if table_name in plan.blocking_reference_counts else ""
        print(f"  - {table_name}: {display_count}{marker}")

    print(f"{prefix} Sample targets:")
    if not plan.sample:
        print("  - none")
        return
    for sample in plan.sample:
        code = sample.code or "-"
        category = sample.category_path or "-"
        print(f"  - id={sample.id}, name={sample.name}, code={code}, category={category}")


def build_impact_scope(plan: CleanupPlan) -> dict:
    return {
        "equipment_tag": VIBRATION_EQUIPMENT_VALUE,
        "target_count": plan.delete_count,
        "reference_check": plan.reference_counts,
        "sample": [sample.as_dict() for sample in plan.sample],
    }


def log_blocked_attempt(db: Session, plan: CleanupPlan) -> DangerousOperationLog:
    return dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key=OPERATION_KEY,
        object_type="exercise_library",
        actor_name="系统脚本",
        source="script",
        status="failed",
        confirmation_phrase=CONFIRMATION_PHRASE,
        summary="带振动器材标签的动作仍被训练模板或历史训练课引用，已拒绝删除",
        impact_scope=build_impact_scope(plan),
        extra_data={"blocking_reference_counts": plan.blocking_reference_counts},
    )


if __name__ == "__main__":
    main()
