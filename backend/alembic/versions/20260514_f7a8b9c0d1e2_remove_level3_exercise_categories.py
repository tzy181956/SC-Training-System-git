"""remove_level3_exercise_categories

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-14 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EXERCISE_TABLE = "exercises"
CATEGORY_TABLE = "exercise_categories"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    exercise_columns = {column["name"] for column in inspector.get_columns(EXERCISE_TABLE)}

    if "category_path" in exercise_columns:
        op.execute(
            sa.text(
                """
                UPDATE exercises
                SET category_path = TRIM(
                    COALESCE(level1_category, '') ||
                    CASE
                        WHEN level1_category IS NOT NULL AND TRIM(level1_category) != ''
                         AND level2_category IS NOT NULL AND TRIM(level2_category) != ''
                        THEN ' / '
                        ELSE ''
                    END ||
                    COALESCE(level2_category, '')
                )
                WHERE base_movement IS NOT NULL OR base_category_id IS NOT NULL
                """
            )
        )

    with op.batch_alter_table(EXERCISE_TABLE, schema=None) as batch_op:
        if "base_category_id" in exercise_columns:
            batch_op.drop_column("base_category_id")
        if "base_movement" in exercise_columns:
            batch_op.drop_column("base_movement")

    op.execute(sa.text("DELETE FROM exercise_categories WHERE level = 3"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    exercise_columns = {column["name"] for column in inspector.get_columns(EXERCISE_TABLE)}

    with op.batch_alter_table(EXERCISE_TABLE, schema=None) as batch_op:
        if "base_movement" not in exercise_columns:
            batch_op.add_column(sa.Column("base_movement", sa.String(length=160), nullable=True))
        if "base_category_id" not in exercise_columns:
            batch_op.add_column(sa.Column("base_category_id", sa.Integer(), nullable=True))
