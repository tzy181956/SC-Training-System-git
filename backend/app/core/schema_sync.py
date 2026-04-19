from sqlalchemy import text

from app.core.database import engine


def ensure_runtime_schema() -> None:
    statements = [
        "ALTER TABLE athletes ADD COLUMN height FLOAT",
        "ALTER TABLE athletes ADD COLUMN weight FLOAT",
        "ALTER TABLE athletes ADD COLUMN body_fat_percentage FLOAT",
        "ALTER TABLE athletes ADD COLUMN wingspan FLOAT",
        "ALTER TABLE athletes ADD COLUMN standing_reach FLOAT",
        "ALTER TABLE test_records ADD COLUMN result_text VARCHAR(80)",
    ]

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception as exc:  # sqlite duplicate-column path
                message = str(exc).lower()
                if "duplicate column" in message or "already exists" in message:
                    continue
                raise
