from __future__ import annotations

import os
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
TEST_SESSION_DATE = date(2099, 1, 2)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="monitoring-smoke-") as temp_dir_text:
        temp_db = Path(temp_dir_text) / "monitoring-smoke.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.as_posix()}"

        if str(BACKEND_ROOT) not in sys.path:
            sys.path.insert(0, str(BACKEND_ROOT))

        from app.core.database import Base, SessionLocal, engine
        from app.models import (
            Athlete,
            AthletePlanAssignment,
            Exercise,
            SetRecord,
            Sport,
            Team,
            TrainingPlanTemplate,
            TrainingPlanTemplateItem,
            TrainingSession,
            TrainingSessionItem,
            TrainingSyncIssue,
        )
        from app.schemas.monitoring import MonitoringAthleteDetailRead, MonitoringTodayRead
        from app.services import monitoring_service

        Base.metadata.create_all(bind=engine)
        completed_at_base = datetime(2099, 1, 2, 9, 0, tzinfo=timezone.utc)
        reference_time = datetime(2099, 1, 2, 9, 45, tzinfo=timezone.utc)

        def create_template(
            db,
            exercise: Exercise,
            name: str,
            prescribed_sets: tuple[int, int] = (2, 1),
        ) -> TrainingPlanTemplate:
            template = TrainingPlanTemplate(name=name, description="monitoring smoke template", is_active=True)
            for index, set_count in enumerate(prescribed_sets, start=1):
                template.items.append(
                    TrainingPlanTemplateItem(
                        exercise_id=exercise.id,
                        sort_order=index,
                        prescribed_sets=set_count,
                        prescribed_reps=5,
                        target_note=None,
                        is_main_lift=index == 1,
                        enable_auto_load=False,
                        initial_load_mode="fixed_weight",
                        initial_load_value=20.0 + index,
                    )
                )
            db.add(template)
            db.flush()
            return template

        def create_athlete(db, team: Team, name: str) -> Athlete:
            athlete = Athlete(code=f"TMP-SMOKE-{abs(hash(name))}", full_name=name, team_id=team.id, is_active=True)
            db.add(athlete)
            db.flush()
            athlete.code = f"ATH-SMOKE-{athlete.id:04d}"
            return athlete

        def create_assignment(db, athlete: Athlete, template: TrainingPlanTemplate) -> AthletePlanAssignment:
            assignment = AthletePlanAssignment(
                athlete_id=athlete.id,
                template_id=template.id,
                assigned_date=TEST_SESSION_DATE,
                start_date=TEST_SESSION_DATE,
                end_date=TEST_SESSION_DATE,
                status="active",
            )
            db.add(assignment)
            db.flush()
            return assignment

        def create_session(
            db,
            assignment: AthletePlanAssignment,
            status: str,
            records_by_item: tuple[int, ...],
            record_time_base: datetime | None = None,
            rir_by_item: tuple[int, ...] | None = None,
        ) -> TrainingSession:
            first_record_time = record_time_base or completed_at_base + timedelta(minutes=assignment.id * 10)
            session = TrainingSession(
                athlete_id=assignment.athlete_id,
                assignment_id=assignment.id,
                template_id=assignment.template_id,
                session_date=TEST_SESSION_DATE,
                status=status,
                started_at=first_record_time if sum(records_by_item) else None,
                completed_at=first_record_time if status in {"completed", "partial_complete", "absent"} else None,
            )
            db.add(session)
            db.flush()

            for item_index, template_item in enumerate(assignment.template.items):
                record_count = records_by_item[item_index] if item_index < len(records_by_item) else 0
                session_item = TrainingSessionItem(
                    session_id=session.id,
                    template_item_id=template_item.id,
                    exercise_id=template_item.exercise_id,
                    sort_order=template_item.sort_order,
                    prescribed_sets=template_item.prescribed_sets,
                    prescribed_reps=template_item.prescribed_reps,
                    target_note=template_item.target_note,
                    is_main_lift=template_item.is_main_lift,
                    enable_auto_load=template_item.enable_auto_load,
                    initial_load=template_item.initial_load_value,
                    status="completed" if record_count >= template_item.prescribed_sets else "in_progress" if record_count else "pending",
                )
                db.add(session_item)
                db.flush()

                for record_index in range(record_count):
                    record_time = first_record_time + timedelta(minutes=item_index * 3 + record_index)
                    actual_rir = rir_by_item[item_index] if rir_by_item and item_index < len(rir_by_item) else 2
                    session_item.records.append(
                        SetRecord(
                            set_number=record_index + 1,
                            target_weight=session_item.initial_load,
                            target_reps=session_item.prescribed_reps,
                            actual_weight=30.0 + assignment.id + item_index,
                            actual_reps=5 + record_index,
                            actual_rir=actual_rir,
                            suggestion_weight=None,
                            suggestion_reason=None,
                            user_decision="accepted",
                            final_weight=30.0 + assignment.id + item_index,
                            completed_at=record_time,
                            notes=f"monitoring-smoke-{assignment.id}-{item_index}-{record_index}",
                        )
                    )

            db.flush()
            return session

        with SessionLocal() as db:
            sport = Sport(name="Monitoring Smoke Sport", code="monitoring_smoke", notes=None)
            db.add(sport)
            db.flush()
            team = Team(sport_id=sport.id, name="Monitoring Smoke Team", code="monitoring_smoke", notes=None)
            db.add(team)
            exercise = Exercise(name="Monitoring Smoke Squat", code="monitoring_smoke_squat")
            db.add(exercise)
            db.flush()

            template = create_template(db, exercise, "Monitoring Smoke Template")
            secondary_template = create_template(db, exercise, "Monitoring Smoke Secondary Template")

            no_plan = create_athlete(db, team, "Smoke 01 No Plan")
            not_started = create_athlete(db, team, "Smoke 02 Not Started")
            in_progress = create_athlete(db, team, "Smoke 03 In Progress")
            completed = create_athlete(db, team, "Smoke 04 Completed")
            partial = create_athlete(db, team, "Smoke 05 Partial Complete")
            absent = create_athlete(db, team, "Smoke 06 Absent")
            retry = create_athlete(db, team, "Smoke 07 Manual Retry Required")
            pending_sync = create_athlete(db, team, "Smoke 08 Pending Sync")
            low_rir = create_athlete(db, team, "Smoke 09 Low RIR")
            high_main_rir = create_athlete(db, team, "Smoke 10 High Main RIR")
            over_sets = create_athlete(db, team, "Smoke 11 Over Sets")
            multi_plan = create_athlete(db, team, "Smoke 12 Multi Plan")

            create_assignment(db, not_started, template)

            in_progress_assignment = create_assignment(db, in_progress, template)
            create_session(
                db,
                in_progress_assignment,
                "in_progress",
                (1, 0),
                record_time_base=completed_at_base + timedelta(minutes=5),
            )

            completed_assignment = create_assignment(db, completed, template)
            completed_session = create_session(
                db,
                completed_assignment,
                "completed",
                (2, 1),
                record_time_base=completed_at_base + timedelta(minutes=20),
            )

            partial_assignment = create_assignment(db, partial, template)
            create_session(
                db,
                partial_assignment,
                "partial_complete",
                (1, 0),
                record_time_base=completed_at_base + timedelta(minutes=15),
            )

            absent_assignment = create_assignment(db, absent, template)
            create_session(db, absent_assignment, "absent", (0, 0))

            retry_assignment = create_assignment(db, retry, template)
            retry_session = create_session(
                db,
                retry_assignment,
                "in_progress",
                (1, 0),
                record_time_base=completed_at_base + timedelta(minutes=30),
            )
            db.add(
                TrainingSyncIssue(
                    athlete_id=retry.id,
                    assignment_id=retry_assignment.id,
                    session_id=retry_session.id,
                    session_date=TEST_SESSION_DATE,
                    session_key=f"monitoring-smoke:{retry.id}:{TEST_SESSION_DATE.isoformat()}",
                    issue_status="manual_retry_required",
                    summary="Monitoring smoke sync issue.",
                    failure_count=3,
                    last_error="smoke-check-offline",
                    sync_payload={"source": "monitoring_smoke_check"},
                )
            )

            pending_assignment = create_assignment(db, pending_sync, template)
            pending_session = create_session(
                db,
                pending_assignment,
                "in_progress",
                (1, 0),
                record_time_base=completed_at_base + timedelta(minutes=35),
            )
            db.add(
                TrainingSyncIssue(
                    athlete_id=pending_sync.id,
                    assignment_id=pending_assignment.id,
                    session_id=pending_session.id,
                    session_date=TEST_SESSION_DATE,
                    session_key=f"monitoring-smoke:{pending_sync.id}:{TEST_SESSION_DATE.isoformat()}",
                    issue_status="pending",
                    summary="Monitoring smoke pending sync issue.",
                    failure_count=1,
                    last_error=None,
                    sync_payload={"source": "monitoring_smoke_check"},
                )
            )

            low_rir_assignment = create_assignment(db, low_rir, template)
            create_session(
                db,
                low_rir_assignment,
                "in_progress",
                (1, 0),
                record_time_base=completed_at_base + timedelta(minutes=40),
                rir_by_item=(0, 2),
            )

            high_main_rir_assignment = create_assignment(db, high_main_rir, template)
            create_session(
                db,
                high_main_rir_assignment,
                "in_progress",
                (1, 0),
                record_time_base=completed_at_base + timedelta(minutes=41),
                rir_by_item=(4, 2),
            )

            over_sets_assignment = create_assignment(db, over_sets, template)
            create_session(
                db,
                over_sets_assignment,
                "completed",
                (3, 1),
                record_time_base=completed_at_base + timedelta(minutes=42),
            )

            multi_completed_assignment = create_assignment(db, multi_plan, template)
            create_session(
                db,
                multi_completed_assignment,
                "completed",
                (2, 1),
                record_time_base=completed_at_base + timedelta(minutes=25),
            )
            create_assignment(db, multi_plan, secondary_template)

            db.commit()

            payload = monitoring_service.get_today_monitoring(db, TEST_SESSION_DATE, reference_time=reference_time)
            MonitoringTodayRead.model_validate(payload)
            athletes = {athlete["athlete_name"]: athlete for athlete in payload["athletes"]}
            require(no_plan.full_name in athletes, "No-plan athlete missing from monitoring payload")

            expected_status_by_name = {
                no_plan.full_name: "no_plan",
                not_started.full_name: "not_started",
                in_progress.full_name: "in_progress",
                completed.full_name: "completed",
                partial.full_name: "partial_complete",
                absent.full_name: "absent",
                retry.full_name: "in_progress",
                pending_sync.full_name: "in_progress",
                low_rir.full_name: "in_progress",
                high_main_rir.full_name: "in_progress",
                over_sets.full_name: "completed",
                multi_plan.full_name: "in_progress",
            }
            for name, expected_status in expected_status_by_name.items():
                actual_status = athletes[name]["session_status"]
                require(actual_status == expected_status, f"{name} status expected {expected_status}, got {actual_status}")

            status_counts = Counter(athlete["session_status"] for athlete in payload["athletes"])
            require(status_counts["no_plan"] == 1, f"Expected 1 no_plan athlete, got {status_counts['no_plan']}")
            require(status_counts["not_started"] == 1, f"Expected 1 not_started athlete, got {status_counts['not_started']}")
            require(status_counts["in_progress"] == 6, f"Expected 6 in_progress athletes, got {status_counts['in_progress']}")
            require(status_counts["completed"] == 2, f"Expected 2 completed athletes, got {status_counts['completed']}")
            require(status_counts["partial_complete"] == 1, f"Expected 1 partial_complete athlete, got {status_counts['partial_complete']}")
            require(status_counts["absent"] == 1, f"Expected 1 absent athlete, got {status_counts['absent']}")

            require(athletes[retry.full_name]["sync_status"] == "manual_retry_required", "Manual retry sync status missing")
            require(athletes[pending_sync.full_name]["sync_status"] == "pending", "Pending sync status missing")
            require(athletes[in_progress.full_name]["sync_status"] == "synced", "Normal in-progress sync status should be synced")

            require(athletes[no_plan.full_name]["alert_level"] == "none", "No-plan athlete should not have alert")
            require(athletes[retry.full_name]["alert_level"] == "critical", "Manual retry should be critical")
            require("同步异常待处理" in athletes[retry.full_name]["alert_reasons"], "Manual retry alert reason missing")
            require(athletes[pending_sync.full_name]["alert_level"] == "warning", "Pending sync should be warning")
            require("本地数据待同步" in athletes[pending_sync.full_name]["alert_reasons"], "Pending sync alert reason missing")
            require(athletes[partial.full_name]["alert_level"] == "warning", "Partial complete should be warning")
            require("已结束未完成" in athletes[partial.full_name]["alert_reasons"], "Partial complete alert reason missing")
            require(athletes[absent.full_name]["alert_level"] == "warning", "Absent should be warning")
            require("缺席" in athletes[absent.full_name]["alert_reasons"], "Absent alert reason missing")
            require(athletes[not_started.full_name]["alert_level"] == "warning", "Timed-out not-started should be warning")
            require("超过训练开始后 30 分钟仍未开始" in athletes[not_started.full_name]["alert_reasons"], "Not-started timeout alert reason missing")
            require(athletes[in_progress.full_name]["alert_level"] == "warning", "Stale in-progress should be warning")
            require("最近一组距离当前时间超过 20 分钟" in athletes[in_progress.full_name]["alert_reasons"], "Stale in-progress alert reason missing")
            require(athletes[low_rir.full_name]["alert_level"] == "warning", "Low RIR should be warning")
            require("最近一组 RIR <= 0" in athletes[low_rir.full_name]["alert_reasons"], "Low RIR alert reason missing")
            require(athletes[high_main_rir.full_name]["alert_level"] == "info", "High main RIR should be info")
            require("主项最近一组 RIR >= 4" in athletes[high_main_rir.full_name]["alert_reasons"], "High main RIR alert reason missing")
            require(athletes[over_sets.full_name]["alert_level"] == "warning", "Over sets should be warning")
            require("完成组数 > 总组数" in athletes[over_sets.full_name]["alert_reasons"], "Over sets alert reason missing")

            require(athletes[not_started.full_name]["completed_sets"] == 0, "Not-started completed_sets should be 0")
            require(athletes[not_started.full_name]["total_sets"] == 3, "Not-started total_sets should include template targets")
            require(athletes[not_started.full_name]["completed_items"] == 0, "Not-started completed_items should be 0")
            require(athletes[not_started.full_name]["total_items"] == 2, "Not-started total_items should include template items")

            require(athletes[completed.full_name]["completed_sets"] == 3, "Completed completed_sets should equal target")
            require(athletes[completed.full_name]["total_sets"] == 3, "Completed total_sets should be 3")
            require(athletes[completed.full_name]["completed_items"] == 2, "Completed completed_items should equal total items")
            require(athletes[completed.full_name]["total_items"] == 2, "Completed total_items should be 2")

            require(athletes[multi_plan.full_name]["session_status"] != "completed", "Multi-plan athlete must not be completed")
            require(athletes[multi_plan.full_name]["completed_sets"] == 3, "Multi-plan completed_sets should include finished plan records")
            require(athletes[multi_plan.full_name]["total_sets"] == 6, "Multi-plan total_sets should include both assignments")
            require(athletes[multi_plan.full_name]["completed_items"] == 2, "Multi-plan completed_items should include finished plan items")
            require(athletes[multi_plan.full_name]["total_items"] == 4, "Multi-plan total_items should include both assignment templates")

            latest_set = athletes[completed.full_name]["latest_set"]
            require(latest_set is not None, "Completed athlete latest_set should exist")
            require(latest_set["actual_weight"] == 30.0 + completed_assignment.id + 1, "latest_set actual_weight mismatch")
            require(latest_set["actual_reps"] == 5, "latest_set actual_reps mismatch")
            require(latest_set["actual_rir"] == 2, "latest_set actual_rir mismatch")
            require(latest_set["completed_at"] is not None, "latest_set completed_at should exist")

            no_plan_detail = monitoring_service.get_athlete_monitoring_detail(
                db,
                TEST_SESSION_DATE,
                no_plan.id,
                reference_time=reference_time,
            )
            MonitoringAthleteDetailRead.model_validate(no_plan_detail)
            require(no_plan_detail["session_status"] == "no_plan", "No-plan detail status should be no_plan")
            require(no_plan_detail["assignments"] == [], "No-plan detail assignments should be empty")

            not_started_detail = monitoring_service.get_athlete_monitoring_detail(
                db,
                TEST_SESSION_DATE,
                not_started.id,
                reference_time=reference_time,
            )
            MonitoringAthleteDetailRead.model_validate(not_started_detail)
            require(not_started_detail["session_status"] == "not_started", "Not-started detail status mismatch")
            require(not_started_detail["alert_level"] == "warning", "Not-started detail alert_level mismatch")
            require(
                "超过训练开始后 30 分钟仍未开始" in not_started_detail["alert_reasons"],
                "Not-started detail alert reason missing",
            )
            require(len(not_started_detail["assignments"]) == 1, "Not-started detail should include one assignment")
            not_started_assignment_detail = not_started_detail["assignments"][0]
            require(len(not_started_assignment_detail["exercises"]) == 2, "Not-started detail should include template exercises")
            require(not_started_assignment_detail["total_sets"] == 3, "Not-started detail total_sets mismatch")
            require(all(not exercise["records"] for exercise in not_started_assignment_detail["exercises"]), "Not-started detail records should be empty")

            completed_detail = monitoring_service.get_athlete_monitoring_detail(
                db,
                TEST_SESSION_DATE,
                completed.id,
                reference_time=reference_time,
            )
            MonitoringAthleteDetailRead.model_validate(completed_detail)
            completed_assignment_detail = completed_detail["assignments"][0]
            require(completed_assignment_detail["session_status"] == "completed", "Completed detail assignment status mismatch")
            require([len(exercise["records"]) for exercise in completed_assignment_detail["exercises"]] == [2, 1], "Completed detail record counts mismatch")
            first_completed_record = completed_assignment_detail["exercises"][0]["records"][0]
            require(first_completed_record["actual_weight"] == 30.0 + completed_assignment.id, "Completed detail actual_weight mismatch")
            require(first_completed_record["actual_reps"] == 5, "Completed detail actual_reps mismatch")
            require(first_completed_record["actual_rir"] == 2, "Completed detail actual_rir mismatch")

            in_progress_detail = monitoring_service.get_athlete_monitoring_detail(
                db,
                TEST_SESSION_DATE,
                in_progress.id,
                reference_time=reference_time,
            )
            MonitoringAthleteDetailRead.model_validate(in_progress_detail)
            in_progress_assignment_detail = in_progress_detail["assignments"][0]
            require(in_progress_assignment_detail["completed_sets"] == 1, "In-progress detail completed_sets mismatch")
            require(in_progress_assignment_detail["completed_sets"] < in_progress_assignment_detail["total_sets"], "In-progress detail should be incomplete")
            require(len(in_progress_assignment_detail["exercises"][0]["records"]) == 1, "In-progress first exercise should include one record")
            require(len(in_progress_assignment_detail["exercises"][1]["records"]) == 0, "In-progress second exercise should have no records")

            multi_plan_detail = monitoring_service.get_athlete_monitoring_detail(
                db,
                TEST_SESSION_DATE,
                multi_plan.id,
                reference_time=reference_time,
            )
            MonitoringAthleteDetailRead.model_validate(multi_plan_detail)
            require(multi_plan_detail["session_status"] != "completed", "Multi-plan detail must not be completed")
            require(len(multi_plan_detail["assignments"]) == 2, "Multi-plan detail should include two assignments")
            require(any(assignment["session_id"] is None for assignment in multi_plan_detail["assignments"]), "Multi-plan detail should include not-started assignment")
            require(any(assignment["session_status"] == "completed" for assignment in multi_plan_detail["assignments"]), "Multi-plan detail should include completed assignment")

            retry_detail = monitoring_service.get_athlete_monitoring_detail(
                db,
                TEST_SESSION_DATE,
                retry.id,
                reference_time=reference_time,
            )
            MonitoringAthleteDetailRead.model_validate(retry_detail)
            require(retry_detail["sync_status"] == "manual_retry_required", "Retry detail sync_status mismatch")
            require(retry_detail["alert_level"] == "critical", "Retry detail alert_level mismatch")
            require("同步异常待处理" in retry_detail["alert_reasons"], "Retry detail alert reason missing")
            require(retry_detail["has_alert"] is True, "Retry detail should have alert")

            print("[CHECK] monitoring schema validation passed")
            print("[CHECK] monitoring status distribution passed")
            print("[CHECK] monitoring totals, latest_set and sync_status passed")
            print("[CHECK] monitoring alert levels and reasons passed")
            print("[CHECK] monitoring athlete detail smoke passed")

        engine.dispose()

    print("[OK] monitoring smoke check passed")


if __name__ == "__main__":
    main()
