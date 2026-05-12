"""add_athlete_birth_date

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-05-12 11:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    athlete_columns = {column["name"] for column in sa.inspect(bind).get_columns("athletes")}

    if "birth_date" not in athlete_columns:
        with op.batch_alter_table("athletes", schema=None) as batch_op:
            batch_op.add_column(sa.Column("birth_date", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    athlete_columns = {column["name"] for column in sa.inspect(bind).get_columns("athletes")}

    if "birth_date" in athlete_columns:
        with op.batch_alter_table("athletes", schema=None) as batch_op:
            batch_op.drop_column("birth_date")
