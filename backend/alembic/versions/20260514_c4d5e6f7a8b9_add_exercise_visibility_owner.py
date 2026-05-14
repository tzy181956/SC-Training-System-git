"""add_exercise_visibility_owner

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-14 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EXERCISE_TABLE = "exercises"
VISIBILITY_INDEX = "ix_exercises_visibility"
OWNER_INDEX = "ix_exercises_owner_user_id"
CREATED_BY_INDEX = "ix_exercises_created_by_user_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(EXERCISE_TABLE)}
    indexes = {index["name"] for index in inspector.get_indexes(EXERCISE_TABLE)}

    with op.batch_alter_table(EXERCISE_TABLE, schema=None) as batch_op:
        if "visibility" not in columns:
            batch_op.add_column(
                sa.Column(
                    "visibility",
                    sa.String(length=20),
                    nullable=False,
                    server_default="public",
                )
            )
        if "owner_user_id" not in columns:
            batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        if "created_by_user_id" not in columns:
            batch_op.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE exercises
            SET visibility = 'public',
                owner_user_id = NULL,
                created_by_user_id = NULL
            """
        )
    )

    if VISIBILITY_INDEX not in indexes:
        op.create_index(VISIBILITY_INDEX, EXERCISE_TABLE, ["visibility"])
    if OWNER_INDEX not in indexes:
        op.create_index(OWNER_INDEX, EXERCISE_TABLE, ["owner_user_id"])
    if CREATED_BY_INDEX not in indexes:
        op.create_index(CREATED_BY_INDEX, EXERCISE_TABLE, ["created_by_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(EXERCISE_TABLE)}
    indexes = {index["name"] for index in inspector.get_indexes(EXERCISE_TABLE)}

    for index_name in (CREATED_BY_INDEX, OWNER_INDEX, VISIBILITY_INDEX):
        if index_name in indexes:
            op.drop_index(index_name, table_name=EXERCISE_TABLE)

    with op.batch_alter_table(EXERCISE_TABLE, schema=None) as batch_op:
        if "created_by_user_id" in columns:
            batch_op.drop_column("created_by_user_id")
        if "owner_user_id" in columns:
            batch_op.drop_column("owner_user_id")
        if "visibility" in columns:
            batch_op.drop_column("visibility")
