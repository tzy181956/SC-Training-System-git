"""add_score_profiles

Revision ID: e7f8a9b0c1d2
Revises: b6c7d8e9f0a1
Create Date: 2026-05-11 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "score_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sport_id", sa.Integer(), sa.ForeignKey("sports.id"), nullable=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("sport_id", "name", name="uq_score_profile_sport_name"),
    )
    op.create_index("ix_score_profiles_id", "score_profiles", ["id"], unique=False)

    op.create_table(
        "score_dimensions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("score_profiles.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("profile_id", "name", name="uq_score_dimension_profile_name"),
    )
    op.create_index("ix_score_dimensions_id", "score_dimensions", ["id"], unique=False)

    op.create_table(
        "score_dimension_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dimension_id", sa.Integer(), sa.ForeignKey("score_dimensions.id"), nullable=False),
        sa.Column("test_metric_definition_id", sa.Integer(), sa.ForeignKey("test_metric_definitions.id"), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("dimension_id", "test_metric_definition_id", name="uq_score_dimension_metric_unique_metric"),
    )
    op.create_index("ix_score_dimension_metrics_id", "score_dimension_metrics", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_score_dimension_metrics_id", table_name="score_dimension_metrics")
    op.drop_table("score_dimension_metrics")
    op.drop_index("ix_score_dimensions_id", table_name="score_dimensions")
    op.drop_table("score_dimensions")
    op.drop_index("ix_score_profiles_id", table_name="score_profiles")
    op.drop_table("score_profiles")
