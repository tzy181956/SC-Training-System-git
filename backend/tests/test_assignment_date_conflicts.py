from __future__ import annotations

from datetime import date
from pathlib import Path
from queue import Queue
import sys
from threading import Event, Lock, Thread
from time import sleep
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base
from app.models import Athlete, AthletePlanAssignment, Sport, Team, TrainingPlanTemplate
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate, BatchAssignmentCreate
from app.services import assignment_service


@pytest.fixture()
def db_session(tmp_path) -> Session:
    engine = create_engine(f"sqlite:///{(tmp_path / 'assignment-conflicts.db').as_posix()}")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_create_assignment_rejects_complete_overlap_and_preview_marks_row_conflict(db_session: Session) -> None:
    ids = _seed_assignment_scope(db_session)
    _add_assignment(
        db_session,
        athlete_id=ids.athlete_id,
        template_id=ids.template_a_id,
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 10),
        repeat_weekdays=[1, 2, 3, 4, 5, 6, 7],
    )

    preview = assignment_service.preview_batch_assignments(
        db_session,
        BatchAssignmentCreate(
            athlete_ids=[ids.athlete_id],
            template_id=ids.template_a_id,
            assigned_date=date(2026, 5, 4),
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 10),
            repeat_weekdays=[1, 2, 3, 4, 5, 6, 7],
        ),
    )

    row = preview["rows"][0]
    assert row["conflict_status"] == "conflict"
    assert row["conflict_dates"] == [date(2026, 5, day) for day in range(4, 11)]
    assert "2026-05-04" in row["conflict_message"]

    with pytest.raises(HTTPException) as raised:
        assignment_service.create_assignment(
            db_session,
            AssignmentCreate(
                athlete_id=ids.athlete_id,
                template_id=ids.template_a_id,
                assigned_date=date(2026, 5, 4),
                start_date=date(2026, 5, 4),
                end_date=date(2026, 5, 10),
                repeat_weekdays=[1, 2, 3, 4, 5, 6, 7],
            ),
        )

    assert raised.value.status_code == 400
    assert "同一天最多只能有一个 active 计划" in raised.value.detail
    assert db_session.query(AthletePlanAssignment).count() == 1


def test_update_assignment_rejects_partial_date_overlap(db_session: Session) -> None:
    ids = _seed_assignment_scope(db_session)
    _add_assignment(
        db_session,
        athlete_id=ids.athlete_id,
        template_id=ids.template_a_id,
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 13),
        repeat_weekdays=[1, 3],
    )
    assignment_id = _add_assignment(
        db_session,
        athlete_id=ids.athlete_id,
        template_id=ids.template_b_id,
        start_date=date(2026, 5, 20),
        end_date=date(2026, 5, 22),
        repeat_weekdays=[3],
    )

    conflicts = assignment_service.find_assignment_date_conflicts(
        db_session,
        ids.athlete_id,
        date(2026, 5, 12),
        date(2026, 5, 16),
        [3, 5],
        ignore_id=assignment_id,
    )
    assert [conflict_date for conflict in conflicts for conflict_date in conflict["dates"]] == [date(2026, 5, 13)]

    with pytest.raises(HTTPException) as raised:
        assignment_service.update_assignment(
            db_session,
            assignment_id,
            AssignmentUpdate(
                start_date=date(2026, 5, 12),
                end_date=date(2026, 5, 16),
                repeat_weekdays=[3, 5],
            ),
        )

    assert raised.value.status_code == 400
    assert "2026-05-13" in raised.value.detail


def test_date_overlap_without_weekday_overlap_has_no_conflict(db_session: Session) -> None:
    ids = _seed_assignment_scope(db_session)
    _add_assignment(
        db_session,
        athlete_id=ids.athlete_id,
        template_id=ids.template_a_id,
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 18),
        repeat_weekdays=[1],
    )

    conflicts = assignment_service.find_assignment_date_conflicts(
        db_session,
        ids.athlete_id,
        date(2026, 5, 4),
        date(2026, 5, 18),
        [2],
    )
    assert conflicts == []

    created = assignment_service.create_assignment(
        db_session,
        AssignmentCreate(
            athlete_id=ids.athlete_id,
            template_id=ids.template_b_id,
            assigned_date=date(2026, 5, 4),
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 18),
            repeat_weekdays=[2],
        ),
    )

    assert created.id is not None
    assert db_session.query(AthletePlanAssignment).count() == 2


def test_batch_assignment_rejects_same_day_conflict_with_different_template(db_session: Session) -> None:
    ids = _seed_assignment_scope(db_session)
    _add_assignment(
        db_session,
        athlete_id=ids.athlete_id,
        template_id=ids.template_a_id,
        start_date=date(2026, 5, 14),
        end_date=date(2026, 5, 14),
        repeat_weekdays=[4],
    )

    with pytest.raises(HTTPException) as raised:
        assignment_service.create_batch_assignments(
            db_session,
            BatchAssignmentCreate(
                athlete_ids=[ids.athlete_id],
                template_id=ids.template_b_id,
                assigned_date=date(2026, 5, 14),
                start_date=date(2026, 5, 14),
                end_date=date(2026, 5, 14),
                repeat_weekdays=[4],
            ),
        )

    assert raised.value.status_code == 400
    assert "2026-05-14" in raised.value.detail
    assert db_session.query(AthletePlanAssignment).count() == 1


def test_begin_immediate_helper_skips_non_sqlite_connection() -> None:
    class NonSqliteSession:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def connection(self):  # pragma: no cover - must not be called
            raise AssertionError("non-SQLite assignment lock must not touch the connection")

    assert assignment_service._begin_immediate_for_assignment_conflict_check(NonSqliteSession()) is False


def test_concurrent_create_assignment_same_day_allows_only_one(tmp_path, monkeypatch) -> None:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'assignment-concurrency.db').as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    seed_db = SessionLocal()
    try:
        ids = _seed_assignment_scope(seed_db)
    finally:
        seed_db.close()

    original_validate_window = assignment_service._validate_window
    first_validate_entered = Event()
    release_first_validate = Event()
    validate_call_lock = Lock()
    validate_call_count = 0

    def delayed_validate_window(*args, **kwargs):
        nonlocal validate_call_count
        with validate_call_lock:
            validate_call_count += 1
            call_index = validate_call_count
        if call_index == 1:
            first_validate_entered.set()
            assert release_first_validate.wait(timeout=5)
        return original_validate_window(*args, **kwargs)

    monkeypatch.setattr(assignment_service, "_validate_window", delayed_validate_window)
    results: Queue[tuple] = Queue()

    def create_in_new_session(template_id: int) -> None:
        db = SessionLocal()
        try:
            try:
                created = assignment_service.create_assignment(
                    db,
                    AssignmentCreate(
                        athlete_id=ids.athlete_id,
                        template_id=template_id,
                        assigned_date=date(2026, 5, 14),
                        start_date=date(2026, 5, 14),
                        end_date=date(2026, 5, 14),
                        repeat_weekdays=[4],
                    ),
                )
                results.put(("success", created.id))
            except HTTPException as exc:
                results.put(("http_error", exc.status_code, exc.detail))
            except Exception as exc:  # pragma: no cover - asserted through result payload
                results.put(("error", type(exc).__name__, str(exc)))
        finally:
            db.close()

    first_thread = Thread(target=create_in_new_session, args=(ids.template_a_id,))
    second_thread = Thread(target=create_in_new_session, args=(ids.template_b_id,))
    first_thread.start()
    assert first_validate_entered.wait(timeout=5)
    second_thread.start()
    sleep(0.1)
    release_first_validate.set()
    first_thread.join(timeout=5)
    second_thread.join(timeout=5)

    try:
        assert not first_thread.is_alive()
        assert not second_thread.is_alive()
        outcomes = [results.get_nowait() for _ in range(2)]
        successes = [outcome for outcome in outcomes if outcome[0] == "success"]
        conflicts = [
            outcome
            for outcome in outcomes
            if outcome[0] == "http_error" and outcome[1] == 400 and "同一天最多只能有一个 active 计划" in outcome[2]
        ]
        assert len(successes) == 1
        assert len(conflicts) == 1
        assert validate_call_count == 2

        verify_db = SessionLocal()
        try:
            assert verify_db.query(AthletePlanAssignment).count() == 1
        finally:
            verify_db.close()
    finally:
        engine.dispose()


def _seed_assignment_scope(db: Session) -> SimpleNamespace:
    sport = Sport(name="Basketball", code="basketball")
    team = Team(name="U18", code="u18", sport=sport)
    athlete = Athlete(code="athlete_001", full_name="Test Athlete", sport=sport, team=team)
    template_a = TrainingPlanTemplate(name="Strength A", sport=sport, team=team, visibility="public")
    template_b = TrainingPlanTemplate(name="Strength B", sport=sport, team=team, visibility="public")

    db.add_all([sport, team, athlete, template_a, template_b])
    db.commit()

    return SimpleNamespace(
        athlete_id=athlete.id,
        template_a_id=template_a.id,
        template_b_id=template_b.id,
    )


def _add_assignment(
    db: Session,
    *,
    athlete_id: int,
    template_id: int,
    start_date: date,
    end_date: date,
    repeat_weekdays: list[int],
    status: str = "active",
) -> int:
    assignment = AthletePlanAssignment(
        athlete_id=athlete_id,
        template_id=template_id,
        assigned_date=start_date,
        start_date=start_date,
        end_date=end_date,
        repeat_weekdays=repeat_weekdays,
        status=status,
    )
    db.add(assignment)
    db.commit()
    return assignment.id
