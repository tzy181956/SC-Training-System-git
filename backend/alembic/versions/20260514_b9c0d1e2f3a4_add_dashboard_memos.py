"""add_dashboard_memos

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-05-14 19:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "dashboard_memos"
USER_INDEX = "ix_dashboard_memos_user_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if TABLE_NAME not in tables:
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("source", sa.String(length=30), nullable=False, server_default="dashboard"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_dashboard_memos_user_id"),
        )
        op.create_index(USER_INDEX, TABLE_NAME, ["user_id"], unique=True)
        return

    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if USER_INDEX not in indexes:
        op.create_index(USER_INDEX, TABLE_NAME, ["user_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if TABLE_NAME not in tables:
        return

    indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}
    if USER_INDEX in indexes:
        op.drop_index(USER_INDEX, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
