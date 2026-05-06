"""merge_athlete_code_and_test_scope_heads

Revision ID: c3d4e5f6a7b8
Revises: a7b8c9d0e1f2, f2a3b4c5d6e7
Create Date: 2026-05-06 15:20:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = ("a7b8c9d0e1f2", "f2a3b4c5d6e7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
