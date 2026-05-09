"""sport_scope_and_reset_test_data

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-05-07 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RESET_TABLES = [
    "training_sync_conflicts",
    "training_sync_issues",
    "training_session_edit_logs",
    "dangerous_operation_logs",
    "content_change_logs",
    "athlete_daily_training_loads",
    "set_records",
    "training_session_items",
    "training_sessions",
    "assignment_item_overrides",
    "athlete_plan_assignments",
    "test_records",
    "test_metric_definitions",
    "test_type_definitions",
    "training_plan_template_items",
    "training_plan_templates",
    "athletes",
    "teams",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    has_sqlite_sequence = bool(
        bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")).fetchone()
    )

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "sport_id" not in user_columns:
        user_sport_column = sa.Column("sport_id", sa.Integer(), nullable=True) if is_sqlite else sa.Column(
            "sport_id",
            sa.Integer(),
            sa.ForeignKey("sports.id"),
            nullable=True,
        )
        op.add_column("users", user_sport_column)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_sport_id ON users(sport_id)")

    definition_columns = {column["name"] for column in inspector.get_columns("test_type_definitions")}
    if "sport_id" not in definition_columns:
        definition_sport_column = sa.Column("sport_id", sa.Integer(), nullable=True) if is_sqlite else sa.Column(
            "sport_id",
            sa.Integer(),
            sa.ForeignKey("sports.id"),
            nullable=True,
        )
        op.add_column(
            "test_type_definitions",
            definition_sport_column,
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_test_type_definitions_sport_id ON test_type_definitions(sport_id)")

    for table_name in RESET_TABLES:
        op.execute(sa.text(f"DELETE FROM {table_name}"))

    op.execute(sa.text("DELETE FROM users WHERE lower(trim(role_code)) <> 'admin'"))
    op.execute(sa.text("UPDATE users SET sport_id = NULL, team_id = NULL"))

    if has_sqlite_sequence:
        table_names = "', '".join(RESET_TABLES)
        op.execute(sa.text(f"DELETE FROM sqlite_sequence WHERE name IN ('{table_names}')"))
        op.execute(sa.text("DELETE FROM sqlite_sequence WHERE name = 'users'"))
        op.execute(
            sa.text(
                """
                INSERT INTO sqlite_sequence(name, seq)
                SELECT 'users', COALESCE(MAX(id), 0)
                FROM users
                WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = 'users')
                """
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE sqlite_sequence
                SET seq = (SELECT COALESCE(MAX(id), 0) FROM users)
                WHERE name = 'users'
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    definition_columns = {column["name"] for column in inspector.get_columns("test_type_definitions")}

    op.execute("DROP INDEX IF EXISTS ix_users_sport_id")
    op.execute("DROP INDEX IF EXISTS ix_test_type_definitions_sport_id")

    if "sport_id" in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("sport_id")
    if "sport_id" in definition_columns:
        with op.batch_alter_table("test_type_definitions") as batch_op:
            batch_op.drop_column("sport_id")
