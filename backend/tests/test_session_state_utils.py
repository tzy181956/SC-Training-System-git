from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.services.session_state_utils import (
    build_snapshot_signature,
    serialize_full_sync_payload,
    serialize_session_snapshot,
)


def _session_like(*, started_at, completed_at):
    completed_set_at = datetime(2026, 5, 15, 10, 5, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        athlete_id=1,
        assignment_id=2,
        template_id=3,
        session_date=date(2026, 5, 15),
        status="in_progress",
        started_at=started_at,
        completed_at=completed_at,
        session_rpe=None,
        session_feedback=None,
        items=[
            SimpleNamespace(
                template_item_id=10,
                exercise_id=20,
                sort_order=1,
                prescribed_sets=2,
                prescribed_reps=5,
                target_note="",
                is_main_lift=True,
                enable_auto_load=False,
                status="in_progress",
                initial_load=60,
                records=[
                    SimpleNamespace(
                        set_number=1,
                        actual_weight=60,
                        actual_reps=5,
                        actual_rir=2,
                        final_weight=60,
                        notes="",
                        completed_at=completed_set_at,
                    )
                ],
            )
        ],
    )


def test_snapshot_signature_treats_naive_and_utc_datetimes_as_same_instant() -> None:
    naive_session = _session_like(
        started_at=datetime(2026, 5, 15, 10, 0, 0),
        completed_at=None,
    )
    aware_payload = _session_like(
        started_at=datetime(2026, 5, 15, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=None,
    )

    remote_signature = build_snapshot_signature(serialize_session_snapshot(naive_session))
    local_signature = build_snapshot_signature(serialize_full_sync_payload(aware_payload))

    assert remote_signature == local_signature
