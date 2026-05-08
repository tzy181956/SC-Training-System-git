"""add_training_plan_template_modules

Revision ID: a1b2c3d4e5f6
Revises: d5e6f7a8b9c0
Create Date: 2026-05-08 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MODULE_TABLE = "training_plan_template_modules"
ITEM_TABLE = "training_plan_template_items"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_training_plan_template_items")

    if MODULE_TABLE not in existing_tables:
        op.create_table(
            MODULE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("template_id", sa.Integer(), sa.ForeignKey("training_plan_templates.id"), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("title", sa.String(length=120), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_training_plan_template_modules_template_id ON training_plan_template_modules(template_id)")

    item_columns = {column["name"] for column in inspector.get_columns(ITEM_TABLE)}
    if "module_id" not in item_columns:
        with op.batch_alter_table(ITEM_TABLE, schema=None) as batch_op:
            batch_op.add_column(sa.Column("module_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_training_plan_template_items_module_id",
                MODULE_TABLE,
                ["module_id"],
                ["id"],
            )
    op.execute("CREATE INDEX IF NOT EXISTS ix_training_plan_template_items_module_id ON training_plan_template_items(module_id)")

    module_table = sa.table(
        MODULE_TABLE,
        sa.column("id", sa.Integer()),
        sa.column("template_id", sa.Integer()),
        sa.column("sort_order", sa.Integer()),
        sa.column("title", sa.String()),
        sa.column("note", sa.Text()),
    )

    template_rows = bind.execute(sa.text("SELECT id FROM training_plan_templates ORDER BY id")).fetchall()
    for row in template_rows:
        template_id = row[0]
        existing_module_id = bind.execute(
            sa.text(
                "SELECT id FROM training_plan_template_modules "
                "WHERE template_id = :template_id ORDER BY sort_order ASC, id ASC LIMIT 1"
            ),
            {"template_id": template_id},
        ).scalar()
        if existing_module_id is None:
            insert_result = bind.execute(
                module_table.insert().values(
                    template_id=template_id,
                    sort_order=1,
                    title=None,
                    note=None,
                )
            )
            inserted_primary_key = getattr(insert_result, "inserted_primary_key", None) or ()
            existing_module_id = inserted_primary_key[0] if inserted_primary_key else None
            if existing_module_id is None:
                existing_module_id = bind.execute(
                    sa.text(
                        "SELECT id FROM training_plan_template_modules "
                        "WHERE template_id = :template_id ORDER BY id DESC LIMIT 1"
                    ),
                    {"template_id": template_id},
                ).scalar()
        bind.execute(
            sa.text(
                "UPDATE training_plan_template_items "
                "SET module_id = :module_id "
                "WHERE template_id = :template_id AND module_id IS NULL"
            ),
            {"module_id": existing_module_id, "template_id": template_id},
        )

    with op.batch_alter_table(ITEM_TABLE, schema=None) as batch_op:
        batch_op.alter_column("module_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    item_columns = {column["name"] for column in inspector.get_columns(ITEM_TABLE)}
    existing_tables = set(inspector.get_table_names())

    op.execute("DROP INDEX IF EXISTS ix_training_plan_template_items_module_id")
    op.execute("DROP INDEX IF EXISTS ix_training_plan_template_modules_template_id")

    if "module_id" in item_columns:
        with op.batch_alter_table(ITEM_TABLE, schema=None) as batch_op:
            batch_op.drop_constraint("fk_training_plan_template_items_module_id", type_="foreignkey")
            batch_op.drop_column("module_id")

    if MODULE_TABLE in existing_tables:
        op.drop_table(MODULE_TABLE)
