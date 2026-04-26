from __future__ import annotations

import hashlib
import json
from typing import Any


NOT_STARTED_SESSION_STATUS = "not_started"
IN_PROGRESS_SESSION_STATUS = "in_progress"
FINAL_SESSION_STATUSES = {"completed", "absent", "partial_complete"}


def resolve_session_item_status(record_count: int, prescribed_sets: int) -> str:
    if record_count <= 0:
        return "pending"
    if record_count >= prescribed_sets:
        return "completed"
    return IN_PROGRESS_SESSION_STATUS


def resolve_session_status(
    *,
    has_items: bool,
    total_records: int,
    all_items_completed: bool,
    is_final_context: bool,
) -> str:
    if not has_items or total_records == 0:
        return "absent" if is_final_context else NOT_STARTED_SESSION_STATUS
    if all_items_completed:
        return "completed"
    if is_final_context:
        return "partial_complete"
    return IN_PROGRESS_SESSION_STATUS


def resolve_finalized_session_status(*, total_records: int, all_items_completed: bool, closure_reason: str) -> str:
    if all_items_completed:
        return "completed"
    if closure_reason == "midnight_cutoff" and total_records == 0:
        return "absent"
    return "partial_complete"


def serialize_session_snapshot(session: Any) -> dict:
    return {
        "athlete_id": session.athlete_id,
        "assignment_id": session.assignment_id,
        "template_id": session.template_id,
        "session_date": session.session_date.isoformat(),
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "items": _serialize_session_items(session.items),
    }


def serialize_full_sync_payload(payload: Any) -> dict:
    return {
        "athlete_id": payload.athlete_id,
        "assignment_id": payload.assignment_id,
        "template_id": payload.template_id,
        "session_date": payload.session_date.isoformat(),
        "status": payload.status,
        "started_at": payload.started_at.isoformat() if payload.started_at else None,
        "completed_at": payload.completed_at.isoformat() if payload.completed_at else None,
        "items": _serialize_session_items(payload.items),
    }


def build_snapshot_signature(snapshot: dict) -> str:
    normalized = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _serialize_session_items(items: Any) -> list[dict]:
    return [
        {
            "template_item_id": item.template_item_id,
            "exercise_id": item.exercise_id,
            "sort_order": item.sort_order,
            "prescribed_sets": item.prescribed_sets,
            "prescribed_reps": item.prescribed_reps,
            "target_note": item.target_note,
            "is_main_lift": item.is_main_lift,
            "enable_auto_load": item.enable_auto_load,
            "status": item.status,
            "initial_load": item.initial_load,
            "records": [
                {
                    "set_number": record.set_number,
                    "actual_weight": record.actual_weight,
                    "actual_reps": record.actual_reps,
                    "actual_rir": record.actual_rir,
                    "final_weight": record.final_weight,
                    "notes": record.notes,
                    "completed_at": record.completed_at.isoformat(),
                }
                for record in sorted(item.records, key=lambda current: current.set_number)
            ],
        }
        for item in sorted(items, key=lambda current: (current.sort_order, current.template_item_id))
    ]
