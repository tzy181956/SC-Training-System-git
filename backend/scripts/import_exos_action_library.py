from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
VENV_SITE_PACKAGES = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

from app.core.database import SessionLocal
from app.core.schema_sync import ensure_runtime_schema
from app.services.exercise_category_service import import_exos_library, preview_exos_import


def main() -> None:
    parser = ArgumentParser(description="Import the EXOS exercise library from the tagged Excel source.")
    parser.add_argument("--preview", action="store_true", help="Show an import preview without writing changes.")
    parser.add_argument("--apply", action="store_true", help="Write the EXOS library into the database.")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Remove stale imported EXOS rows and orphan categories during apply.",
    )
    args = parser.parse_args()

    ensure_runtime_schema()
    db = SessionLocal()
    try:
        if args.preview or not args.apply:
            preview = preview_exos_import(db)
            print(preview.model_dump_json(indent=2))
            return

        result = import_exos_library(db, replace_existing=args.replace_existing)
        print(result.model_dump_json(indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
