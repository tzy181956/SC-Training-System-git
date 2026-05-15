from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Exercise, ExerciseTag, Tag
from app.services import backup_service, dangerous_operation_service


TARGET_TAG_KEY = "bodyPosition"
TARGET_TAG_LABEL = "体位"
TARGET_TAG_VALUE = "其他"
TARGET_TAG_CATEGORIES = {"bodyPosition", "体位", "body_position"}
CONFIRMATION_PHRASE = "REMOVE_OTHER_BODY_POSITION_TAG"
OPERATION_KEY = "remove_other_body_position_tag"
SAMPLE_LIMIT = 20

TAG_LABELS = {
    "functionType": "功能类型",
    "trainingGoal": "训练目标",
    "bodyRegion": "动作区域",
    "subBodyPart": "细分部位",
    "primaryPattern": "主动作模式",
    "secondaryPattern": "动作模式补充",
    "direction": "方向属性",
    "lowerDominance": "下肢主导",
    "limbCombination": "肢体组合",
    "laterality": "侧别",
    "powerType": "动力属性",
    "equipment": "器械",
    "bodyPosition": "体位",
    "usageScene": "应用场景",
    "fmsItem": "FMS项目",
    "fmsPhase": "FMS阶段",
    "fmsLevel": "FMS等级",
}


@dataclass(slots=True)
class ExerciseSample:
    id: int
    name: str
    code: str | None
    category_path: str | None
    body_position: list[str]

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "category_path": self.category_path,
            "body_position": self.body_position,
        }


@dataclass(slots=True)
class CleanupPlan:
    exercise_ids: list[int]
    tag_ids: list[int]
    sample: list[ExerciseSample]

    @property
    def exercise_count(self) -> int:
        return len(self.exercise_ids)

    @property
    def tag_count(self) -> int:
        return len(self.tag_ids)

    @property
    def has_changes(self) -> bool:
        return bool(self.exercise_ids or self.tag_ids)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove the body position tag value '其他' from exercises and delete the matching tag row."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print target counts and samples. No data is changed.",
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

        if not plan.has_changes:
            dangerous_operation_service.log_dangerous_operation(
                db,
                operation_key=OPERATION_KEY,
                object_type="exercise_library",
                actor_name="系统脚本",
                source="script",
                status="completed",
                confirmation_phrase=CONFIRMATION_PHRASE,
                summary="未发现体位标签“其他”，无需清理",
                impact_scope=build_impact_scope(plan),
            )
            db.commit()
            print("[CLEANUP] No matching tag value found. Nothing was changed.")
            return

        backup_result = backup_service.create_pre_dangerous_operation_backup(
            label="remove_other_body_position_tag"
        )
        if backup_result.backup_path:
            print(f"[BACKUP] Backup created before cleanup: {backup_result.backup_path}")

        try:
            updated_exercises = clean_exercises(db, plan.exercise_ids)
            deleted_exercise_tags = delete_tag_links(db, plan.tag_ids)
            deleted_tag_rows = delete_tags(db, plan.tag_ids)
            dangerous_operation_service.log_dangerous_operation(
                db,
                operation_key=OPERATION_KEY,
                object_type="exercise_library",
                actor_name="系统脚本",
                source="script",
                status="completed",
                confirmation_phrase=CONFIRMATION_PHRASE,
                summary=f"删除体位标签“其他”，并从 {updated_exercises} 个动作中取消该标签",
                impact_scope={
                    **build_impact_scope(plan),
                    "updated_exercises": updated_exercises,
                    "deleted_exercise_tag_links": deleted_exercise_tags,
                    "deleted_tag_rows": deleted_tag_rows,
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
                summary="删除体位标签“其他”失败，已回滚数据库事务",
                impact_scope=build_impact_scope(plan),
                backup_path=backup_result.backup_path,
                extra_data={"error": str(exc)},
            )
            db.commit()
            raise

    print(f"[CLEANUP] Removed {TARGET_TAG_LABEL}={TARGET_TAG_VALUE} from {plan.exercise_count} exercises.")


def build_cleanup_plan(db: Session) -> CleanupPlan:
    exercises = db.scalars(select(Exercise).order_by(Exercise.id)).all()
    matching_exercises = [exercise for exercise in exercises if has_target_tag(exercise.structured_tags)]
    tag_rows = db.scalars(
        select(Tag).where(
            Tag.name == TARGET_TAG_VALUE,
            Tag.category.in_(TARGET_TAG_CATEGORIES),
        )
    ).all()

    return CleanupPlan(
        exercise_ids=[int(exercise.id) for exercise in matching_exercises],
        tag_ids=[int(tag.id) for tag in tag_rows],
        sample=[
            ExerciseSample(
                id=int(exercise.id),
                name=exercise.name,
                code=exercise.code,
                category_path=exercise.category_path,
                body_position=list(load_json_object(exercise.structured_tags).get(TARGET_TAG_KEY) or []),
            )
            for exercise in matching_exercises[:SAMPLE_LIMIT]
        ],
    )


def has_target_tag(structured_tags: object) -> bool:
    tags = load_json_object(structured_tags)
    values = tags.get(TARGET_TAG_KEY)
    if not isinstance(values, list):
        return False
    return any(str(value or "").strip() == TARGET_TAG_VALUE for value in values)


def clean_exercises(db: Session, exercise_ids: list[int]) -> int:
    if not exercise_ids:
        return 0

    updated = 0
    exercises = db.scalars(select(Exercise).where(Exercise.id.in_(exercise_ids)).order_by(Exercise.id)).all()
    for exercise in exercises:
        cleaned_tags, changed = remove_target_tag(load_json_object(exercise.structured_tags))
        if not changed:
            continue
        tag_text = build_tag_text(cleaned_tags)
        search_keywords = clean_search_keywords(exercise.search_keywords, tag_text)
        exercise.structured_tags = cleaned_tags
        exercise.tag_text = tag_text or None
        exercise.search_keywords = search_keywords
        updated += 1
    return updated


def remove_target_tag(tags: dict) -> tuple[dict[str, list[str]], bool]:
    cleaned: dict[str, list[str]] = {}
    changed = False

    for key, raw_values in tags.items():
        if not isinstance(raw_values, list):
            cleaned[key] = []
            changed = True
            continue

        values: list[str] = []
        seen: set[str] = set()
        for raw_value in raw_values:
            value = str(raw_value or "").strip()
            if not value:
                changed = True
                continue
            if key == TARGET_TAG_KEY and value == TARGET_TAG_VALUE:
                changed = True
                continue
            if value in seen:
                changed = True
                continue
            seen.add(value)
            values.append(value)
        cleaned[key] = values

    return cleaned, changed


def clean_search_keywords(value: object, tag_text: str) -> list[str]:
    keywords = load_json_list(value)
    cleaned: list[str] = []
    seen: set[str] = set()

    for raw_keyword in keywords:
        keyword = str(raw_keyword or "").strip()
        if not keyword:
            continue
        if should_remove_keyword(keyword):
            continue
        if keyword in seen:
            continue
        seen.add(keyword)
        cleaned.append(keyword)

    if tag_text and tag_text not in seen:
        cleaned.append(tag_text)
    return cleaned


def should_remove_keyword(keyword: str) -> bool:
    return keyword == TARGET_TAG_VALUE or f"{TARGET_TAG_LABEL}:{TARGET_TAG_VALUE}" in keyword


def delete_tag_links(db: Session, tag_ids: list[int]) -> int:
    if not tag_ids:
        return 0
    result = db.execute(delete(ExerciseTag).where(ExerciseTag.tag_id.in_(tag_ids)))
    return int(result.rowcount or 0)


def delete_tags(db: Session, tag_ids: list[int]) -> int:
    if not tag_ids:
        return 0
    result = db.execute(delete(Tag).where(Tag.id.in_(tag_ids)))
    return int(result.rowcount or 0)


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


def load_json_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def build_tag_text(tags: dict[str, list[str]]) -> str:
    parts = [
        f"{TAG_LABELS[key]}:{'|'.join(values)}"
        for key, values in tags.items()
        if key in TAG_LABELS and values
    ]
    return "；".join(parts)


def print_plan(plan: CleanupPlan, *, dry_run: bool) -> None:
    prefix = "[DRY-RUN]" if dry_run else "[PLAN]"
    print(f"{prefix} Target tag: {TARGET_TAG_LABEL}={TARGET_TAG_VALUE}")
    print(f"{prefix} Matching exercises: {plan.exercise_count}")
    print(f"{prefix} Matching tag rows: {plan.tag_count}")
    print(f"{prefix} Sample exercises:")
    if not plan.sample:
        print("  - none")
        return
    for sample in plan.sample:
        code = sample.code or "-"
        category = sample.category_path or "-"
        print(
            f"  - id={sample.id}, name={sample.name}, code={code}, "
            f"category={category}, bodyPosition={sample.body_position}"
        )


def build_impact_scope(plan: CleanupPlan) -> dict:
    return {
        "target_tag_key": TARGET_TAG_KEY,
        "target_tag_label": TARGET_TAG_LABEL,
        "target_tag_value": TARGET_TAG_VALUE,
        "matching_exercises": plan.exercise_count,
        "matching_tag_rows": plan.tag_count,
        "sample": [sample.as_dict() for sample in plan.sample],
    }


if __name__ == "__main__":
    main()
