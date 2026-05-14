"""add_user_token_version_fields

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-14 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "users"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if "token_version" not in columns:
            batch_op.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"))
        if "password_changed_at" not in columns:
            batch_op.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
        if "last_login_at" not in columns:
            batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        if "last_login_ip" not in columns:
            batch_op.add_column(sa.Column("last_login_ip", sa.String(length=45), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}

    with op.batch_alter_table(TABLE_NAME, schema=None) as batch_op:
        if "last_login_ip" in columns:
            batch_op.drop_column("last_login_ip")
        if "last_login_at" in columns:
            batch_op.drop_column("last_login_at")
        if "password_changed_at" in columns:
            batch_op.drop_column("password_changed_at")
        if "token_version" in columns:
            batch_op.drop_column("token_version")
