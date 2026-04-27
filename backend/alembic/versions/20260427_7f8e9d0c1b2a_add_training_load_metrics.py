"""add_training_load_metrics

Revision ID: 7f8e9d0c1b2a
Revises: 4e1a2b3c4d5e
Create Date: 2026-04-27 22:10:00.000000

"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f8e9d0c1b2a"
down_revision: Union[str, None] = "4e1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("training_sessions")}

    with op.batch_alter_table("training_sessions", schema=None) as batch_op:
        if "session_duration_minutes" not in existing_columns:
            batch_op.add_column(sa.Column("session_duration_minutes", sa.Integer(), nullable=True))
        if "session_srpe_load" not in existing_columns:
            batch_op.add_column(sa.Column("session_srpe_load", sa.Integer(), nullable=True))
        if "load_metrics_updated_at" not in existing_columns:
            batch_op.add_column(sa.Column("load_metrics_updated_at", sa.DateTime(timezone=True), nullable=True))

    if "athlete_daily_training_loads" not in inspector.get_table_names():
        op.create_table(
            "athlete_daily_training_loads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("athletes.id"), nullable=False),
            sa.Column("load_date", sa.Date(), nullable=False),
            sa.Column("session_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_duration_minutes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_srpe_load", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_session_ids", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("athlete_id", "load_date", name="uq_athlete_daily_training_loads_athlete_date"),
        )
        op.create_index("ix_athlete_daily_training_loads_athlete_id", "athlete_daily_training_loads", ["athlete_id"])
        op.create_index("ix_athlete_daily_training_loads_load_date", "athlete_daily_training_loads", ["load_date"])

    _backfill_training_load_metrics(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "athlete_daily_training_loads" in inspector.get_table_names():
        op.drop_index("ix_athlete_daily_training_loads_load_date", table_name="athlete_daily_training_loads")
        op.drop_index("ix_athlete_daily_training_loads_athlete_id", table_name="athlete_daily_training_loads")
        op.drop_table("athlete_daily_training_loads")

    existing_columns = {column["name"] for column in inspector.get_columns("training_sessions")}
    with op.batch_alter_table("training_sessions", schema=None) as batch_op:
        if "load_metrics_updated_at" in existing_columns:
            batch_op.drop_column("load_metrics_updated_at")
        if "session_srpe_load" in existing_columns:
            batch_op.drop_column("session_srpe_load")
        if "session_duration_minutes" in existing_columns:
            batch_op.drop_column("session_duration_minutes")


def _backfill_training_load_metrics(bind) -> None:
    first_record_rows = bind.execute(
        sa.text(
            """
            SELECT training_session_items.session_id AS session_id, MIN(set_records.completed_at) AS first_record_at
            FROM training_session_items
            JOIN set_records ON set_records.session_item_id = training_session_items.id
            GROUP BY training_session_items.session_id
            """
        )
    ).mappings()
    first_record_map = {row["session_id"]: _parse_datetime(row["first_record_at"]) for row in first_record_rows}

    session_rows = bind.execute(
        sa.text(
            """
            SELECT id, athlete_id, session_date, started_at, completed_at, session_rpe
            FROM training_sessions
            """
        )
    ).mappings()
    now = datetime.now(timezone.utc)

    daily_totals: dict[tuple[int, object], dict[str, object]] = defaultdict(
        lambda: {
            "session_count": 0,
            "total_duration_minutes": 0,
            "total_srpe_load": 0,
            "source_session_ids": [],
        }
    )

    for row in session_rows:
        session_id = row["id"]
        started_at = first_record_map.get(session_id) or _parse_datetime(row["started_at"])
        completed_at = _parse_datetime(row["completed_at"])
        session_rpe = row["session_rpe"]

        duration_minutes, srpe_load = _calculate_metrics(started_at, completed_at, session_rpe)
        bind.execute(
            sa.text(
                """
                UPDATE training_sessions
                SET session_duration_minutes = :session_duration_minutes,
                    session_srpe_load = :session_srpe_load,
                    load_metrics_updated_at = :load_metrics_updated_at
                WHERE id = :session_id
                """
            ),
            {
                "session_id": session_id,
                "session_duration_minutes": duration_minutes,
                "session_srpe_load": srpe_load,
                "load_metrics_updated_at": now,
            },
        )

        if duration_minutes is None or srpe_load is None:
            continue

        key = (row["athlete_id"], row["session_date"])
        daily_totals[key]["session_count"] += 1
        daily_totals[key]["total_duration_minutes"] += duration_minutes
        daily_totals[key]["total_srpe_load"] += srpe_load
        daily_totals[key]["source_session_ids"].append(session_id)

    bind.execute(sa.text("DELETE FROM athlete_daily_training_loads"))
    for (athlete_id, load_date), payload in daily_totals.items():
        bind.execute(
            sa.text(
                """
                INSERT INTO athlete_daily_training_loads (
                    athlete_id,
                    load_date,
                    session_count,
                    total_duration_minutes,
                    total_srpe_load,
                    source_session_ids,
                    created_at,
                    updated_at
                ) VALUES (
                    :athlete_id,
                    :load_date,
                    :session_count,
                    :total_duration_minutes,
                    :total_srpe_load,
                    :source_session_ids,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                "athlete_id": athlete_id,
                "load_date": load_date,
                "session_count": payload["session_count"],
                "total_duration_minutes": payload["total_duration_minutes"],
                "total_srpe_load": payload["total_srpe_load"],
                "source_session_ids": json.dumps(payload["source_session_ids"]),
                "created_at": now,
                "updated_at": now,
            },
        )


def _calculate_metrics(
    started_at: datetime | None,
    completed_at: datetime | None,
    session_rpe: int | None,
) -> tuple[int | None, int | None]:
    if started_at is None or completed_at is None or session_rpe is None:
        return None, None

    diff_seconds = (completed_at - started_at).total_seconds()
    if diff_seconds <= 0:
        return None, None

    duration_minutes = max(1, round(diff_seconds / 60))
    return duration_minutes, duration_minutes * int(session_rpe)


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_aware_utc(value)

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return _ensure_aware_utc(datetime.fromisoformat(normalized))
    except ValueError:
        for pattern in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return _ensure_aware_utc(datetime.strptime(text, pattern))
            except ValueError:
                continue
    return None


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
