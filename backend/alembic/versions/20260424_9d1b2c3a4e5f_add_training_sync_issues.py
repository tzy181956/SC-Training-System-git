"""add_training_sync_issues

Revision ID: 9d1b2c3a4e5f
Revises: 5f2d4f0f4b8b
Create Date: 2026-04-24 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d1b2c3a4e5f"
down_revision: Union[str, None] = "5f2d4f0f4b8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_sync_issues",
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("session_key", sa.String(length=160), nullable=False),
        sa.Column("issue_status", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sync_payload", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["athlete_plan_assignments.id"]),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("training_sync_issues", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_training_sync_issues_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_training_sync_issues_issue_status"), ["issue_status"], unique=False)
        batch_op.create_index(batch_op.f("ix_training_sync_issues_session_date"), ["session_date"], unique=False)
        batch_op.create_index(batch_op.f("ix_training_sync_issues_session_key"), ["session_key"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("training_sync_issues", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_training_sync_issues_session_key"))
        batch_op.drop_index(batch_op.f("ix_training_sync_issues_session_date"))
        batch_op.drop_index(batch_op.f("ix_training_sync_issues_issue_status"))
        batch_op.drop_index(batch_op.f("ix_training_sync_issues_id"))

    op.drop_table("training_sync_issues")
