from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import not_found
from app.models import Athlete, AthleteDailyTrainingLoad, TrainingSession


def refresh_session_load_metrics(
    db: Session,
    session: TrainingSession,
    *,
    previous_athlete_id: int | None = None,
    previous_load_date: date | None = None,
) -> None:
    duration_minutes, srpe_load = _calculate_session_load_values(session)
    session.session_duration_minutes = duration_minutes
    session.session_srpe_load = srpe_load
    session.load_metrics_updated_at = datetime.now(timezone.utc)
    db.flush()

    refresh_targets = {
        (session.athlete_id, session.session_date),
    }
    if previous_athlete_id is not None and previous_load_date is not None:
        refresh_targets.add((previous_athlete_id, previous_load_date))

    for athlete_id, load_date in refresh_targets:
        if athlete_id is None or load_date is None:
            continue
        _upsert_daily_training_load(db, athlete_id=athlete_id, load_date=load_date)


def get_athlete_training_loads(
    db: Session,
    athlete_id: int,
    date_from: date,
    date_to: date,
) -> dict:
    athlete = db.get(Athlete, athlete_id)
    if not athlete:
        raise not_found("Athlete not found")

    sessions = (
        db.query(TrainingSession)
        .filter(
            TrainingSession.athlete_id == athlete_id,
            TrainingSession.session_date >= date_from,
            TrainingSession.session_date <= date_to,
            TrainingSession.status != "voided",
        )
        .order_by(TrainingSession.session_date.asc(), TrainingSession.id.asc())
        .all()
    )

    return {
        "athlete": athlete,
        "date_range": {"date_from": date_from, "date_to": date_to},
        "sessions": [
            {
                "session_id": session.id,
                "session_date": session.session_date,
                "status": session.status,
                "session_rpe": session.session_rpe,
                "session_duration_minutes": session.session_duration_minutes,
                "session_srpe_load": session.session_srpe_load,
            }
            for session in sessions
        ],
        "daily_loads": _build_daily_load_series(db, athlete_id=athlete_id, date_from=date_from, date_to=date_to),
        "metrics": {
            "formula_status": "pending",
            "acwr": None,
            "monotony": None,
            "strain": None,
        },
    }


def _build_daily_load_series(db: Session, *, athlete_id: int, date_from: date, date_to: date) -> list[dict]:
    rows = (
        db.query(AthleteDailyTrainingLoad)
        .filter(
            AthleteDailyTrainingLoad.athlete_id == athlete_id,
            AthleteDailyTrainingLoad.load_date >= date_from,
            AthleteDailyTrainingLoad.load_date <= date_to,
        )
        .order_by(AthleteDailyTrainingLoad.load_date.asc(), AthleteDailyTrainingLoad.id.asc())
        .all()
    )
    row_map = {row.load_date: row for row in rows}

    results: list[dict] = []
    current = date_from
    while current <= date_to:
        row = row_map.get(current)
        results.append(
            {
                "load_date": current,
                "session_count": row.session_count if row else 0,
                "total_duration_minutes": row.total_duration_minutes if row else 0,
                "total_srpe_load": row.total_srpe_load if row else 0,
            }
        )
        current += timedelta(days=1)
    return results


def _upsert_daily_training_load(db: Session, *, athlete_id: int, load_date: date) -> None:
    sessions = (
        db.query(TrainingSession)
        .filter(
            TrainingSession.athlete_id == athlete_id,
            TrainingSession.session_date == load_date,
            TrainingSession.status != "voided",
            TrainingSession.session_duration_minutes.is_not(None),
            TrainingSession.session_srpe_load.is_not(None),
        )
        .order_by(TrainingSession.id.asc())
        .all()
    )
    existing = (
        db.query(AthleteDailyTrainingLoad)
        .filter(
            AthleteDailyTrainingLoad.athlete_id == athlete_id,
            AthleteDailyTrainingLoad.load_date == load_date,
        )
        .first()
    )

    if not sessions:
        if existing:
            db.delete(existing)
            db.flush()
        return

    payload = {
        "session_count": len(sessions),
        "total_duration_minutes": sum(session.session_duration_minutes or 0 for session in sessions),
        "total_srpe_load": sum(session.session_srpe_load or 0 for session in sessions),
        "source_session_ids": [session.id for session in sessions],
    }
    if existing:
        existing.session_count = payload["session_count"]
        existing.total_duration_minutes = payload["total_duration_minutes"]
        existing.total_srpe_load = payload["total_srpe_load"]
        existing.source_session_ids = payload["source_session_ids"]
        db.flush()
        return

    db.add(
        AthleteDailyTrainingLoad(
            athlete_id=athlete_id,
            load_date=load_date,
            session_count=payload["session_count"],
            total_duration_minutes=payload["total_duration_minutes"],
            total_srpe_load=payload["total_srpe_load"],
            source_session_ids=payload["source_session_ids"],
        )
    )
    db.flush()


def _calculate_session_load_values(session: TrainingSession) -> tuple[int | None, int | None]:
    if session.session_rpe is None or session.completed_at is None:
        return None, None

    started_at = _resolve_effective_started_at(session)
    if started_at is None:
        return None, None

    completed_at = _ensure_aware_utc(session.completed_at)
    diff_seconds = (completed_at - started_at).total_seconds()
    if diff_seconds <= 0:
        return None, None

    duration_minutes = max(1, round(diff_seconds / 60))
    return duration_minutes, duration_minutes * session.session_rpe


def _resolve_effective_started_at(session: TrainingSession) -> datetime | None:
    record_times = [
        _ensure_aware_utc(record.completed_at)
        for item in session.items
        for record in item.records
        if record.completed_at is not None
    ]
    if record_times:
        return min(record_times)
    if session.started_at is None:
        return None
    return _ensure_aware_utc(session.started_at)


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
