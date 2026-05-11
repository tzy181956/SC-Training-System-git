"""Service package exports.

Keep this module free of eager submodule imports.

Several services depend on each other transitively during startup and smoke
checks. Importing every service here turns ``from app.services import x`` into
a package-wide preload and can trigger circular imports before the target
module finishes initializing.
"""

__all__ = [
    "access_control_service",
    "assignment_service",
    "athlete_service",
    "backup_service",
    "content_change_log_service",
    "dangerous_operation_service",
    "exercise_category_service",
    "exercise_service",
    "log_service",
    "monitoring_service",
    "plan_service",
    "score_profile_service",
    "session_service",
    "test_definition_service",
    "test_record_service",
    "training_load_service",
    "training_report_service",
    "user_service",
]
