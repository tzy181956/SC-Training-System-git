from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings


MAX_SAMPLES = 20
EXIT_OK = 0
EXIT_ORPHANS_FOUND = 1
EXIT_SCRIPT_ERROR = 2


@dataclass(frozen=True)
class ForeignKeyCandidate:
    table: str
    column: str
    ref_table: str
    ref_column: str = "id"


FK_CANDIDATES: tuple[ForeignKeyCandidate, ...] = (
    ForeignKeyCandidate("exercises", "created_by_user_id", "users"),
    ForeignKeyCandidate("exercises", "owner_user_id", "users"),
    ForeignKeyCandidate("test_type_definitions", "sport_id", "sports"),
    ForeignKeyCandidate("test_type_definitions", "team_id", "teams"),
    ForeignKeyCandidate(
        "training_plan_template_items",
        "initial_load_test_metric_definition_id",
        "test_metric_definitions",
    ),
    ForeignKeyCandidate("training_plan_templates", "created_by_user_id", "users"),
    ForeignKeyCandidate("training_plan_templates", "owner_user_id", "users"),
    ForeignKeyCandidate("training_plan_templates", "source_template_id", "training_plan_templates"),
    ForeignKeyCandidate("users", "sport_id", "sports"),
)


class CheckError(RuntimeError):
    pass


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _sqlite_path_from_database_url(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise CheckError(f"Only sqlite DATABASE_URL is supported: {database_url}")

    database = url.database
    if not database or database == ":memory:":
        raise CheckError("A file-based sqlite DATABASE_URL is required.")

    db_path = Path(database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    return db_path.resolve()


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise CheckError(f"SQLite database file does not exist: {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    table_sql = _quote_identifier(table_name)
    rows = conn.execute(f"PRAGMA table_info({table_sql})").fetchall()
    return {row["name"] for row in rows}


def _ensure_schema(conn: sqlite3.Connection, candidate: ForeignKeyCandidate) -> None:
    for table_name in (candidate.table, candidate.ref_table):
        if not _table_exists(conn, table_name):
            raise CheckError(f"Required table is missing: {table_name}")

    child_columns = _table_columns(conn, candidate.table)
    if "id" not in child_columns:
        raise CheckError(f"Required id column is missing: {candidate.table}.id")
    if candidate.column not in child_columns:
        raise CheckError(f"Required column is missing: {candidate.table}.{candidate.column}")

    ref_columns = _table_columns(conn, candidate.ref_table)
    if candidate.ref_column not in ref_columns:
        raise CheckError(f"Required reference column is missing: {candidate.ref_table}.{candidate.ref_column}")


def _count_orphans(conn: sqlite3.Connection, candidate: ForeignKeyCandidate) -> int:
    table = _quote_identifier(candidate.table)
    column = _quote_identifier(candidate.column)
    ref_table = _quote_identifier(candidate.ref_table)
    ref_column = _quote_identifier(candidate.ref_column)
    sql = f"""
        SELECT COUNT(*) AS orphan_count
        FROM {table} AS child
        LEFT JOIN {ref_table} AS parent
            ON child.{column} = parent.{ref_column}
        WHERE child.{column} IS NOT NULL
          AND parent.{ref_column} IS NULL
    """
    row = conn.execute(sql).fetchone()
    return int(row["orphan_count"])


def _sample_orphans(conn: sqlite3.Connection, candidate: ForeignKeyCandidate) -> list[sqlite3.Row]:
    table = _quote_identifier(candidate.table)
    column = _quote_identifier(candidate.column)
    ref_table = _quote_identifier(candidate.ref_table)
    ref_column = _quote_identifier(candidate.ref_column)
    sql = f"""
        SELECT child."id" AS row_id, child.{column} AS orphan_value
        FROM {table} AS child
        LEFT JOIN {ref_table} AS parent
            ON child.{column} = parent.{ref_column}
        WHERE child.{column} IS NOT NULL
          AND parent.{ref_column} IS NULL
        ORDER BY child."id"
        LIMIT ?
    """
    return list(conn.execute(sql, (MAX_SAMPLES,)).fetchall())


def main() -> int:
    database_url = get_settings().database_url
    db_path = _sqlite_path_from_database_url(database_url)

    print("[FK_ORPHAN_CHECK] Read-only FK orphan precheck")
    print(f"[FK_ORPHAN_CHECK] Database: {db_path}")

    orphan_total = 0
    with _connect_readonly(db_path) as conn:
        for candidate in FK_CANDIDATES:
            _ensure_schema(conn, candidate)
            orphan_count = _count_orphans(conn, candidate)
            relation = f"{candidate.table}.{candidate.column} -> {candidate.ref_table}.{candidate.ref_column}"

            if orphan_count == 0:
                print(f"[OK] {relation}: ok")
                continue

            orphan_total += orphan_count
            print(f"[ORPHAN] {relation}: {orphan_count}")
            for sample in _sample_orphans(conn, candidate):
                print(
                    f"  sample {candidate.table}.id={sample['row_id']}, "
                    f"{candidate.column}={sample['orphan_value']}"
                )

    if orphan_total:
        print(f"[SUMMARY] Orphan references found: {orphan_total}")
        return EXIT_ORPHANS_FOUND

    print("[SUMMARY] No orphan references found.")
    return EXIT_OK


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as exc:
        print(f"[FK_ORPHAN_CHECK] ERROR: {exc}")
        raise SystemExit(EXIT_SCRIPT_ERROR) from exc
    except sqlite3.Error as exc:
        print(f"[FK_ORPHAN_CHECK] SQLite error: {exc}")
        raise SystemExit(EXIT_SCRIPT_ERROR) from exc
