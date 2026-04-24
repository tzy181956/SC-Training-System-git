from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import Exercise, ExerciseTag, Tag, TrainingPlanTemplateItem, TrainingSessionItem
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.schemas.tag import TagCreate
from app.services import backup_service, content_change_log_service, dangerous_operation_service
from app.services.exercise_library_import import _slugify

EXERCISE_FACET_KEYS = (
    "bodyRegion",
    "primaryPattern",
    "secondaryPattern",
    "direction",
    "lowerDominance",
    "limbCombination",
    "laterality",
    "powerType",
    "equipment",
    "bodyPosition",
    "usageScene",
    "trainingGoal",
    "functionType",
)


def _normalize_exercise_payload_defaults(data: dict) -> dict:
    data.setdefault("structured_tags", {})
    data.setdefault("search_keywords", [])
    return data


def _normalize_exercise_record(exercise: Exercise) -> Exercise:
    if exercise.structured_tags is None:
        exercise.structured_tags = {}
    if exercise.search_keywords is None:
        exercise.search_keywords = []
    return exercise


def _sync_english_name_fields(data: dict) -> dict:
    if "name_en" in data:
        data["alias"] = data["name_en"]
    elif "alias" in data and "name_en" not in data:
        data["name_en"] = data["alias"]
    return data


def list_tags(db: Session) -> list[Tag]:
    return db.query(Tag).order_by(Tag.category, Tag.sort_order, Tag.name).all()


def grouped_tags(db: Session) -> dict[str, list[Tag]]:
    grouped: dict[str, list[Tag]] = defaultdict(list)
    for tag in list_tags(db):
        grouped[tag.category].append(tag)
    return grouped


def create_tag(db: Session, payload: TagCreate) -> Tag:
    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def list_exercises(db: Session) -> list[Exercise]:
    items = (
        db.query(Exercise)
        .options(
            joinedload(Exercise.tags).joinedload(ExerciseTag.tag),
            joinedload(Exercise.base_category),
        )
        .order_by(Exercise.name)
        .all()
    )
    return [_normalize_exercise_record(item) for item in items]


def list_exercise_facets(db: Session) -> dict:
    items = (
        db.query(Exercise.level1_category, Exercise.level2_category, Exercise.structured_tags)
        .order_by(Exercise.name)
        .all()
    )

    level1_values: set[str] = set()
    level2_values: set[str] = set()
    level2_by_level1: dict[str, set[str]] = defaultdict(set)
    facet_values: dict[str, set[str]] = defaultdict(set)

    for level1, level2, structured_tags in items:
        level1_value = (level1 or "").strip()
        level2_value = (level2 or "").strip()
        normalized_tags = structured_tags if isinstance(structured_tags, dict) else {}

        if level1_value:
            level1_values.add(level1_value)
        if level2_value:
            level2_values.add(level2_value)
        if level1_value and level2_value:
            level2_by_level1[level1_value].add(level2_value)

        for key, values in normalized_tags.items():
            if key not in EXERCISE_FACET_KEYS or not isinstance(values, list):
                continue
            for value in values:
                normalized_value = str(value or "").strip()
                if normalized_value:
                    facet_values[key].add(normalized_value)

    return {
        "level1_options": sorted(level1_values),
        "level2_options": sorted(level2_values),
        "level2_options_by_level1": {
            key: sorted(values) for key, values in sorted(level2_by_level1.items(), key=lambda item: item[0])
        },
        "facets": {
            key: sorted(values) for key, values in sorted(facet_values.items(), key=lambda item: item[0])
        },
    }


def get_exercise(db: Session, exercise_id: int) -> Exercise:
    exercise = (
        db.query(Exercise)
        .options(
            joinedload(Exercise.tags).joinedload(ExerciseTag.tag),
            joinedload(Exercise.base_category),
        )
        .filter(Exercise.id == exercise_id)
        .first()
    )
    if not exercise:
        raise not_found("Exercise not found")
    return _normalize_exercise_record(exercise)


def create_exercise(db: Session, payload: ExerciseCreate) -> Exercise:
    data = payload.model_dump(exclude={"tag_ids"})
    _sync_english_name_fields(data)
    _normalize_exercise_payload_defaults(data)

    existing_codes = {item.code for item in db.query(Exercise).all() if item.code}
    if not data.get("code"):
        base = f"CUSTOM_{_slugify(data['name']).upper()}"
        code = base
        counter = 2
        while code in existing_codes:
            code = f"{base}_{counter}"
            counter += 1
        data["code"] = code
    if not data.get("source_type"):
        data["source_type"] = "custom_manual"

    exercise = Exercise(**data)
    db.add(exercise)
    db.flush()

    for tag_id in payload.tag_ids:
        db.add(ExerciseTag(exercise_id=exercise.id, tag_id=tag_id))

    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="exercise",
        object_id=exercise.id,
        object_label=exercise.name,
        summary=f"新建动作“{exercise.name}”",
        after_snapshot=_serialize_exercise_for_log(exercise, tag_ids=payload.tag_ids),
    )
    db.commit()
    return get_exercise(db, exercise.id)


def update_exercise(db: Session, exercise_id: int, payload: ExerciseUpdate) -> Exercise:
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise not_found("Exercise not found")

    before_tag_ids = [
        row[0]
        for row in db.query(ExerciseTag.tag_id).filter(ExerciseTag.exercise_id == exercise_id).order_by(ExerciseTag.tag_id).all()
    ]
    before_snapshot = _serialize_exercise_for_log(exercise, tag_ids=before_tag_ids)

    data = payload.model_dump(exclude_unset=True, exclude={"tag_ids"})
    _sync_english_name_fields(data)
    _normalize_exercise_payload_defaults(data)
    for key, value in data.items():
        setattr(exercise, key, value)

    if payload.tag_ids is not None:
        db.query(ExerciseTag).filter(ExerciseTag.exercise_id == exercise_id).delete()
        for tag_id in payload.tag_ids:
            db.add(ExerciseTag(exercise_id=exercise_id, tag_id=tag_id))

    db.flush()
    after_tag_ids = payload.tag_ids if payload.tag_ids is not None else before_tag_ids
    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="exercise",
        object_id=exercise.id,
        object_label=exercise.name,
        summary=f"更新动作“{exercise.name}”",
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_exercise_for_log(exercise, tag_ids=after_tag_ids),
    )
    db.commit()
    return get_exercise(db, exercise_id)


def delete_exercise(db: Session, exercise_id: int, *, actor_name: str | None = None) -> None:
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise not_found("Exercise not found")

    template_refs = db.query(TrainingPlanTemplateItem).filter(TrainingPlanTemplateItem.exercise_id == exercise_id).count()
    session_refs = db.query(TrainingSessionItem).filter(TrainingSessionItem.exercise_id == exercise_id).count()
    if template_refs or session_refs:
        raise bad_request(
            f"Exercise is referenced by {template_refs} template items and {session_refs} session items; remove those references before deleting it."
        )

    backup_result = backup_service.create_pre_dangerous_operation_backup(label=f"delete_exercise_{exercise_id}")
    db.delete(exercise)
    dangerous_operation_service.log_dangerous_operation(
        db,
        operation_key="delete_exercise",
        object_type="exercise",
        object_id=exercise_id,
        actor_name=actor_name,
        summary=f"删除动作“{exercise.name}”",
        impact_scope={
            "exercise_name": exercise.name,
            "code": exercise.code,
            "source_type": exercise.source_type,
            "level1_category": exercise.level1_category,
            "level2_category": exercise.level2_category,
            "base_movement": exercise.base_movement,
        },
        backup_path=backup_result.backup_path,
    )
    db.commit()


def attach_tag(db: Session, exercise_id: int, tag_id: int) -> Exercise:
    existing = db.query(ExerciseTag).filter(ExerciseTag.exercise_id == exercise_id, ExerciseTag.tag_id == tag_id).first()
    if not existing:
        db.add(ExerciseTag(exercise_id=exercise_id, tag_id=tag_id))
        db.commit()
    return get_exercise(db, exercise_id)


def detach_tag(db: Session, exercise_id: int, tag_id: int) -> Exercise:
    existing = db.query(ExerciseTag).filter(ExerciseTag.exercise_id == exercise_id, ExerciseTag.tag_id == tag_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    return get_exercise(db, exercise_id)


def _serialize_exercise_for_log(exercise: Exercise, *, tag_ids: list[int] | None = None) -> dict:
    return {
        "id": exercise.id,
        "name": exercise.name,
        "alias": exercise.alias,
        "code": exercise.code,
        "source_type": exercise.source_type,
        "name_en": exercise.name_en,
        "level1_category": exercise.level1_category,
        "level2_category": exercise.level2_category,
        "base_movement": exercise.base_movement,
        "category_path": exercise.category_path,
        "structured_tags": exercise.structured_tags or {},
        "search_keywords": exercise.search_keywords or [],
        "tag_text": exercise.tag_text,
        "base_category_id": exercise.base_category_id,
        "description": exercise.description,
        "video_url": exercise.video_url,
        "video_path": exercise.video_path,
        "coaching_points": exercise.coaching_points,
        "common_errors": exercise.common_errors,
        "notes": exercise.notes,
        "default_increment": exercise.default_increment,
        "is_main_lift_candidate": exercise.is_main_lift_candidate,
        "tag_ids": sorted(tag_ids or []),
    }
