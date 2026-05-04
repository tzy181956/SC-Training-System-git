"""add_test_definition_catalog

Revision ID: 9c1d2e3f4a5b
Revises: 8a9b0c1d2e3f
Create Date: 2026-04-29 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.test_definition_defaults import DEFAULT_TEST_DEFINITION_CATALOG


# revision identifiers, used by Alembic.
revision: str = "9c1d2e3f4a5b"
down_revision: Union[str, None] = "8a9b0c1d2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "test_type_definitions" not in existing_tables:
        op.create_table(
            "test_type_definitions",
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )

    if "test_metric_definitions" not in existing_tables:
        op.create_table(
            "test_metric_definitions",
            sa.Column("test_type_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("default_unit", sa.String(length=30), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["test_type_id"], ["test_type_definitions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("test_type_id", "code", name="uq_test_metric_definition_type_code"),
            sa.UniqueConstraint("test_type_id", "name", name="uq_test_metric_definition_type_name"),
        )

    op.execute("CREATE INDEX IF NOT EXISTS ix_test_type_definitions_id ON test_type_definitions(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_metric_definitions_id ON test_metric_definitions(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_metric_definitions_test_type_id ON test_metric_definitions(test_type_id)")

    _seed_default_test_definitions(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "test_metric_definitions" in existing_tables:
        op.drop_table("test_metric_definitions")
    if "test_type_definitions" in existing_tables:
        op.drop_table("test_type_definitions")


def _seed_default_test_definitions(bind) -> None:
    has_existing_definition = bind.execute(
        sa.text("SELECT id FROM test_type_definitions LIMIT 1")
    ).scalar()
    if has_existing_definition is not None:
        return

    for definition in DEFAULT_TEST_DEFINITION_CATALOG:
        bind.execute(
            sa.text(
                """
                INSERT INTO test_type_definitions(name, code, notes)
                VALUES (:name, :code, :notes)
                """
            ),
            {
                "name": definition["name"],
                "code": definition["code"],
                "notes": definition["notes"],
            },
        )

    for definition in DEFAULT_TEST_DEFINITION_CATALOG:
        type_id = bind.execute(
            sa.text("SELECT id FROM test_type_definitions WHERE code = :code"),
            {"code": definition["code"]},
        ).scalar_one()
        for metric in definition["metrics"]:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO test_metric_definitions(test_type_id, name, code, default_unit, notes)
                    VALUES (:test_type_id, :name, :code, :default_unit, :notes)
                    """
                ),
                {
                    "test_type_id": type_id,
                    "name": metric["name"],
                    "code": metric["code"],
                    "default_unit": metric["default_unit"],
                    "notes": metric["notes"],
                },
            )
