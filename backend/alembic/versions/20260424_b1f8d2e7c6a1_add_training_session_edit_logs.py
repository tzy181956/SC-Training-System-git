"""add_training_session_edit_logs

Revision ID: b1f8d2e7c6a1
Revises: 9d1b2c3a4e5f
Create Date: 2026-04-24 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1f8d2e7c6a1"
down_revision: Union[str, None] = "9d1b2c3a4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "training_session_edit_logs" not in set(inspector.get_table_names()):
        op.create_table(
            "training_session_edit_logs",
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("session_item_id", sa.Integer(), nullable=True),
            sa.Column("set_record_id", sa.Integer(), nullable=True),
            sa.Column("action_type", sa.String(length=30), nullable=False),
            sa.Column("actor_name", sa.String(length=120), nullable=False),
            sa.Column("object_type", sa.String(length=30), nullable=False),
            sa.Column("object_id", sa.Integer(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("before_snapshot", sa.JSON(), nullable=True),
            sa.Column("after_snapshot", sa.JSON(), nullable=True),
            sa.Column("edited_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
            sa.ForeignKeyConstraint(["session_item_id"], ["training_session_items.id"]),
            sa.ForeignKeyConstraint(["set_record_id"], ["set_records.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("training_session_edit_logs")
    }
    with op.batch_alter_table("training_session_edit_logs", schema=None) as batch_op:
        if batch_op.f("ix_training_session_edit_logs_action_type") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_training_session_edit_logs_action_type"), ["action_type"], unique=False)
        if batch_op.f("ix_training_session_edit_logs_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_training_session_edit_logs_id"), ["id"], unique=False)
        if batch_op.f("ix_training_session_edit_logs_session_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_training_session_edit_logs_session_id"), ["session_id"], unique=False)
        if batch_op.f("ix_training_session_edit_logs_session_item_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_training_session_edit_logs_session_item_id"), ["session_item_id"], unique=False)
        if batch_op.f("ix_training_session_edit_logs_set_record_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_training_session_edit_logs_set_record_id"), ["set_record_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "training_session_edit_logs" not in inspector.get_table_names():
        return

    existing_indexes = {
        index["name"] for index in inspector.get_indexes("training_session_edit_logs")
    }
    with op.batch_alter_table("training_session_edit_logs", schema=None) as batch_op:
        if batch_op.f("ix_training_session_edit_logs_set_record_id") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_training_session_edit_logs_set_record_id"))
        if batch_op.f("ix_training_session_edit_logs_session_item_id") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_training_session_edit_logs_session_item_id"))
        if batch_op.f("ix_training_session_edit_logs_session_id") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_training_session_edit_logs_session_id"))
        if batch_op.f("ix_training_session_edit_logs_id") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_training_session_edit_logs_id"))
        if batch_op.f("ix_training_session_edit_logs_action_type") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_training_session_edit_logs_action_type"))

    op.drop_table("training_session_edit_logs")
