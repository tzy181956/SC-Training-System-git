from app.core.database import Base, engine
from app.core.schema_sync import ensure_runtime_schema
from app.models import *  # noqa: F401,F403


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    print("Database schema ensured.")


if __name__ == "__main__":
    main()
