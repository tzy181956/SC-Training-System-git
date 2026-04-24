from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import Athlete, SetRecord, TrainingSession, TrainingSessionEditLog, TrainingSessionItem, TrainingSyncConflict
from app.services import training_sync_service


def get_training_report(
    db: Session,
    athlete_id: int,
    date_from: date,
    date_to: date,
) -> dict:
    """Aggregate coach-facing training history, trends, and flags for one athlete."""
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="未找到对应运动员。")

    sessions = (
        db.query(TrainingSession)
        .options(
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.exercise),
            joinedload(TrainingSession.items).joinedload(TrainingSessionItem.records),
        )
        .filter(
            TrainingSession.athlete_id == athlete_id,
            TrainingSession.session_date >= date_from,
            TrainingSession.session_date <= date_to,
        )
        .order_by(TrainingSession.session_date.desc(), TrainingSession.id.desc())
        .all()
    )

    edit_logs_by_session = _get_edit_logs_by_session(db, [session.id for session in sessions])
    session_payloads = [_build_session_payload(session, edit_logs_by_session.get(session.id, [])) for session in sessions]
    summary = _build_summary(sessions)
    trend = _build_trends(sessions)
    flags = _build_flags(sessions, athlete.full_name)
    flags.extend(_build_sync_conflict_flags(db, athlete_id, date_from, date_to))
    sync_issues = training_sync_service.list_sync_issues(
        db,
        athlete_id=athlete_id,
        date_from=date_from,
        date_to=date_to,
        issue_status="manual_retry_required",
        limit=6,
    )
    flags.extend(_build_sync_issue_flags(sync_issues))

    return {
        "athlete": athlete,
        "date_range": {"date_from": date_from, "date_to": date_to},
        "summary": summary,
        "sessions": session_payloads,
        "trend": trend,
        "flags": flags,
        "sync_issues": sync_issues,
    }


def _build_session_payload(session: TrainingSession, edit_logs: list[dict]) -> dict:
    total_items = len(session.items)
    completed_items = sum(1 for item in session.items if item.status == "completed")
    total_sets = sum(item.prescribed_sets for item in session.items)
    completed_sets = sum(len(item.records) for item in session.items)

    items = []
    for item in session.items:
        records = []
        for record in item.records:
            records.append(
                {
                    "id": record.id,
                    "set_number": record.set_number,
                    "target_weight": record.target_weight,
                    "target_reps": record.target_reps,
                    "actual_weight": record.actual_weight,
                    "actual_reps": record.actual_reps,
                    "actual_rir": record.actual_rir,
                    "suggestion_weight": record.suggestion_weight,
                    "suggestion_reason": record.suggestion_reason,
                    "user_decision": record.user_decision,
                    "final_weight": record.final_weight,
                    "completed_at": record.completed_at,
                    "notes": record.notes,
                    "adjustment_type": _resolve_adjustment_type(record),
                }
            )

        items.append(
            {
                "id": item.id,
                "exercise_name": item.exercise.name if item.exercise else "未命名动作",
                "sort_order": item.sort_order,
                "prescribed_sets": item.prescribed_sets,
                "prescribed_reps": item.prescribed_reps,
                "completed_sets": len(item.records),
                "target_note": item.target_note,
                "is_main_lift": item.is_main_lift,
                "status": item.status,
                "records": records,
            }
        )

    return {
        "id": session.id,
        "session_date": session.session_date,
        "template_name": getattr(getattr(session, "template", None), "name", None) or f"计划 {session.template_id}",
        "status": _format_training_session_status(session.status),
        "completed_items": completed_items,
        "total_items": total_items,
        "completed_sets": completed_sets,
        "total_sets": total_sets,
        "items": items,
        "edit_logs": edit_logs,
    }


def _get_edit_logs_by_session(db: Session, session_ids: list[int]) -> dict[int, list[dict]]:
    if not session_ids:
        return {}

    logs = (
        db.query(TrainingSessionEditLog)
        .filter(TrainingSessionEditLog.session_id.in_(session_ids))
        .order_by(TrainingSessionEditLog.created_at.desc(), TrainingSessionEditLog.id.desc())
        .all()
    )

    grouped: dict[int, list[dict]] = defaultdict(list)
    for log in logs:
        grouped[log.session_id].append(
            {
                "id": log.id,
                "action_type": log.action_type,
                "actor_name": log.actor_name,
                "object_type": log.object_type,
                "object_id": log.object_id,
                "summary": log.summary,
                "created_at": log.created_at,
                "edited_at": log.edited_at,
            }
        )
    return grouped


def _build_summary(sessions: list[TrainingSession]) -> dict:
    total_sessions = len(sessions)
    completed_sessions = sum(1 for session in sessions if session.status == "completed")
    total_items = sum(len(session.items) for session in sessions)
    completed_items = sum(1 for session in sessions for item in session.items if item.status == "completed")
    total_sets = sum(item.prescribed_sets for session in sessions for item in session.items)
    completed_sets = sum(len(item.records) for session in sessions for item in session.items)
    latest_session_date = sessions[0].session_date if sessions else None

    return {
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "completion_rate": round((completed_sets / total_sets) * 100, 1) if total_sets else 0,
        "completed_items": completed_items,
        "total_items": total_items,
        "completed_sets": completed_sets,
        "total_sets": total_sets,
        "latest_session_date": latest_session_date,
    }


def _build_trends(sessions: list[TrainingSession]) -> dict:
    main_lift_points: dict[str, list[dict]] = defaultdict(list)
    completion_trend: list[dict] = []

    chronological_sessions = list(reversed(sessions))
    for session in chronological_sessions:
        session_total_sets = sum(item.prescribed_sets for item in session.items)
        session_completed_sets = sum(len(item.records) for item in session.items)
        completion_trend.append(
            {
                "session_date": session.session_date,
                "template_name": getattr(getattr(session, "template", None), "name", None) or f"计划 {session.template_id}",
                "completion_rate": round((session_completed_sets / session_total_sets) * 100, 1) if session_total_sets else 0,
            }
        )

        for item in session.items:
            if not item.is_main_lift or not item.records:
                continue
            last_record = item.records[-1]
            main_lift_points[item.exercise.name if item.exercise else "主项动作"].append(
                {
                    "session_date": session.session_date,
                    "value": last_record.final_weight,
                }
            )

    return {
        "main_lift_series": [
            {"exercise_name": exercise_name, "points": points}
            for exercise_name, points in main_lift_points.items()
        ],
        "completion_series": completion_trend,
    }


def _build_flags(sessions: list[TrainingSession], athlete_name: str) -> list[dict]:
    flags: list[dict] = []

    for session in sessions:
        if session.status != "completed":
            flags.append(
                {
                    "level": "提醒",
                    "title": f"{session.session_date} 训练未完成",
                    "description": "该次训练仍有动作或组次未完成，建议检查执行进度。",
                }
            )

        for item in session.items:
            exercise_name = item.exercise.name if item.exercise else "当前动作"
            deload_count = 0
            low_rir_streak = 0

            for index, record in enumerate(item.records):
                if index > 0:
                    previous = item.records[index - 1]
                    if previous.suggestion_weight is not None and record.final_weight < previous.suggestion_weight:
                        deload_count += 1

                if record.actual_rir <= 1:
                    low_rir_streak += 1
                else:
                    low_rir_streak = 0

                if low_rir_streak >= 2:
                    flags.append(
                        {
                            "level": "注意",
                            "title": f"{session.session_date} {exercise_name} 连续低 RIR",
                            "description": "同一动作连续两组及以上 RIR 小于等于 1，建议关注疲劳与技术表现。",
                        }
                    )
                    break

            if deload_count >= 2:
                flags.append(
                    {
                        "level": "注意",
                        "title": f"{session.session_date} {exercise_name} 频繁降重",
                        "description": "单次训练内多次低于上一组建议重量，可能需要调整当天训练强度。",
                    }
                )

    if not sessions or sessions[0].session_date < date.today() - timedelta(days=7):
        flags.append(
            {
                "level": "提醒",
                "title": f"{athlete_name} 最近 7 天无训练记录",
                "description": "当前筛选运动员最近 7 天没有训练会话，请确认是否未训练或未录入。",
            }
        )

    return flags


def _build_sync_conflict_flags(db: Session, athlete_id: int, date_from: date, date_to: date) -> list[dict]:
    conflicts = (
        db.query(TrainingSyncConflict)
        .filter(
            TrainingSyncConflict.athlete_id == athlete_id,
            TrainingSyncConflict.session_date >= date_from,
            TrainingSyncConflict.session_date <= date_to,
        )
        .order_by(TrainingSyncConflict.created_at.desc(), TrainingSyncConflict.id.desc())
        .limit(6)
        .all()
    )
    return [
        {
            "level": "注意",
            "title": f"{conflict.session_date} 检测到同步冲突",
            "description": "整堂课兜底同步已按本地草稿覆盖后端，请教练或管理员复核这堂课记录。",
        }
        for conflict in conflicts
    ]


def _build_sync_issue_flags(sync_issues: list[dict]) -> list[dict]:
    return [
        {
            "level": "注意",
            "title": f"{issue['session_date']} 同步异常待处理",
            "description": "该堂训练仍有本地草稿未完成同步，自动重试已停止，需要教练或管理员手动重试。",
        }
        for issue in sync_issues
    ]


def _resolve_adjustment_type(record: SetRecord) -> str:
    if record.user_decision == "accepted":
        return "按建议执行"
    if record.suggestion_weight is not None and record.final_weight == record.suggestion_weight:
        return "按建议调整"
    return "偏离建议调整"


def _format_training_session_status(status: str) -> str:
    if status in {"not_started", "pending"}:
        return "未开始"
    if status == "completed":
        return "已完成"
    if status == "in_progress":
        return "进行中"
    if status == "absent":
        return "缺席"
    if status == "partial_complete":
        return "未完全完成"
    return "未知状态"
