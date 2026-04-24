"""add_dangerous_operation_logs

Revision ID: f3a4b5c6d7e8
Revises: b1f8d2e7c6a1
Create Date: 2026-04-24 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "b1f8d2e7c6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "dangerous_operation_logs" not in table_names:
        op.create_table(
            "dangerous_operation_logs",
            sa.Column("operation_key", sa.String(length=50), nullable=False),
            sa.Column("object_type", sa.String(length=50), nullable=False),
            sa.Column("object_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=120), nullable=False),
            sa.Column("source", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("impact_scope", sa.JSON(), nullable=True),
            sa.Column("confirmation_required", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("confirmation_phrase", sa.String(length=80), nullable=True),
            sa.Column("backup_path", sa.String(length=255), nullable=True),
            sa.Column("extra_data", sa.JSON(), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {
        index["name"] for index in inspector.get_indexes("dangerous_operation_logs")
    }
    with op.batch_alter_table("dangerous_operation_logs", schema=None) as batch_op:
        if batch_op.f("ix_dangerous_operation_logs_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_dangerous_operation_logs_id"), ["id"], unique=False)
        if batch_op.f("ix_dangerous_operation_logs_object_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_dangerous_operation_logs_object_id"), ["object_id"], unique=False)
        if batch_op.f("ix_dangerous_operation_logs_object_type") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_dangerous_operation_logs_object_type"), ["object_type"], unique=False)
        if batch_op.f("ix_dangerous_operation_logs_operation_key") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_dangerous_operation_logs_operation_key"), ["operation_key"], unique=False)
        if batch_op.f("ix_dangerous_operation_logs_status") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_dangerous_operation_logs_status"), ["status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "dangerous_operation_logs" not in inspector.get_table_names():
        return

    existing_indexes = {
        index["name"] for index in inspector.get_indexes("dangerous_operation_logs")
    }
    with op.batch_alter_table("dangerous_operation_logs", schema=None) as batch_op:
        if batch_op.f("ix_dangerous_operation_logs_status") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_dangerous_operation_logs_status"))
        if batch_op.f("ix_dangerous_operation_logs_operation_key") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_dangerous_operation_logs_operation_key"))
        if batch_op.f("ix_dangerous_operation_logs_object_type") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_dangerous_operation_logs_object_type"))
        if batch_op.f("ix_dangerous_operation_logs_object_id") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_dangerous_operation_logs_object_id"))
        if batch_op.f("ix_dangerous_operation_logs_id") in existing_indexes:
            batch_op.drop_index(batch_op.f("ix_dangerous_operation_logs_id"))

    op.drop_table("dangerous_operation_logs")
