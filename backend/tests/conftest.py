from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response


_TEST_DIR = Path(tempfile.mkdtemp(prefix="sc_training_backend_tests_"))
_TEST_DB_PATH = _TEST_DIR / "test.db"

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["APP_ENV"] = "development"
os.environ.setdefault("SECRET_KEY", "test-secret-key")


class ASGIClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def get(self, path: str, *, headers: dict[str, str] | None = None) -> Response:
        return self.request("GET", path, headers=headers)

    def post(
        self,
        path: str,
        *,
        json_body: Any | None = None,
        files: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        return self.request("POST", path, json_body=json_body, files=files, headers=headers)

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        files: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        return asyncio.run(self._request(method, path, json_body=json_body, files=files, headers=headers))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        files: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, json=json_body, files=files, headers=headers)


@pytest.fixture()
def asgi_client() -> ASGIClient:
    from app.main import app

    return ASGIClient(app)


def pytest_sessionfinish(session, exitstatus) -> None:
    _ = session, exitstatus
    shutil.rmtree(_TEST_DIR, ignore_errors=True)
