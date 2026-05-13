"""add_template_visibility_owner

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-05-13 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TEMPLATE_TABLE = "training_plan_templates"
VISIBILITY_INDEX = "ix_training_plan_templates_visibility"
OWNER_INDEX = "ix_training_plan_templates_owner_user_id"
SOURCE_INDEX = "ix_training_plan_templates_source_template_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(TEMPLATE_TABLE)}
    indexes = {index["name"] for index in inspector.get_indexes(TEMPLATE_TABLE)}

    with op.batch_alter_table(TEMPLATE_TABLE, schema=None) as batch_op:
        if "visibility" not in columns:
            batch_op.add_column(
                sa.Column(
                    "visibility",
                    sa.String(length=20),
                    nullable=False,
                    server_default="private",
                )
            )
        if "owner_user_id" not in columns:
            batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        if "created_by_user_id" not in columns:
            batch_op.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        if "source_template_id" not in columns:
            batch_op.add_column(sa.Column("source_template_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE training_plan_templates
            SET visibility = 'public',
                owner_user_id = NULL,
                created_by_user_id = NULL,
                source_template_id = NULL
            """
        )
    )

    if VISIBILITY_INDEX not in indexes:
        op.create_index(VISIBILITY_INDEX, TEMPLATE_TABLE, ["visibility"])
    if OWNER_INDEX not in indexes:
        op.create_index(OWNER_INDEX, TEMPLATE_TABLE, ["owner_user_id"])
    if SOURCE_INDEX not in indexes:
        op.create_index(SOURCE_INDEX, TEMPLATE_TABLE, ["source_template_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(TEMPLATE_TABLE)}
    indexes = {index["name"] for index in inspector.get_indexes(TEMPLATE_TABLE)}

    for index_name in (SOURCE_INDEX, OWNER_INDEX, VISIBILITY_INDEX):
        if index_name in indexes:
            op.drop_index(index_name, table_name=TEMPLATE_TABLE)

    with op.batch_alter_table(TEMPLATE_TABLE, schema=None) as batch_op:
        if "source_template_id" in columns:
            batch_op.drop_column("source_template_id")
        if "created_by_user_id" in columns:
            batch_op.drop_column("created_by_user_id")
        if "owner_user_id" in columns:
            batch_op.drop_column("owner_user_id")
        if "visibility" in columns:
            batch_op.drop_column("visibility")
