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
        "ALTER TABLE users ADD COLUMN team_id INTEGER REFERENCES teams(id)",
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

        exercise_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(exercises)")).fetchall()
        }
        if "load_profile" in exercise_columns:
            connection.execute(text("ALTER TABLE exercises DROP COLUMN load_profile"))

        template_item_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(training_plan_template_items)")).fetchall()
        }
        if "rest_seconds" in template_item_columns:
            connection.execute(text("ALTER TABLE training_plan_template_items DROP COLUMN rest_seconds"))

        connection.execute(
            text("UPDATE exercises SET structured_tags = '{}' WHERE structured_tags IS NULL")
        )
        connection.execute(
            text("UPDATE exercises SET search_keywords = '[]' WHERE search_keywords IS NULL")
        )

        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_exercises_code_unique ON exercises(code)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS dangerous_operation_logs (
                    id INTEGER PRIMARY KEY,
                    operation_key VARCHAR(50) NOT NULL,
                    object_type VARCHAR(50) NOT NULL,
                    object_id INTEGER,
                    actor_name VARCHAR(120) NOT NULL,
                    source VARCHAR(30) NOT NULL DEFAULT 'api',
                    status VARCHAR(20) NOT NULL DEFAULT 'completed',
                    summary TEXT NOT NULL,
                    impact_scope JSON,
                    confirmation_required BOOLEAN NOT NULL DEFAULT 1,
                    confirmation_phrase VARCHAR(80),
                    backup_path VARCHAR(255),
                    extra_data JSON,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_dangerous_operation_logs_operation_key ON dangerous_operation_logs(operation_key)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_dangerous_operation_logs_object_type ON dangerous_operation_logs(object_type)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_dangerous_operation_logs_object_id ON dangerous_operation_logs(object_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_dangerous_operation_logs_status ON dangerous_operation_logs(status)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS training_sync_issues (
                    id INTEGER PRIMARY KEY,
                    athlete_id INTEGER NOT NULL,
                    assignment_id INTEGER,
                    session_id INTEGER,
                    session_date DATE NOT NULL,
                    session_key VARCHAR(160) NOT NULL,
                    issue_status VARCHAR(30) NOT NULL DEFAULT 'manual_retry_required',
                    summary TEXT NOT NULL,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    sync_payload JSON,
                    resolved_at DATETIME,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(athlete_id) REFERENCES athletes(id),
                    FOREIGN KEY(assignment_id) REFERENCES athlete_plan_assignments(id),
                    FOREIGN KEY(session_id) REFERENCES training_sessions(id)
                )
                """
            )
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_training_sync_issues_session_key_unique ON training_sync_issues(session_key)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_training_sync_issues_issue_status ON training_sync_issues(issue_status)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_training_sync_issues_session_date ON training_sync_issues(session_date)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS content_change_logs (
                    id INTEGER PRIMARY KEY,
                    action_type VARCHAR(30) NOT NULL,
                    object_type VARCHAR(50) NOT NULL,
                    object_id INTEGER,
                    object_label VARCHAR(160),
                    actor_name VARCHAR(120) NOT NULL,
                    team_id INTEGER,
                    summary TEXT NOT NULL,
                    before_snapshot JSON,
                    after_snapshot JSON,
                    extra_context JSON,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(team_id) REFERENCES teams(id)
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_content_change_logs_action_type ON content_change_logs(action_type)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_content_change_logs_actor_name ON content_change_logs(actor_name)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_content_change_logs_object_id ON content_change_logs(object_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_content_change_logs_object_type ON content_change_logs(object_type)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_content_change_logs_team_id ON content_change_logs(team_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_team_id ON users(team_id)")
        )
