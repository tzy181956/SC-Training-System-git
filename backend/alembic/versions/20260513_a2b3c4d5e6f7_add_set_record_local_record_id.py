"""add_set_record_local_record_id

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-13 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UNIQUE_CONSTRAINT_NAME = "uq_session_item_local_record_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    set_record_columns = {column["name"] for column in inspector.get_columns("set_records")}
    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("set_records")}
    indexes = {index["name"] for index in inspector.get_indexes("set_records")}

    if "local_record_id" not in set_record_columns:
        with op.batch_alter_table("set_records", schema=None) as batch_op:
            batch_op.add_column(sa.Column("local_record_id", sa.Integer(), nullable=True))

    if UNIQUE_CONSTRAINT_NAME not in unique_constraints and UNIQUE_CONSTRAINT_NAME not in indexes:
        with op.batch_alter_table("set_records", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                UNIQUE_CONSTRAINT_NAME,
                ["session_item_id", "local_record_id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    set_record_columns = {column["name"] for column in inspector.get_columns("set_records")}
    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("set_records")}
    indexes = {index["name"] for index in inspector.get_indexes("set_records")}

    if UNIQUE_CONSTRAINT_NAME in unique_constraints:
        with op.batch_alter_table("set_records", schema=None) as batch_op:
            batch_op.drop_constraint(UNIQUE_CONSTRAINT_NAME, type_="unique")
    elif UNIQUE_CONSTRAINT_NAME in indexes:
        op.drop_index(UNIQUE_CONSTRAINT_NAME, table_name="set_records")

    if "local_record_id" in set_record_columns:
        with op.batch_alter_table("set_records", schema=None) as batch_op:
            batch_op.drop_column("local_record_id")
