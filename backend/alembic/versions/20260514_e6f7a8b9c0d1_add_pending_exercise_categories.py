"""add_pending_exercise_categories

Revision ID: e6f7a8b9c0d1
Revises: c4d5e6f7a8b9
Create Date: 2026-05-14 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORY_TABLE = "exercise_categories"
PENDING_NAME = "待定"


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_pending_categories(bind)


def downgrade() -> None:
    # Do not delete pending categories automatically; they may already be used by exercises.
    pass


def _ensure_pending_categories(bind) -> None:
    level1_items = bind.execute(
        sa.text("SELECT id, code FROM exercise_categories WHERE level = 1 ORDER BY sort_order, name_zh, id")
    ).mappings().all()
    if not _category_exists(bind, None, 1, PENDING_NAME):
        _insert_pending(bind, None, None, 1)

    level1_items = bind.execute(
        sa.text("SELECT id, code FROM exercise_categories WHERE level = 1 ORDER BY sort_order, name_zh, id")
    ).mappings().all()
    for level1 in level1_items:
        if not _category_exists(bind, level1["id"], 2, PENDING_NAME):
            _insert_pending(bind, level1["id"], level1["code"], 2)

def _category_exists(bind, parent_id: int | None, level: int, name_zh: str) -> bool:
    if parent_id is None:
        result = bind.execute(
            sa.text(
                """
                SELECT 1 FROM exercise_categories
                WHERE parent_id IS NULL AND level = :level AND name_zh = :name_zh
                LIMIT 1
                """
            ),
            {"level": level, "name_zh": name_zh},
        ).first()
        return result is not None

    result = bind.execute(
        sa.text(
            """
            SELECT 1 FROM exercise_categories
            WHERE parent_id = :parent_id AND level = :level AND name_zh = :name_zh
            LIMIT 1
            """
        ),
        {"parent_id": parent_id, "level": level, "name_zh": name_zh},
    ).first()
    return result is not None


def _insert_pending(bind, parent_id: int | None, parent_code: str | None, level: int) -> None:
    base_code = f"{parent_code}/pending" if parent_code else "pending"
    code = _unique_code(bind, base_code)
    bind.execute(
        sa.text(
            """
            INSERT INTO exercise_categories (
                parent_id, level, name_zh, name_en, code, sort_order, is_system, created_at, updated_at
            )
            VALUES (
                :parent_id, :level, :name_zh, :name_en, :code, :sort_order, :is_system, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "parent_id": parent_id,
            "level": level,
            "name_zh": PENDING_NAME,
            "name_en": "Pending",
            "code": code,
            "sort_order": 9999,
            "is_system": 1,
        },
    )


def _unique_code(bind, base_code: str) -> str:
    code = base_code
    counter = 2
    while bind.execute(sa.text("SELECT 1 FROM exercise_categories WHERE code = :code LIMIT 1"), {"code": code}).first():
        code = f"{base_code}-{counter}"
        counter += 1
    return code
