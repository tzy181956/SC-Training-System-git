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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    athlete_columns = {
        column["name"]: column for column in inspector.get_columns("athletes")
    }

    if "code" not in athlete_columns:
        with op.batch_alter_table("athletes", schema=None) as batch_op:
            batch_op.add_column(sa.Column("code", sa.String(length=64), nullable=True))
        athlete_columns = {
            column["name"]: column for column in sa.inspect(bind).get_columns("athletes")
        }

    op.execute(
        "UPDATE athletes "
        "SET code = printf('ATH-%06d', id) "
        "WHERE code IS NULL OR trim(code) = ''"
    )

    duplicate_code = bind.execute(
        sa.text(
            """
            SELECT code
            FROM athletes
            WHERE code IS NOT NULL AND trim(code) <> ''
            GROUP BY code
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).scalar()
    if duplicate_code is not None:
        raise RuntimeError(
            f"Cannot finalize athlete code migration because duplicate code exists: {duplicate_code}"
        )

    code_column = athlete_columns["code"]
    if code_column.get("nullable", True):
        with op.batch_alter_table("athletes", schema=None) as batch_op:
            batch_op.alter_column("code", existing_type=sa.String(length=64), nullable=False)

    if not _has_unique_code(sa.inspect(bind)):
        op.create_index("ix_athletes_code_unique", "athletes", ["code"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    athlete_columns = {
        column["name"] for column in inspector.get_columns("athletes")
    }
    athlete_indexes = {
        index["name"] for index in inspector.get_indexes("athletes")
    }
    athlete_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("athletes")
        if constraint.get("name")
    }

    if "code" not in athlete_columns:
        return

    with op.batch_alter_table("athletes", schema=None) as batch_op:
        if "uq_athletes_code" in athlete_unique_constraints:
            batch_op.drop_constraint("uq_athletes_code", type_="unique")
        if "ix_athletes_code_unique" in athlete_indexes:
            batch_op.drop_index("ix_athletes_code_unique")
        batch_op.drop_column("code")


def _has_unique_code(inspector: sa.Inspector) -> bool:
    for index in inspector.get_indexes("athletes"):
        if index.get("unique") and index.get("column_names") == ["code"]:
            return True

    for constraint in inspector.get_unique_constraints("athletes"):
        if constraint.get("column_names") == ["code"]:
            return True

    return False
