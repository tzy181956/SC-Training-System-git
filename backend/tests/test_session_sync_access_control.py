from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.endpoints import sessions as sessions_endpoint  # noqa: E402
from app.schemas.training_session import SessionSetSyncOperation  # noqa: E402


class FakeAccessControlService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int | None]] = []

    def get_accessible_session_item(self, db, current_user, item_id: int):
        self.calls.append(("session_item", item_id))

    def get_accessible_session(self, db, current_user, session_id: int):
        self.calls.append(("session", session_id))

    def get_accessible_assignment(self, db, current_user, assignment_id: int):
        self.calls.append(("assignment", assignment_id))

    def get_accessible_set_record(self, db, current_user, record_id: int):
        self.calls.append(("set_record", record_id))


class FakeSessionService:
    def __init__(self) -> None:
        self.payloads: list[SessionSetSyncOperation] = []

    def sync_session_operation(self, db, payload: SessionSetSyncOperation):
        self.payloads.append(payload)
        session = SimpleNamespace(status="in_progress", completed_at=None)
        return SimpleNamespace(), None, SimpleNamespace(), session


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class SyncSessionOperationAccessControlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_access_control_service = sessions_endpoint.access_control_service
        self.original_session_service = sessions_endpoint.session_service
        self.access_control_service = FakeAccessControlService()
        self.session_service = FakeSessionService()
        sessions_endpoint.access_control_service = self.access_control_service
        sessions_endpoint.session_service = self.session_service
        self.db = FakeDb()
        self.current_user = object()

    def tearDown(self) -> None:
        sessions_endpoint.access_control_service = self.original_access_control_service
        sessions_endpoint.session_service = self.original_session_service

    def _call(self, payload: SessionSetSyncOperation):
        return sessions_endpoint.sync_session_operation(payload, self.db, self.current_user)

    def _create_set_payload(self, **overrides) -> SessionSetSyncOperation:
        data = {
            "operation_type": "create_set",
            "actual_weight": 50.0,
            "actual_reps": 5,
            "actual_rir": 2,
            "final_weight": 50.0,
        }
        data.update(overrides)
        return SessionSetSyncOperation(**data)

    def test_create_set_checks_session_item_when_present(self) -> None:
        self._call(self._create_set_payload(session_item_id=31))

        self.assertEqual(self.access_control_service.calls, [("session_item", 31)])
        self.assertEqual(len(self.session_service.payloads), 1)

    def test_create_set_prefers_session_item_when_multiple_identifiers_are_present(self) -> None:
        self._call(self._create_set_payload(session_item_id=31, session_id=21, assignment_id=11))

        self.assertEqual(self.access_control_service.calls, [("session_item", 31)])
        self.assertEqual(len(self.session_service.payloads), 1)

    def test_create_set_checks_session_when_session_item_missing(self) -> None:
        self._call(self._create_set_payload(session_id=21))

        self.assertEqual(self.access_control_service.calls, [("session", 21)])
        self.assertEqual(len(self.session_service.payloads), 1)

    def test_create_set_checks_assignment_when_session_identifiers_missing(self) -> None:
        self._call(self._create_set_payload(assignment_id=11))

        self.assertEqual(self.access_control_service.calls, [("assignment", 11)])
        self.assertEqual(len(self.session_service.payloads), 1)

    def test_create_set_requires_one_supported_identifier(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            self._call(self._create_set_payload())

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(
            raised.exception.detail,
            "create_set requires session_item_id, session_id or assignment_id",
        )
        self.assertEqual(self.access_control_service.calls, [])
        self.assertEqual(self.session_service.payloads, [])
        self.assertEqual(self.db.commits, 0)
        self.assertEqual(self.db.rollbacks, 1)

    def test_update_set_still_checks_set_record_when_record_id_present(self) -> None:
        payload = SessionSetSyncOperation(
            operation_type="update_set",
            session_id=21,
            record_id=41,
            actual_weight=55.0,
            actual_reps=4,
            actual_rir=1,
            final_weight=55.0,
        )

        self._call(payload)

        self.assertEqual(self.access_control_service.calls, [("set_record", 41)])
        self.assertEqual(len(self.session_service.payloads), 1)

    def test_complete_session_access_control_is_unchanged(self) -> None:
        with self.subTest("session_id"):
            self._call(SessionSetSyncOperation(operation_type="complete_session", session_id=21))
            self.assertEqual(self.access_control_service.calls, [("session", 21)])

        self.access_control_service.calls.clear()
        self.session_service.payloads.clear()

        with self.subTest("assignment_id"):
            self._call(SessionSetSyncOperation(operation_type="complete_session", assignment_id=11))
            self.assertEqual(self.access_control_service.calls, [("assignment", 11)])


if __name__ == "__main__":
    unittest.main()
