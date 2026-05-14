"""remove_not_applicable_exercise_tags

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-14 16:20:00.000000

"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NOT_APPLICABLE_VALUE = "不适用"
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


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("exercises")}
    if not {"structured_tags", "tag_text", "search_keywords"}.issubset(columns):
        return

    rows = bind.execute(
        sa.text("SELECT id, structured_tags, tag_text, search_keywords FROM exercises")
    ).mappings().all()

    for row in rows:
        original_tags = _load_json_object(row["structured_tags"])
        cleaned_tags, changed = _clean_structured_tags(original_tags)
        tag_text = _build_tag_text(cleaned_tags)
        search_keywords, search_changed = _clean_search_keywords(row["search_keywords"], tag_text)

        if changed or search_changed or (row["tag_text"] or "") != tag_text:
            bind.execute(
                sa.text(
                    """
                    UPDATE exercises
                    SET structured_tags = :structured_tags,
                        tag_text = :tag_text,
                        search_keywords = :search_keywords
                    WHERE id = :exercise_id
                    """
                ),
                {
                    "exercise_id": row["id"],
                    "structured_tags": json.dumps(cleaned_tags, ensure_ascii=False),
                    "tag_text": tag_text or None,
                    "search_keywords": json.dumps(search_keywords, ensure_ascii=False),
                },
            )


def downgrade() -> None:
    # The removed value meant "no tag selected"; it cannot be restored reliably.
    pass


def _load_json_object(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _clean_structured_tags(tags: dict) -> tuple[dict[str, list[str]], bool]:
    cleaned: dict[str, list[str]] = {}
    changed = False

    for key, raw_values in tags.items():
        if not isinstance(raw_values, list):
            changed = True
            continue

        values: list[str] = []
        seen: set[str] = set()
        for raw_value in raw_values:
            value = str(raw_value or "").strip()
            if not value:
                changed = True
                continue
            if value == NOT_APPLICABLE_VALUE:
                changed = True
                continue
            if value in seen:
                changed = True
                continue
            seen.add(value)
            values.append(value)
        cleaned[key] = values

    return cleaned, changed


def _build_tag_text(tags: dict[str, list[str]]) -> str:
    parts = [
        f"{TAG_LABELS[key]}:{'|'.join(values)}"
        for key, values in tags.items()
        if key in TAG_LABELS and values
    ]
    return "；".join(parts)


def _clean_search_keywords(value: object, tag_text: str) -> tuple[list[str], bool]:
    keywords = _load_json_list(value)
    cleaned: list[str] = []
    seen: set[str] = set()
    changed = False

    for raw_keyword in keywords:
        keyword = str(raw_keyword or "").strip()
        if not keyword:
            changed = True
            continue
        if NOT_APPLICABLE_VALUE in keyword:
            changed = True
            continue
        if keyword in seen:
            changed = True
            continue
        seen.add(keyword)
        cleaned.append(keyword)

    if tag_text and tag_text not in seen:
        cleaned.append(tag_text)
        changed = True

    if len(cleaned) != len(keywords):
        changed = True

    return cleaned, changed


def _load_json_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
