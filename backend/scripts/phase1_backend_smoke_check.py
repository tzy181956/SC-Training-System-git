from __future__ import annotations

import gc
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
SOURCE_DB = BACKEND_ROOT / "training.db"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resolve_smoke_session_date(assignment) -> date:
    repeat_weekdays = getattr(assignment, "repeat_weekdays", None) or [1, 2, 3, 4, 5, 6, 7]
    valid_weekdays = {int(day) for day in repeat_weekdays if 1 <= int(day) <= 7}
    current_date = assignment.start_date
    while current_date <= assignment.end_date:
        if current_date.isoweekday() in valid_weekdays:
            return current_date
        current_date += timedelta(days=1)
    raise AssertionError(f"Assignment {assignment.id} has no scheduled date within its active window")


def build_full_sync_payload(session, payload_cls, item_cls, record_cls, *, status: str, last_server_signature: str | None, trigger_reason: str, note_suffix: str):
    items = []
    for item_index, item in enumerate(sorted(session.items, key=lambda current: (current.sort_order, current.template_item_id))):
        records = []
        for record_index, record in enumerate(sorted(item.records, key=lambda current: current.set_number)):
            next_notes = record.notes
            if item_index == 0 and record_index == 0:
                base_notes = next_notes or ""
                next_notes = f"{base_notes}{note_suffix}"
            records.append(
                record_cls(
                    set_number=record.set_number,
                    actual_weight=record.actual_weight,
                    actual_reps=record.actual_reps,
                    actual_rir=record.actual_rir,
                    final_weight=record.final_weight,
                    notes=next_notes,
                    completed_at=record.completed_at,
                )
            )

        items.append(
            item_cls(
                template_item_id=item.template_item_id,
                exercise_id=item.exercise_id,
                sort_order=item.sort_order,
                prescribed_sets=item.prescribed_sets,
                prescribed_reps=item.prescribed_reps,
                target_note=item.target_note,
                is_main_lift=item.is_main_lift,
                enable_auto_load=item.enable_auto_load,
                status=item.status,
                initial_load=item.initial_load,
                records=records,
            )
        )

    return payload_cls(
        assignment_id=session.assignment_id,
        athlete_id=session.athlete_id,
        template_id=session.template_id,
        session_date=session.session_date,
        session_id=session.id,
        status=status,
        started_at=session.started_at,
        completed_at=(datetime.now(timezone.utc) if status in {"completed", "absent", "partial_complete"} else None),
        last_server_updated_at=session.updated_at,
        last_server_signature=last_server_signature,
        trigger_reason=trigger_reason,
        items=items,
    )


def main() -> None:
    require(SOURCE_DB.exists(), f"Source database not found: {SOURCE_DB}")

    with tempfile.TemporaryDirectory(prefix="phase1-backend-smoke-") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        temp_db = temp_dir / "training-smoke.db"
        temp_backup_dir = temp_dir / "backups"
        shutil.copy2(SOURCE_DB, temp_db)

        os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.as_posix()}"
        if str(BACKEND_ROOT) not in sys.path:
            sys.path.insert(0, str(BACKEND_ROOT))
        venv_site_packages = BACKEND_ROOT / ".venv" / "Lib" / "site-packages"
        if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
            sys.path.append(str(venv_site_packages))

        from app.core.database import SessionLocal, engine
        from app.core.schema_sync import ensure_runtime_schema
        from app.models import Athlete, AthletePlanAssignment, TrainingSyncConflict
        from app.schemas.training_session import (
            SessionFullSyncItem,
            SessionFullSyncPayload,
            SessionFullSyncRecord,
            SessionSetSyncOperation,
            TrainingSyncIssueReportPayload,
        )
        from app.services import backup_service, session_service, training_sync_service

        try:
            ensure_runtime_schema()

            print("[CHECK] backend smoke setup ready")

            athlete_id = None
            original_athlete_name = None
            test_session_date = None

            with SessionLocal() as db:
                assignments = db.query(AthletePlanAssignment).all()
                target_assignment = next(
                    (
                        assignment
                        for assignment in assignments
                        if assignment.status == "active"
                        and assignment.template
                        and assignment.template.items
                    ),
                    None,
                )
                require(target_assignment is not None, "No active assignment with template items available for smoke test")

                athlete = db.get(Athlete, target_assignment.athlete_id)
                require(athlete is not None, "Assignment athlete not found")
                athlete_id = athlete.id
                original_athlete_name = athlete.full_name
                test_session_date = resolve_smoke_session_date(target_assignment)

                preview_session = session_service.open_session_for_assignment(db, target_assignment.id, test_session_date)
                require(isinstance(preview_session, dict), "Training preview should return a local preview snapshot")
                require(preview_session["id"] is None, "Preview should not create a live session before the first set")
                require(preview_session["status"] == "not_started", "Preview session should stay not_started")
                require(bool(preview_session["items"]), "Preview session should contain training items")

                first_preview_item = preview_session["items"][0]
                set_operation = SessionSetSyncOperation(
                    operation_type="create_set",
                    assignment_id=target_assignment.id,
                    session_date=test_session_date,
                    template_item_id=first_preview_item["template_item_id"],
                    session_item_id=None,
                    session_id=None,
                    local_record_id=1,
                    actual_weight=20.0,
                    actual_reps=5,
                    actual_rir=2,
                    final_weight=20.0,
                    notes="phase1-smoke-create-set",
                )
                _, _, _, started_session = session_service.sync_session_operation(db, set_operation)
                require(started_session.id is not None, "First set should create or confirm a live session")
                require(started_session.status == "in_progress", "First set should move session into in_progress")
                print("[CHECK] incremental sync path created first session")

                live_session = session_service.get_session(db, started_session.id)
                for item in list(live_session.items):
                    session_service.complete_session_item(db, item.id)
                completed_session = session_service.get_session(db, started_session.id)
                require(completed_session.status == "completed", "Completing all items should recompute session to completed")
                require(completed_session.server_signature is not None, "Completed session should expose a server signature baseline")
                print("[CHECK] session status recomputation reached completed")

                conflict_payload = build_full_sync_payload(
                    completed_session,
                    SessionFullSyncPayload,
                    SessionFullSyncItem,
                    SessionFullSyncRecord,
                    status="partial_complete",
                    last_server_signature="stale-signature",
                    trigger_reason="fallback",
                    note_suffix="|fallback-conflict",
                )
                fallback_session, conflict_logged = session_service.sync_session_snapshot(db, conflict_payload)
                require(conflict_logged, "Full-session fallback should log a conflict for stale signature baselines")
                require(fallback_session.status == "partial_complete", "Full-session fallback should overwrite backend status from local draft")
                conflict_count = (
                    db.query(TrainingSyncConflict)
                    .filter(TrainingSyncConflict.session_id == fallback_session.id)
                    .count()
                )
                require(conflict_count >= 1, "Conflict log row should exist after stale-signature full sync")
                print("[CHECK] full-session fallback logged conflict and overwrote backend snapshot")

                retry_base_session = session_service.get_session(db, fallback_session.id)
                retry_payload = build_full_sync_payload(
                    retry_base_session,
                    SessionFullSyncPayload,
                    SessionFullSyncItem,
                    SessionFullSyncRecord,
                    status="completed",
                    last_server_signature=retry_base_session.server_signature,
                    trigger_reason="manual",
                    note_suffix="|manual-retry",
                )
                reported_issue = training_sync_service.report_sync_issue(
                    db,
                    TrainingSyncIssueReportPayload(
                        session_key=f"smoke:{retry_base_session.id}",
                        athlete_id=retry_base_session.athlete_id,
                        assignment_id=retry_base_session.assignment_id,
                        session_id=retry_base_session.id,
                        session_date=retry_base_session.session_date,
                        failure_count=3,
                        summary="Smoke check reported a manual retry required sync issue.",
                        last_error="smoke-check-offline",
                        sync_payload=retry_payload,
                    ),
                )
                require(reported_issue["issue_status"] == "manual_retry_required", "Reported sync issue should enter manual_retry_required")
                listed_issues = training_sync_service.list_sync_issues(
                    db,
                    athlete_id=retry_base_session.athlete_id,
                    date_from=test_session_date,
                    date_to=test_session_date,
                )
                require(any(issue["id"] == reported_issue["id"] for issue in listed_issues), "Reported sync issue should be visible in pending issue list")
                retried_issue, retried_session, retry_conflict_logged = training_sync_service.retry_sync_issue(db, reported_issue["id"])
                require(retried_issue["issue_status"] == "resolved", "Manual retry should resolve the sync issue")
                require(retried_session.status == "completed", "Manual retry should restore the target session state from payload")
                require(retry_conflict_logged is False, "Manual retry with current server signature should not log a new conflict")
                print("[CHECK] sync issue reporting and manual retry path passed")

            engine.dispose()

            backup_result = backup_service.create_backup(
                trigger="manual",
                label="phase1_smoke",
                backup_dir=temp_backup_dir,
                source_db_path=temp_db,
            )
            require(backup_result.backup_path is not None and backup_result.backup_path.exists(), "Backup smoke check did not create a backup file")
            scope_keys = {scope.key for scope in backup_service.list_restore_scopes()}
            require({"full_database", "training_records", "test_records"}.issubset(scope_keys), "Restore scopes are incomplete")

            restore_target_db = temp_dir / "training-restore-target.db"
            shutil.copy2(temp_db, restore_target_db)

            connection = sqlite3.connect(restore_target_db)
            try:
                connection.execute("UPDATE athletes SET full_name = ? WHERE id = ?", ("PHASE1_SMOKE_MUTATION", athlete_id))
                connection.commit()
                changed_name = connection.execute("SELECT full_name FROM athletes WHERE id = ?", (athlete_id,)).fetchone()[0]
            finally:
                connection.close()
                del connection
                gc.collect()
                time.sleep(0.1)
            require(changed_name == "PHASE1_SMOKE_MUTATION", "Database mutation before restore did not apply")
            restore_target_db.unlink()

            backup_service.restore_database_file_from_backup_path(
                source_backup_path=backup_result.backup_path,
                target_db_path=restore_target_db,
            )
            connection = sqlite3.connect(restore_target_db)
            try:
                restored_name = connection.execute("SELECT full_name FROM athletes WHERE id = ?", (athlete_id,)).fetchone()[0]
            finally:
                connection.close()
                del connection
                gc.collect()
            require(restored_name == original_athlete_name, "Restore smoke check did not roll back the mutated database")

            catalog_records = backup_service.list_backup_catalog(backup_dir=temp_backup_dir)
            require(any(record.filename == backup_result.backup_path.name for record in catalog_records), "Backup catalog did not include the smoke backup")
            print("[CHECK] backup and restore smoke path passed")
        finally:
            engine.dispose()

    print("[OK] phase1 backend smoke check passed")


if __name__ == "__main__":
    main()
