from collections import defaultdict

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import not_found
from app.models import Exercise, ExerciseTag, Tag
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate
from app.schemas.tag import TagCreate


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
    items = db.query(Exercise).options(joinedload(Exercise.tags).joinedload(ExerciseTag.tag)).order_by(Exercise.name).all()
    return items


def get_exercise(db: Session, exercise_id: int) -> Exercise:
    exercise = (
        db.query(Exercise)
        .options(joinedload(Exercise.tags).joinedload(ExerciseTag.tag))
        .filter(Exercise.id == exercise_id)
        .first()
    )
    if not exercise:
        raise not_found("Exercise not found")
    return exercise


def create_exercise(db: Session, payload: ExerciseCreate) -> Exercise:
    exercise = Exercise(**payload.model_dump(exclude={"tag_ids"}))
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
    for key, value in payload.model_dump(exclude_unset=True, exclude={"tag_ids"}).items():
        setattr(exercise, key, value)
    if payload.tag_ids is not None:
        db.query(ExerciseTag).filter(ExerciseTag.exercise_id == exercise_id).delete()
        for tag_id in payload.tag_ids:
            db.add(ExerciseTag(exercise_id=exercise_id, tag_id=tag_id))
    db.commit()
    return get_exercise(db, exercise_id)


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
