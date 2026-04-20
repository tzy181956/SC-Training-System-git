from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import Base, engine
from app.core.schema_sync import ensure_runtime_schema
from app.models import *  # noqa: F401,F403
from app.services.exercise_category_service import EXOS_SOURCE_PATH, import_exos_library, preview_exos_import
from sqlalchemy import inspect


def main() -> None:
    parser = ArgumentParser(description="Import EXOS action library into the local database.")
    parser.add_argument("--preview", action="store_true", help="Only show the import summary.")
    parser.add_argument("--apply", action="store_true", help="Apply the import.")
    parser.add_argument("--replace-existing", action="store_true", help="Clear the current action library before import.")
    args = parser.parse_args()

    inspector = inspect(engine)
    if not inspector.has_table("exercise_categories") or not inspector.has_table("exercises"):
        Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()

    if args.preview or not args.apply:
        summary = preview_exos_import(EXOS_SOURCE_PATH)
        print(summary.model_dump_json(indent=2))
        return

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        summary = import_exos_library(db, source_path=EXOS_SOURCE_PATH, replace_existing=args.replace_existing)
        print(summary.model_dump_json(indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
