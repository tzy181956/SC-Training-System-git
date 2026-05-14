"""delete_vibration_equipment_exercises

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-05-14 16:35:00.000000

"""

from typing import Sequence, Union


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No schema change is needed. The original destructive exercise cleanup was
    # moved to backend/scripts/data_cleanup/delete_vibration_equipment_exercises.py
    # so deploy-time Alembic upgrades never delete business data implicitly.
    pass


def downgrade() -> None:
    pass
