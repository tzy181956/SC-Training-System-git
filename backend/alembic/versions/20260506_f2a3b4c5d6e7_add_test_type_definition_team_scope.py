"""add_test_type_definition_team_scope

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-06 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("test_type_definitions")}

    if "team_id" not in existing_columns:
        op.add_column(
            "test_type_definitions",
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_test_type_definitions_team_id ON test_type_definitions(team_id)")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("test_type_definitions")}

    op.execute("DROP INDEX IF EXISTS ix_test_type_definitions_team_id")
    if "team_id" in existing_columns:
        with op.batch_alter_table("test_type_definitions") as batch_op:
            batch_op.drop_column("team_id")
