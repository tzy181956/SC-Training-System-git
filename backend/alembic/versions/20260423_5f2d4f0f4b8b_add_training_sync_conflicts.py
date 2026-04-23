"""add_training_sync_conflicts

Revision ID: 5f2d4f0f4b8b
Revises: c318e7988c37
Create Date: 2026-04-23 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f2d4f0f4b8b"
down_revision: Union[str, None] = "c318e7988c37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_sync_conflicts",
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("trigger_reason", sa.String(length=20), nullable=False),
        sa.Column("conflict_type", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("local_snapshot", sa.JSON(), nullable=True),
        sa.Column("remote_snapshot", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["athlete_plan_assignments.id"]),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("training_sync_conflicts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_training_sync_conflicts_athlete_id"), ["athlete_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_training_sync_conflicts_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_training_sync_conflicts_session_date"), ["session_date"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("training_sync_conflicts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_training_sync_conflicts_session_date"))
        batch_op.drop_index(batch_op.f("ix_training_sync_conflicts_id"))
        batch_op.drop_index(batch_op.f("ix_training_sync_conflicts_athlete_id"))

    op.drop_table("training_sync_conflicts")
