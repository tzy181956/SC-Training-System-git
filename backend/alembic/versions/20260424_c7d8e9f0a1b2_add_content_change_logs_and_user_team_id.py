"""add_content_change_logs_and_user_team_id

Revision ID: c7d8e9f0a1b2
Revises: f3a4b5c6d7e8
Create Date: 2026-04-24 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "team_id" not in user_columns:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(sa.Column("team_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_users_team_id_teams", "teams", ["team_id"], ["id"])
            batch_op.create_index(batch_op.f("ix_users_team_id"), ["team_id"], unique=False)
    elif batch_op_name("ix_users_team_id") not in user_indexes:
        op.create_index(batch_op_name("ix_users_team_id"), "users", ["team_id"], unique=False)

    table_names = set(inspector.get_table_names())
    if "content_change_logs" not in table_names:
        op.create_table(
            "content_change_logs",
            sa.Column("action_type", sa.String(length=30), nullable=False),
            sa.Column("object_type", sa.String(length=50), nullable=False),
            sa.Column("object_id", sa.Integer(), nullable=True),
            sa.Column("object_label", sa.String(length=160), nullable=True),
            sa.Column("actor_name", sa.String(length=120), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("before_snapshot", sa.JSON(), nullable=True),
            sa.Column("after_snapshot", sa.JSON(), nullable=True),
            sa.Column("extra_context", sa.JSON(), nullable=True),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("content_change_logs")}
    with op.batch_alter_table("content_change_logs", schema=None) as batch_op:
        if batch_op.f("ix_content_change_logs_action_type") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_content_change_logs_action_type"), ["action_type"], unique=False)
        if batch_op.f("ix_content_change_logs_actor_name") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_content_change_logs_actor_name"), ["actor_name"], unique=False)
        if batch_op.f("ix_content_change_logs_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_content_change_logs_id"), ["id"], unique=False)
        if batch_op.f("ix_content_change_logs_object_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_content_change_logs_object_id"), ["object_id"], unique=False)
        if batch_op.f("ix_content_change_logs_object_type") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_content_change_logs_object_type"), ["object_type"], unique=False)
        if batch_op.f("ix_content_change_logs_team_id") not in existing_indexes:
            batch_op.create_index(batch_op.f("ix_content_change_logs_team_id"), ["team_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "content_change_logs" in inspector.get_table_names():
        existing_indexes = {index["name"] for index in inspector.get_indexes("content_change_logs")}
        with op.batch_alter_table("content_change_logs", schema=None) as batch_op:
            if batch_op.f("ix_content_change_logs_team_id") in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_content_change_logs_team_id"))
            if batch_op.f("ix_content_change_logs_object_type") in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_content_change_logs_object_type"))
            if batch_op.f("ix_content_change_logs_object_id") in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_content_change_logs_object_id"))
            if batch_op.f("ix_content_change_logs_id") in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_content_change_logs_id"))
            if batch_op.f("ix_content_change_logs_actor_name") in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_content_change_logs_actor_name"))
            if batch_op.f("ix_content_change_logs_action_type") in existing_indexes:
                batch_op.drop_index(batch_op.f("ix_content_change_logs_action_type"))
        op.drop_table("content_change_logs")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "team_id" in user_columns:
        with op.batch_alter_table("users", schema=None) as batch_op:
            if batch_op.f("ix_users_team_id") in user_indexes:
                batch_op.drop_index(batch_op.f("ix_users_team_id"))
            try:
                batch_op.drop_constraint("fk_users_team_id_teams", type_="foreignkey")
            except Exception:
                pass
            batch_op.drop_column("team_id")


def batch_op_name(index_name: str) -> str:
    return f"ix_users_team_id" if index_name == "ix_users_team_id" else index_name
