from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from app.services import backup_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a manual SQLite backup for Phase 1 checks.")
    parser.add_argument(
        "label",
        nargs="?",
        default="manual",
        help="Optional backup label. Example: phase1_acceptance",
    )
    args = parser.parse_args()

    result = backup_service.create_backup(trigger="manual", label=args.label)
    policy = backup_service.describe_backup_policy()

    if not result.backup_path:
        raise SystemExit("Backup was not created.")

    print(f"[BACKUP] Created: {result.backup_path}")
    print(f"[BACKUP] Directory: {policy['backup_directory']}")
    print(f"[BACKUP] Pattern: {policy['filename_pattern']}")
    if result.deleted_paths:
        print("[BACKUP] Retention deleted:")
        for path in result.deleted_paths:
            print(f" - {path}")


if __name__ == "__main__":
    main()
