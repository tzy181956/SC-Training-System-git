from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


settings = get_settings()
database_url = make_url(settings.database_url)
is_sqlite_database = database_url.get_backend_name() == "sqlite"
sqlite_database_name = database_url.database or ""


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if is_sqlite_database else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


if is_sqlite_database:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        if sqlite_database_name != ":memory:":
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
