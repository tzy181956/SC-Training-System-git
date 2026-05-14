from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from app.core.database import SessionLocal
from app.models import AuthEventLog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prune old auth event logs.")
    parser.add_argument("--days", type=int, default=180, help="Keep logs from the last N days. Default: 180.")
    parser.add_argument("--dry-run", action="store_true", help="Show how many rows would be deleted without deleting them.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.days < 1:
        raise SystemExit("--days must be at least 1.")

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    db = SessionLocal()
    try:
        query = db.query(AuthEventLog).filter(AuthEventLog.created_at < cutoff)
        count = query.count()
        if args.dry_run:
            print(f"[AUTH_EVENT_LOGS] Dry run: {count} rows older than {cutoff.isoformat()} would be deleted.")
            return 0

        deleted = query.delete(synchronize_session=False)
        db.commit()
        print(f"[AUTH_EVENT_LOGS] Deleted {deleted} rows older than {cutoff.isoformat()}.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
