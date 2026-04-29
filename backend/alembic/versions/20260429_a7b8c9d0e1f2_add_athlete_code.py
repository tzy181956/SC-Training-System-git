"""add_athlete_code

Revision ID: a7b8c9d0e1f2
Revises: e1f2a3b4c5d6
Create Date: 2026-04-29 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("code", sa.String(length=64), nullable=True))

    op.execute(
        "UPDATE athletes "
        "SET code = printf('ATH-%06d', id) "
        "WHERE code IS NULL OR trim(code) = ''"
    )

    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.alter_column("code", existing_type=sa.String(length=64), nullable=False)
        batch_op.create_unique_constraint("uq_athletes_code", ["code"])


def downgrade() -> None:
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_athletes_code", type_="unique")
        batch_op.drop_column("code")
