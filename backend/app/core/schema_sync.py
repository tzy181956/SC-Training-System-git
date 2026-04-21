from sqlalchemy import text

from app.core.database import engine


def ensure_runtime_schema() -> None:
    statements = [
        "ALTER TABLE athletes ADD COLUMN gender VARCHAR(20)",
        "ALTER TABLE exercises ADD COLUMN code VARCHAR(64)",
        "ALTER TABLE exercises ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'custom_manual'",
        "ALTER TABLE exercises ADD COLUMN name_en VARCHAR(160)",
        "ALTER TABLE exercises ADD COLUMN level1_category VARCHAR(120)",
        "ALTER TABLE exercises ADD COLUMN level2_category VARCHAR(160)",
        "ALTER TABLE exercises ADD COLUMN base_movement VARCHAR(160)",
        "ALTER TABLE exercises ADD COLUMN category_path VARCHAR(255)",
        "ALTER TABLE exercises ADD COLUMN original_english_fields JSON",
        "ALTER TABLE exercises ADD COLUMN structured_tags JSON",
        "ALTER TABLE exercises ADD COLUMN search_keywords JSON",
        "ALTER TABLE exercises ADD COLUMN tag_text TEXT",
        "ALTER TABLE exercises ADD COLUMN raw_row JSON",
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

        athlete_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(athletes)")).fetchall()
        }
        if "training_level" in athlete_columns:
            connection.execute(text("ALTER TABLE athletes DROP COLUMN training_level"))

        connection.execute(
            text("UPDATE exercises SET structured_tags = '{}' WHERE structured_tags IS NULL")
        )
        connection.execute(
            text("UPDATE exercises SET search_keywords = '[]' WHERE search_keywords IS NULL")
        )

        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_exercises_code_unique ON exercises(code)")
        )
