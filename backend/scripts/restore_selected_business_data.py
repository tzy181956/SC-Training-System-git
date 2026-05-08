from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.services import backup_service, dangerous_operation_service


DELETE_ORDER = [
    "assignment_item_overrides",
    "athlete_plan_assignments",
    "training_plan_template_items",
    "training_plan_templates",
    "test_records",
    "test_metric_definitions",
    "test_type_definitions",
    "athletes",
    "teams",
]

INSERT_ORDER = [
    "teams",
    "athletes",
    "training_plan_templates",
    "training_plan_template_items",
    "athlete_plan_assignments",
    "assignment_item_overrides",
    "test_type_definitions",
    "test_metric_definitions",
    "test_records",
]


def _require_sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError(f"Only sqlite database URLs are supported: {database_url}")
    return Path(database_url.removeprefix(prefix))


def _table_columns(connection: sqlite3.Connection, schema_name: str, table_name: str) -> list[str]:
    rows = connection.execute(f'PRAGMA {schema_name}.table_info("{table_name}")').fetchall()
    return [row[1] for row in rows]


def _reset_sqlite_sequence(connection: sqlite3.Connection, table_name: str) -> None:
    if connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'").fetchone() is None:
        return
    max_id = connection.execute(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"').fetchone()[0]
    existing = connection.execute("SELECT 1 FROM sqlite_sequence WHERE name = ?", (table_name,)).fetchone()
    if existing:
        connection.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (max_id, table_name))
    else:
        connection.execute("INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", (table_name, max_id))


def restore_selected_business_data(*, backup_filename: str, actor_name: str | None = None) -> dict[str, int]:
    settings = get_settings()
    database_path = _require_sqlite_path(settings.database_url)
    backup_path = backup_service.get_backup_directory() / Path(backup_filename).name
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    pre_restore_backup = backup_service.create_pre_dangerous_operation_backup(
        label="before_selective_restore_business_data"
    )

    engine.dispose()
    restored_counts: dict[str, int] = {}
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("ATTACH DATABASE ? AS restore_source", (str(backup_path),))
        try:
            connection.execute("BEGIN IMMEDIATE")
            for table_name in DELETE_ORDER:
                connection.execute(f'DELETE FROM "{table_name}"')

            for table_name in INSERT_ORDER:
                target_columns = _table_columns(connection, "main", table_name)
                source_columns = set(_table_columns(connection, "restore_source", table_name))
                common_columns = [column_name for column_name in target_columns if column_name in source_columns]
                if common_columns:
                    columns_sql = ", ".join(f'"{column_name}"' for column_name in common_columns)
                    connection.execute(
                        f'INSERT INTO main."{table_name}" ({columns_sql}) '
                        f'SELECT {columns_sql} FROM restore_source."{table_name}"'
                    )
                restored_counts[table_name] = connection.execute(
                    f'SELECT COUNT(*) FROM main."{table_name}"'
                ).fetchone()[0]
                _reset_sqlite_sequence(connection, table_name)

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.execute("DETACH DATABASE restore_source")
            connection.execute("PRAGMA foreign_keys = ON")
    finally:
        connection.close()

    with SessionLocal() as db:
        dangerous_operation_service.log_dangerous_operation(
            db,
            operation_key="restore_selected_business_data",
            object_type="database",
            actor_name=actor_name,
            source="script",
            confirmation_phrase=dangerous_operation_service.RESTORE_BACKUP_CONFIRMATION,
            summary=f"从备份 {backup_path.name} 选择性恢复队伍、运动员、模板、计划分配和测试数据",
            impact_scope={
                "backup_name": backup_path.name,
                "restored_tables": INSERT_ORDER,
                "restored_counts": restored_counts,
            },
            backup_path=pre_restore_backup.backup_path,
            extra_data={
                "backup_name": backup_path.name,
                "restored_counts": restored_counts,
                "preserved_tables": ["users", "sports"],
            },
        )
        db.commit()

    return restored_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore selected business data from a managed backup.")
    parser.add_argument(
        "--backup",
        default="training-20260507-203427-before_migration-upgrade_from_c3d4e5f6a7b8.db",
        help="Backup filename under backend/backups/",
    )
    parser.add_argument("--actor", default=None, help="Optional actor name for dangerous operation log.")
    args = parser.parse_args()

    restored_counts = restore_selected_business_data(backup_filename=args.backup, actor_name=args.actor)
    for table_name in INSERT_ORDER:
        print(f"{table_name}: {restored_counts.get(table_name, 0)}")


if __name__ == "__main__":
    main()
