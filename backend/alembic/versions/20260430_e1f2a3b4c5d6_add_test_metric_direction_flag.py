"""add_test_metric_direction_flag

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-30 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.test_definition_defaults import DEFAULT_LOWER_BETTER_TEST_METRIC_CODES


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "test_metric_definitions" not in existing_tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("test_metric_definitions")}
    if "is_lower_better" not in existing_columns:
        with op.batch_alter_table("test_metric_definitions") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_lower_better",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )

    if DEFAULT_LOWER_BETTER_TEST_METRIC_CODES:
        params = {f"metric_code_{index}": code for index, code in enumerate(DEFAULT_LOWER_BETTER_TEST_METRIC_CODES)}
        placeholders = ", ".join(f":metric_code_{index}" for index in range(len(DEFAULT_LOWER_BETTER_TEST_METRIC_CODES)))
        bind.execute(
            sa.text(
                f"""
                UPDATE test_metric_definitions
                SET is_lower_better = 1
                WHERE code IN ({placeholders})
                """
            ),
            params,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "test_metric_definitions" not in existing_tables:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("test_metric_definitions")}
    if "is_lower_better" in existing_columns:
        with op.batch_alter_table("test_metric_definitions") as batch_op:
            batch_op.drop_column("is_lower_better")
