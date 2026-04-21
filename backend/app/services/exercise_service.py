from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.models import Exercise, ExerciseTag, Tag, TrainingPlanTemplateItem, TrainingSessionItem
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.schemas.tag import TagCreate
from app.services.exercise_library_import import _slugify


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
    """Keep alias as a compatibility mirror of name_en, but do not treat it as the primary field."""
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
    db.commit()
    return get_exercise(db, exercise.id)


def update_exercise(db: Session, exercise_id: int, payload: ExerciseUpdate) -> Exercise:
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise not_found("Exercise not found")
    data = payload.model_dump(exclude_unset=True, exclude={"tag_ids"})
    _sync_english_name_fields(data)
    _normalize_exercise_payload_defaults(data)
    for key, value in data.items():
        setattr(exercise, key, value)
    if payload.tag_ids is not None:
        db.query(ExerciseTag).filter(ExerciseTag.exercise_id == exercise_id).delete()
        for tag_id in payload.tag_ids:
            db.add(ExerciseTag(exercise_id=exercise_id, tag_id=tag_id))
    db.commit()
    return get_exercise(db, exercise_id)


def delete_exercise(db: Session, exercise_id: int) -> None:
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise not_found("Exercise not found")

    template_refs = db.query(TrainingPlanTemplateItem).filter(TrainingPlanTemplateItem.exercise_id == exercise_id).count()
    session_refs = db.query(TrainingSessionItem).filter(TrainingSessionItem.exercise_id == exercise_id).count()
    if template_refs or session_refs:
        raise bad_request(
            f"Exercise is referenced by {template_refs} template items and {session_refs} session items; remove those references before deleting it."
        )

    db.delete(exercise)
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
