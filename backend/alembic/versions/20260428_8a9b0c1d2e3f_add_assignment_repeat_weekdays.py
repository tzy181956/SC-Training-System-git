"""add_assignment_repeat_weekdays

Revision ID: 8a9b0c1d2e3f
Revises: 7f8e9d0c1b2a
Create Date: 2026-04-28 23:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a9b0c1d2e3f"
down_revision: Union[str, None] = "7f8e9d0c1b2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("athlete_plan_assignments")
    }

    if "repeat_weekdays" not in existing_columns:
        with op.batch_alter_table("athlete_plan_assignments", schema=None) as batch_op:
            batch_op.add_column(sa.Column("repeat_weekdays", sa.JSON(), nullable=True))

    op.execute(
        "UPDATE athlete_plan_assignments "
        "SET repeat_weekdays = '[1,2,3,4,5,6,7]' "
        "WHERE repeat_weekdays IS NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("athlete_plan_assignments")
    }

    if "repeat_weekdays" in existing_columns:
        with op.batch_alter_table("athlete_plan_assignments", schema=None) as batch_op:
            batch_op.drop_column("repeat_weekdays")
