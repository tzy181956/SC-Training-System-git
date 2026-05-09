"""backfill_test_definition_catalog

Revision ID: d4e5f6a7b8c9
Revises: 9c1d2e3f4a5b
Create Date: 2026-04-29 22:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.test_definition_defaults import DEFAULT_TEST_DEFINITION_CATALOG


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "9c1d2e3f4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "test_metric_definitions" in existing_tables:
        existing_columns = {column["name"] for column in inspector.get_columns("test_metric_definitions")}
        if "is_lower_better" not in existing_columns:
            op.execute("DROP TABLE IF EXISTS _alembic_tmp_test_metric_definitions")
            with op.batch_alter_table("test_metric_definitions") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_lower_better",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )

    if "test_type_definitions" in existing_tables and "test_metric_definitions" in existing_tables:
        _backfill_default_test_definitions(bind, inspector)


def downgrade() -> None:
    return None


def _backfill_default_test_definitions(bind, inspector) -> None:
    type_columns = {column["name"] for column in inspector.get_columns("test_type_definitions")}
    metric_columns = {column["name"] for column in inspector.get_columns("test_metric_definitions")}

    has_metric_direction = "is_lower_better" in metric_columns

    for definition in DEFAULT_TEST_DEFINITION_CATALOG:
        existing_type_id = bind.execute(
            sa.text(
                """
                SELECT id
                FROM test_type_definitions
                WHERE name = :name OR code = :code
                LIMIT 1
                """
            ),
            {
                "name": definition["name"],
                "code": definition["code"],
            },
        ).scalar()
        if existing_type_id is None:
            insert_type_values = {
                "name": definition["name"],
                "code": definition["code"],
                "notes": definition["notes"],
            }
            insert_type_columns = ["name", "code", "notes"]
            if "sport_id" in type_columns:
                insert_type_columns.append("sport_id")
                insert_type_values["sport_id"] = None
            if "team_id" in type_columns:
                insert_type_columns.append("team_id")
                insert_type_values["team_id"] = None

            bind.execute(
                sa.text(
                    f"""
                    INSERT INTO test_type_definitions ({", ".join(insert_type_columns)})
                    VALUES ({", ".join(f":{column}" for column in insert_type_columns)})
                    """
                ),
                insert_type_values,
            )
            existing_type_id = bind.execute(
                sa.text("SELECT id FROM test_type_definitions WHERE code = :code LIMIT 1"),
                {"code": definition["code"]},
            ).scalar_one()

        for metric in definition["metrics"]:
            existing_metric_id = bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM test_metric_definitions
                    WHERE test_type_id = :test_type_id
                      AND (name = :name OR code = :code)
                    LIMIT 1
                    """
                ),
                {
                    "test_type_id": existing_type_id,
                    "name": metric["name"],
                    "code": metric["code"],
                },
            ).scalar()
            if existing_metric_id is None:
                insert_metric_values = {
                    "test_type_id": existing_type_id,
                    "name": metric["name"],
                    "code": metric["code"],
                    "default_unit": metric["default_unit"],
                    "notes": metric["notes"],
                }
                insert_metric_columns = ["test_type_id", "name", "code", "default_unit", "notes"]
                if has_metric_direction:
                    insert_metric_columns.append("is_lower_better")
                    insert_metric_values["is_lower_better"] = bool(metric.get("is_lower_better", False))

                bind.execute(
                    sa.text(
                        f"""
                        INSERT INTO test_metric_definitions ({", ".join(insert_metric_columns)})
                        VALUES ({", ".join(f":{column}" for column in insert_metric_columns)})
                        """
                    ),
                    insert_metric_values,
                )
                continue

            bind.execute(
                sa.text(
                    """
                    UPDATE test_metric_definitions
                    SET default_unit = COALESCE(default_unit, :default_unit)
                    WHERE id = :metric_id
                    """
                ),
                {
                    "default_unit": metric["default_unit"],
                    "metric_id": existing_metric_id,
                },
            )
