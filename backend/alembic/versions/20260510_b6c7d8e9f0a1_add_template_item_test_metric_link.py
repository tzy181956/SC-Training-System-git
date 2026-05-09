"""add_template_item_test_metric_link

Revision ID: b6c7d8e9f0a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-10 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "training_plan_template_items"
COLUMN_NAME = "initial_load_test_metric_definition_id"
INDEX_NAME = "ix_training_plan_template_items_initial_load_test_metric_definition_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    is_sqlite = bind.dialect.name == "sqlite"

    if COLUMN_NAME not in existing_columns:
        column = sa.Column(COLUMN_NAME, sa.Integer(), nullable=True) if is_sqlite else sa.Column(
            COLUMN_NAME,
            sa.Integer(),
            sa.ForeignKey("test_metric_definitions.id"),
            nullable=True,
        )
        op.add_column(TABLE_NAME, column)

    op.execute(
        f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} "
        f"ON {TABLE_NAME}({COLUMN_NAME})"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}

    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    if COLUMN_NAME in existing_columns:
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.drop_column(COLUMN_NAME)
