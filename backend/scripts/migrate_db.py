from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import get_settings
from app.core.database import Base
from app.models import *  # noqa: F401,F403
from app.services import backup_service

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def _require_sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError(f"Only sqlite database URLs are supported by this helper: {database_url}")
    return Path(database_url.removeprefix(prefix))


def _has_table(db_path: Path, table_name: str) -> bool:
    if not db_path.exists():
        return False
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,),
        ).fetchone()
    return row is not None


def _has_existing_app_schema(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    app_tables = sorted(Base.metadata.tables.keys())
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    existing = {row[0] for row in rows}
    return any(table in existing for table in app_tables)


def _run_alembic(*args: str) -> None:
    command = [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args]
    subprocess.run(command, cwd=BACKEND_DIR, check=True)


def _get_current_revision(db_path: Path) -> str | None:
    if not _has_table(db_path, "alembic_version"):
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    return row[0] if row else None


def _get_head_revision() -> str:
    config = Config(str(ALEMBIC_INI))
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def bootstrap_database() -> None:
    settings = get_settings()
    db_path = _require_sqlite_path(settings.database_url)
    if db_path.exists():
        backup_result = backup_service.create_pre_migration_backup(label="bootstrap")
        if backup_result.backup_path:
            print(f"[MIGRATION] Backup created: {backup_result.backup_path}")

    has_alembic = _has_table(db_path, "alembic_version")
    has_schema = _has_existing_app_schema(db_path)

    if has_alembic:
        print("[MIGRATION] Existing alembic version table detected. Running upgrade head.")
        _run_alembic("upgrade", "head")
        return

    if has_schema:
        print("[MIGRATION] Existing application schema detected without alembic_version. Stamping current head for compatibility.")
        _run_alembic("stamp", "head")
        return

    print("[MIGRATION] No existing schema detected. Running upgrade head.")
    _run_alembic("upgrade", "head")


def ensure_database() -> None:
    settings = get_settings()
    db_path = _require_sqlite_path(settings.database_url)
    head_revision = _get_head_revision()
    current_revision = _get_current_revision(db_path)

    if current_revision == head_revision:
        print(f"[MIGRATION] Database already at head revision {head_revision}.")
        return

    if current_revision is not None:
        backup_result = backup_service.create_pre_migration_backup(label=f"upgrade_from_{current_revision}")
        if backup_result.backup_path:
            print(f"[MIGRATION] Backup created: {backup_result.backup_path}")
        print(f"[MIGRATION] Upgrading database from {current_revision} to {head_revision}.")
        _run_alembic("upgrade", "head")
        return

    print("[MIGRATION] Database is not versioned yet. Running bootstrap flow.")
    bootstrap_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="Database migration helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Backup database, then stamp or upgrade to head.")
    subparsers.add_parser("ensure", help="Upgrade only when database is behind head revision.")

    upgrade_parser = subparsers.add_parser("upgrade", help="Run alembic upgrade.")
    upgrade_parser.add_argument("revision", nargs="?", default="head")

    stamp_parser = subparsers.add_parser("stamp", help="Run alembic stamp.")
    stamp_parser.add_argument("revision", nargs="?", default="head")

    subparsers.add_parser("current", help="Show current alembic revision.")

    args = parser.parse_args()

    if args.command == "bootstrap":
        bootstrap_database()
    elif args.command == "ensure":
        ensure_database()
    elif args.command == "upgrade":
        _run_alembic("upgrade", args.revision)
    elif args.command == "stamp":
        _run_alembic("stamp", args.revision)
    elif args.command == "current":
        _run_alembic("current")
    else:
        raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"[MIGRATION] Alembic command failed with exit code {exc.returncode}")
        raise SystemExit(exc.returncode) from exc
    except Exception as exc:  # noqa: BLE001
        print(f"[MIGRATION] {exc}")
        raise SystemExit(1) from exc
