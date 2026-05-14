from sqlalchemy import text

from app.core.database import SessionLocal, engine
from app.core.test_definition_defaults import DEFAULT_LOWER_BETTER_TEST_METRIC_CODES
from app.services import exercise_category_service, test_definition_service


def ensure_runtime_schema() -> None:
    template_columns_before: set[str] = set()
    exercise_columns_before: set[str] = set()
    with engine.begin() as connection:
        try:
            template_columns_before = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(training_plan_templates)")).fetchall()
            }
        except Exception:
            template_columns_before = set()
        try:
            exercise_columns_before = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(exercises)")).fetchall()
            }
        except Exception:
            exercise_columns_before = set()

    statements = [
        "ALTER TABLE athletes ADD COLUMN gender VARCHAR(20)",
        "ALTER TABLE exercises ADD COLUMN code VARCHAR(64)",
        "ALTER TABLE exercises ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'custom_manual'",
        "ALTER TABLE exercises ADD COLUMN name_en VARCHAR(160)",
        "ALTER TABLE exercises ADD COLUMN level1_category VARCHAR(120)",
        "ALTER TABLE exercises ADD COLUMN level2_category VARCHAR(160)",
        "ALTER TABLE exercises ADD COLUMN category_path VARCHAR(255)",
        "ALTER TABLE exercises ADD COLUMN original_english_fields JSON",
        "ALTER TABLE exercises ADD COLUMN structured_tags JSON",
        "ALTER TABLE exercises ADD COLUMN search_keywords JSON",
        "ALTER TABLE exercises ADD COLUMN tag_text TEXT",
        "ALTER TABLE exercises ADD COLUMN raw_row JSON",
        "ALTER TABLE exercises ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'public'",
        "ALTER TABLE exercises ADD COLUMN owner_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE exercises ADD COLUMN created_by_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE athletes ADD COLUMN height FLOAT",
        "ALTER TABLE athletes ADD COLUMN weight FLOAT",
        "ALTER TABLE athletes ADD COLUMN body_fat_percentage FLOAT",
        "ALTER TABLE athletes ADD COLUMN wingspan FLOAT",
        "ALTER TABLE athletes ADD COLUMN standing_reach FLOAT",
        "ALTER TABLE athletes ADD COLUMN code VARCHAR(64)",
        "ALTER TABLE training_sessions ADD COLUMN session_rpe INTEGER",
        "ALTER TABLE training_sessions ADD COLUMN session_feedback TEXT",
        "ALTER TABLE training_sessions ADD COLUMN session_duration_minutes INTEGER",
        "ALTER TABLE training_sessions ADD COLUMN session_srpe_load INTEGER",
        "ALTER TABLE training_sessions ADD COLUMN load_metrics_updated_at DATETIME",
        "ALTER TABLE athlete_plan_assignments ADD COLUMN repeat_weekdays JSON",
        "ALTER TABLE test_records ADD COLUMN result_text VARCHAR(80)",
        "ALTER TABLE test_metric_definitions ADD COLUMN is_lower_better BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE set_records ADD COLUMN local_record_id INTEGER",
        "ALTER TABLE training_plan_templates ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private'",
        "ALTER TABLE training_plan_templates ADD COLUMN owner_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE training_plan_templates ADD COLUMN created_by_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE training_plan_templates ADD COLUMN source_template_id INTEGER REFERENCES training_plan_templates(id)",
        "ALTER TABLE users ADD COLUMN sport_id INTEGER REFERENCES sports(id)",
        "ALTER TABLE users ADD COLUMN team_id INTEGER REFERENCES teams(id)",
        "ALTER TABLE test_type_definitions ADD COLUMN sport_id INTEGER REFERENCES sports(id)",
        "ALTER TABLE test_type_definitions ADD COLUMN team_id INTEGER REFERENCES teams(id)",
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
        if "base_category_id" in exercise_columns:
            try:
                connection.execute(text("ALTER TABLE exercises DROP COLUMN base_category_id"))
            except Exception:
                pass
        if "base_movement" in exercise_columns:
            try:
                connection.execute(text("ALTER TABLE exercises DROP COLUMN base_movement"))
            except Exception:
                pass

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
        if "visibility" not in exercise_columns_before:
            connection.execute(
                text(
                    """
                    UPDATE exercises
                    SET visibility = 'public',
                        owner_user_id = NULL,
                        created_by_user_id = NULL
                    """
                )
            )
        connection.execute(
            text(
                "UPDATE athlete_plan_assignments SET repeat_weekdays = '[1,2,3,4,5,6,7]' WHERE repeat_weekdays IS NULL"
            )
        )
        connection.execute(
            text(
                "UPDATE athletes SET code = printf('ATH-%06d', id) "
                "WHERE code IS NULL OR TRIM(code) = ''"
            )
        )

        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_exercises_code_unique ON exercises(code)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_exercises_visibility ON exercises(visibility)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_exercises_owner_user_id ON exercises(owner_user_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_exercises_created_by_user_id ON exercises(created_by_user_id)")
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_athletes_code_unique ON athletes(code)")
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS uq_session_item_local_record_id ON set_records(session_item_id, local_record_id)")
        )
        if "visibility" not in template_columns_before:
            connection.execute(
                text(
                    """
                    UPDATE training_plan_templates
                    SET visibility = 'public',
                        owner_user_id = NULL,
                        created_by_user_id = NULL,
                        source_template_id = NULL
                    """
                )
            )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_training_plan_templates_visibility ON training_plan_templates(visibility)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_training_plan_templates_owner_user_id ON training_plan_templates(owner_user_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_training_plan_templates_source_template_id ON training_plan_templates(source_template_id)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS athlete_daily_training_loads (
                    id INTEGER PRIMARY KEY,
                    athlete_id INTEGER NOT NULL,
                    load_date DATE NOT NULL,
                    session_count INTEGER NOT NULL DEFAULT 0,
                    total_duration_minutes INTEGER NOT NULL DEFAULT 0,
                    total_srpe_load INTEGER NOT NULL DEFAULT 0,
                    source_session_ids JSON,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(athlete_id) REFERENCES athletes(id)
                )
                """
            )
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_athlete_daily_training_loads_athlete_date_unique ON athlete_daily_training_loads(athlete_id, load_date)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_athlete_daily_training_loads_athlete_id ON athlete_daily_training_loads(athlete_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_athlete_daily_training_loads_load_date ON athlete_daily_training_loads(load_date)")
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
            text("CREATE INDEX IF NOT EXISTS ix_users_sport_id ON users(sport_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_team_id ON users(team_id)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS dashboard_memos (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    content TEXT NOT NULL DEFAULT '',
                    source VARCHAR(30) NOT NULL DEFAULT 'dashboard',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_dashboard_memos_user_id ON dashboard_memos(user_id)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_type_definitions (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(80) NOT NULL,
                    code VARCHAR(80) NOT NULL UNIQUE,
                    sport_id INTEGER REFERENCES sports(id),
                    team_id INTEGER REFERENCES teams(id),
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_metric_definitions (
                    id INTEGER PRIMARY KEY,
                    test_type_id INTEGER NOT NULL,
                    name VARCHAR(80) NOT NULL,
                    code VARCHAR(80) NOT NULL,
                    default_unit VARCHAR(30),
                    is_lower_better BOOLEAN NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(test_type_id) REFERENCES test_type_definitions(id)
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_test_type_definitions_id ON test_type_definitions(id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_test_type_definitions_sport_id ON test_type_definitions(sport_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_test_type_definitions_team_id ON test_type_definitions(team_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_test_metric_definitions_id ON test_metric_definitions(id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_test_metric_definitions_test_type_id ON test_metric_definitions(test_type_id)")
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_test_metric_definitions_type_name_unique ON test_metric_definitions(test_type_id, name)")
        )
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_test_metric_definitions_type_code_unique ON test_metric_definitions(test_type_id, code)")
        )

        if DEFAULT_LOWER_BETTER_TEST_METRIC_CODES:
            metric_code_params = {
                f"metric_code_{index}": code for index, code in enumerate(DEFAULT_LOWER_BETTER_TEST_METRIC_CODES)
            }
            metric_code_placeholders = ", ".join(f":metric_code_{index}" for index in range(len(DEFAULT_LOWER_BETTER_TEST_METRIC_CODES)))
            connection.execute(
                text(
                    f"""
                    UPDATE test_metric_definitions
                    SET is_lower_better = 1
                    WHERE code IN ({metric_code_placeholders})
                    """
                ),
                metric_code_params,
            )

    with SessionLocal() as db:
        exercise_category_service.ensure_pending_categories(db)
        test_definition_service.ensure_default_test_definition_catalog(db)
        db.commit()
