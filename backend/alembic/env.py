from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.database import Base
from app.models import *  # noqa: F401,F403


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_database_url() -> str:
    override = os.getenv("ALEMBIC_DATABASE_URL")
    if override:
        return override
    return get_settings().database_url


database_url = _resolve_database_url()
config.set_main_option("sqlalchemy.url", database_url)
target_metadata = Base.metadata
is_sqlite_database = make_url(database_url).get_backend_name() == "sqlite"
SQLITE_REDUNDANT_PK_ID_INDEXES = {
    ("athlete_daily_training_loads", "ix_athlete_daily_training_loads_id"),
    ("dashboard_memos", "ix_dashboard_memos_id"),
    ("training_plan_template_modules", "ix_training_plan_template_modules_id"),
}


def _is_athlete_code_unique_constraint(obj: object) -> bool:
    table = getattr(obj, "table", None)
    if getattr(table, "name", None) != "athletes":
        return False
    columns = [column.name for column in getattr(obj, "columns", [])]
    return columns == ["code"]


def _is_known_sqlite_redundant_pk_id_index(obj: object, name: str | None) -> bool:
    table = getattr(obj, "table", None)
    table_name = getattr(table, "name", None)
    columns = [column.name for column in getattr(obj, "columns", [])]
    return (table_name, name) in SQLITE_REDUNDANT_PK_ID_INDEXES and columns == ["id"]


def include_object(obj: object, name: str | None, type_: str, reflected: bool, compare_to: object | None) -> bool:
    if not is_sqlite_database:
        return True

    # SQLite reflects the athletes.code unique index and ORM unique constraint
    # as different objects even though both enforce the same single-column rule.
    if type_ == "index" and reflected and name == "ix_athletes_code_unique":
        return False
    if type_ == "unique_constraint" and not reflected and name is None and _is_athlete_code_unique_constraint(obj):
        return False

    # A few historical SQLite migrations omitted redundant BaseModel primary-key
    # id indexes. Primary keys are already indexed, so avoid adding migrations
    # solely to create these known duplicate indexes.
    if type_ == "index" and not reflected and _is_known_sqlite_redundant_pk_id_index(obj, name):
        return False

    return True


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
