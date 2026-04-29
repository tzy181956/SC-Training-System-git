"""backfill_test_definition_catalog

Revision ID: d4e5f6a7b8c9
Revises: 9c1d2e3f4a5b
Create Date: 2026-04-29 22:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.services import test_definition_service


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
            with op.batch_alter_table("test_metric_definitions") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_lower_better",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )

    session = Session(bind=bind)
    try:
        test_definition_service.ensure_default_test_definition_catalog(session)
        test_definition_service.backfill_test_definitions_from_records(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    return None
