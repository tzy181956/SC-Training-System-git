"""add_auth_event_logs

Revision ID: f8a9b0c1d2e3
Revises: e2f3a4b5c6d7
Create Date: 2026-05-14 21:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "auth_event_logs"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME in set(inspector.get_table_names()):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("failure_reason", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_event_logs_id"), TABLE_NAME, ["id"], unique=False)
    op.create_index(op.f("ix_auth_event_logs_username"), TABLE_NAME, ["username"], unique=False)
    op.create_index(op.f("ix_auth_event_logs_user_id"), TABLE_NAME, ["user_id"], unique=False)
    op.create_index(op.f("ix_auth_event_logs_success"), TABLE_NAME, ["success"], unique=False)
    op.create_index(op.f("ix_auth_event_logs_failure_reason"), TABLE_NAME, ["failure_reason"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in set(inspector.get_table_names()):
        return

    op.drop_index(op.f("ix_auth_event_logs_failure_reason"), table_name=TABLE_NAME)
    op.drop_index(op.f("ix_auth_event_logs_success"), table_name=TABLE_NAME)
    op.drop_index(op.f("ix_auth_event_logs_user_id"), table_name=TABLE_NAME)
    op.drop_index(op.f("ix_auth_event_logs_username"), table_name=TABLE_NAME)
    op.drop_index(op.f("ix_auth_event_logs_id"), table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
