from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.database import Base
from app.models import *  # noqa: F401,F403


BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_EXE = BACKEND_DIR / ".venv" / "Scripts" / "alembic.exe"


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


def _backup_database(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}.migration-backup-{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _run_alembic(*args: str) -> None:
    if not ALEMBIC_EXE.exists():
        raise RuntimeError(f"Alembic executable not found: {ALEMBIC_EXE}")
    command = [str(ALEMBIC_EXE), "-c", str(ALEMBIC_INI), *args]
    subprocess.run(command, cwd=BACKEND_DIR, check=True)


def bootstrap_database() -> None:
    settings = get_settings()
    db_path = _require_sqlite_path(settings.database_url)
    backup_path = _backup_database(db_path)
    if backup_path:
        print(f"[MIGRATION] Backup created: {backup_path}")

    has_alembic = _has_table(db_path, "alembic_version")
    has_schema = _has_existing_app_schema(db_path)

    if has_alembic:
        print("[MIGRATION] Existing alembic version table detected. Running upgrade head.")
        _run_alembic("upgrade", "head")
        return

    if has_schema:
        print("[MIGRATION] Existing application schema detected without alembic_version. Stamping baseline head.")
        _run_alembic("stamp", "head")
        return

    print("[MIGRATION] No existing schema detected. Running upgrade head.")
    _run_alembic("upgrade", "head")


def main() -> None:
    parser = argparse.ArgumentParser(description="Database migration helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Backup database, then stamp or upgrade to head.")

    upgrade_parser = subparsers.add_parser("upgrade", help="Run alembic upgrade.")
    upgrade_parser.add_argument("revision", nargs="?", default="head")

    stamp_parser = subparsers.add_parser("stamp", help="Run alembic stamp.")
    stamp_parser.add_argument("revision", nargs="?", default="head")

    subparsers.add_parser("current", help="Show current alembic revision.")

    args = parser.parse_args()

    if args.command == "bootstrap":
        bootstrap_database()
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
