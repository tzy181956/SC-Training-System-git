"""add_fk_constraints_for_metadata_drift

Revision ID: c9d0e1f2a3b4
Revises: f8a9b0c1d2e3
Create Date: 2026-05-16 09:20:00.000000

"""

from __future__ import annotations

from typing import NamedTuple, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MAX_ORPHAN_SAMPLES = 20


class ForeignKeySpec(NamedTuple):
    table: str
    column: str
    referred_table: str
    name: str
    referred_column: str = "id"


FK_SPECS: tuple[ForeignKeySpec, ...] = (
    ForeignKeySpec("exercises", "created_by_user_id", "users", "fk_exercises_created_by_user_id_users"),
    ForeignKeySpec("exercises", "owner_user_id", "users", "fk_exercises_owner_user_id_users"),
    ForeignKeySpec("test_type_definitions", "sport_id", "sports", "fk_test_type_definitions_sport_id_sports"),
    ForeignKeySpec("test_type_definitions", "team_id", "teams", "fk_test_type_definitions_team_id_teams"),
    ForeignKeySpec(
        "training_plan_template_items",
        "initial_load_test_metric_definition_id",
        "test_metric_definitions",
        "fk_training_plan_template_items_initial_load_test_metric_definition_id_test_metric_definitions",
    ),
    ForeignKeySpec(
        "training_plan_templates",
        "created_by_user_id",
        "users",
        "fk_training_plan_templates_created_by_user_id_users",
    ),
    ForeignKeySpec(
        "training_plan_templates",
        "owner_user_id",
        "users",
        "fk_training_plan_templates_owner_user_id_users",
    ),
    ForeignKeySpec(
        "training_plan_templates",
        "source_template_id",
        "training_plan_templates",
        "fk_training_plan_templates_source_template_id_training_plan_templates",
    ),
    ForeignKeySpec("users", "sport_id", "sports", "fk_users_sport_id_sports"),
)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _ensure_fk_columns_exist(bind: sa.engine.Connection, spec: ForeignKeySpec) -> None:
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    for table_name in (spec.table, spec.referred_table):
        if table_name not in table_names:
            raise RuntimeError(f"Required table is missing before FK migration: {table_name}")

    child_columns = {column["name"] for column in inspector.get_columns(spec.table)}
    if "id" not in child_columns:
        raise RuntimeError(f"Required id column is missing before FK migration: {spec.table}.id")
    if spec.column not in child_columns:
        raise RuntimeError(f"Required column is missing before FK migration: {spec.table}.{spec.column}")

    referred_columns = {column["name"] for column in inspector.get_columns(spec.referred_table)}
    if spec.referred_column not in referred_columns:
        raise RuntimeError(
            "Required reference column is missing before FK migration: "
            f"{spec.referred_table}.{spec.referred_column}"
        )


def _find_orphans(bind: sa.engine.Connection, spec: ForeignKeySpec) -> tuple[int, list[tuple[int, int]]]:
    table = _quote_identifier(spec.table)
    column = _quote_identifier(spec.column)
    referred_table = _quote_identifier(spec.referred_table)
    referred_column = _quote_identifier(spec.referred_column)

    count_sql = sa.text(
        f"""
        SELECT COUNT(*) AS orphan_count
        FROM {table} AS child
        LEFT JOIN {referred_table} AS parent
            ON child.{column} = parent.{referred_column}
        WHERE child.{column} IS NOT NULL
          AND parent.{referred_column} IS NULL
        """
    )
    sample_sql = sa.text(
        f"""
        SELECT child."id" AS row_id, child.{column} AS orphan_value
        FROM {table} AS child
        LEFT JOIN {referred_table} AS parent
            ON child.{column} = parent.{referred_column}
        WHERE child.{column} IS NOT NULL
          AND parent.{referred_column} IS NULL
        ORDER BY child."id"
        LIMIT :limit
        """
    )

    orphan_count = int(bind.execute(count_sql).scalar_one())
    if orphan_count == 0:
        return 0, []

    rows = bind.execute(sample_sql, {"limit": MAX_ORPHAN_SAMPLES}).mappings().all()
    return orphan_count, [(int(row["row_id"]), int(row["orphan_value"])) for row in rows]


def _assert_no_orphans() -> None:
    bind = op.get_bind()
    orphan_messages: list[str] = []

    for spec in FK_SPECS:
        _ensure_fk_columns_exist(bind, spec)
        orphan_count, samples = _find_orphans(bind, spec)
        if orphan_count == 0:
            continue

        sample_text = ", ".join(
            f"{spec.table}.id={row_id} {spec.column}={orphan_value}" for row_id, orphan_value in samples
        )
        orphan_messages.append(
            f"{spec.table}.{spec.column} -> {spec.referred_table}.{spec.referred_column}: "
            f"{orphan_count} orphan(s); samples: {sample_text or '(none)'}"
        )

    if orphan_messages:
        details = "\n".join(f"- {message}" for message in orphan_messages)
        raise RuntimeError(f"Cannot add FK constraints while orphan references exist:\n{details}")


def _foreign_key_exists(
    inspector: sa.engine.reflection.Inspector,
    spec: ForeignKeySpec,
    *,
    match_equivalent_relation: bool = True,
) -> bool:
    for foreign_key in inspector.get_foreign_keys(spec.table):
        constrained_columns = list(foreign_key.get("constrained_columns") or [])
        referred_columns = list(foreign_key.get("referred_columns") or [])
        if foreign_key.get("name") == spec.name:
            return True
        if match_equivalent_relation and (
            constrained_columns == [spec.column]
            and foreign_key.get("referred_table") == spec.referred_table
            and referred_columns == [spec.referred_column]
        ):
            return True
    return False


def _create_foreign_keys() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    specs_by_table: dict[str, list[ForeignKeySpec]] = {}
    for spec in FK_SPECS:
        if _foreign_key_exists(inspector, spec):
            continue
        specs_by_table.setdefault(spec.table, []).append(spec)

    for table_name, specs in specs_by_table.items():
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            for spec in specs:
                batch_op.create_foreign_key(
                    spec.name,
                    spec.referred_table,
                    [spec.column],
                    [spec.referred_column],
                )


def _drop_foreign_keys() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    specs_by_table: dict[str, list[ForeignKeySpec]] = {}
    for spec in FK_SPECS:
        if _foreign_key_exists(inspector, spec, match_equivalent_relation=False):
            specs_by_table.setdefault(spec.table, []).append(spec)

    for table_name, specs in specs_by_table.items():
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            for spec in reversed(specs):
                batch_op.drop_constraint(spec.name, type_="foreignkey")


def upgrade() -> None:
    _assert_no_orphans()
    _create_foreign_keys()


def downgrade() -> None:
    _drop_foreign_keys()
