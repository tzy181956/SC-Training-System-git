"""add_training_session_finish_feedback

Revision ID: 4e1a2b3c4d5e
Revises: c7d8e9f0a1b2
Create Date: 2026-04-27 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e1a2b3c4d5e"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("training_sessions")}

    with op.batch_alter_table("training_sessions", schema=None) as batch_op:
        if "session_rpe" not in existing_columns:
            batch_op.add_column(sa.Column("session_rpe", sa.Integer(), nullable=True))
        if "session_feedback" not in existing_columns:
            batch_op.add_column(sa.Column("session_feedback", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("training_sessions")}

    with op.batch_alter_table("training_sessions", schema=None) as batch_op:
        if "session_feedback" in existing_columns:
            batch_op.drop_column("session_feedback")
        if "session_rpe" in existing_columns:
            batch_op.drop_column("session_rpe")
