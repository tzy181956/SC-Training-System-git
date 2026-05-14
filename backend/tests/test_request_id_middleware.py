from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient, Response

from app.core.logging import REQUEST_ID_HEADER, RequestIDMiddleware


class ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _build_app(*, logger: logging.Logger | None = None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware, logger=logger)

    @app.get("/ok")
    async def ok(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    return app


def _get(
    app: Any,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    raise_app_exceptions: bool = True,
) -> Response:
    return asyncio.run(
        _async_get(
            app,
            path,
            headers=headers,
            raise_app_exceptions=raise_app_exceptions,
        )
    )


async def _async_get(
    app: Any,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    raise_app_exceptions: bool = True,
) -> Response:
    transport = ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path, headers=headers)


def _assert_uuid(value: str) -> None:
    assert str(uuid.UUID(value)) == value


def test_client_request_id_is_reused() -> None:
    request_id = "coach-ipad_01.session:abc-123"
    response = _get(_build_app(), "/ok", headers={REQUEST_ID_HEADER: request_id})

    assert response.headers[REQUEST_ID_HEADER] == request_id
    assert response.json()["request_id"] == request_id


def test_request_id_is_generated_when_header_is_missing() -> None:
    response = _get(_build_app(), "/ok")

    generated_request_id = response.headers[REQUEST_ID_HEADER]
    _assert_uuid(generated_request_id)
    assert response.json()["request_id"] == generated_request_id


@pytest.mark.parametrize("unsafe_request_id", ["has space", "a" * 81])
def test_unsafe_request_id_header_is_replaced(unsafe_request_id: str) -> None:
    response = _get(_build_app(), "/ok", headers={REQUEST_ID_HEADER: unsafe_request_id})

    generated_request_id = response.headers[REQUEST_ID_HEADER]
    assert generated_request_id != unsafe_request_id
    _assert_uuid(generated_request_id)
    assert response.json()["request_id"] == generated_request_id


def test_failed_request_is_not_also_logged_as_completed() -> None:
    handler = ListHandler()
    logger = logging.getLogger(f"request-id-middleware-test.{uuid.uuid4()}")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    request_id = "training-tablet-01"

    response = _get(
        _build_app(logger=logger),
        "/boom",
        headers={REQUEST_ID_HEADER: request_id},
        raise_app_exceptions=False,
    )

    messages = [record.getMessage() for record in handler.records]
    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == request_id
    assert messages.count("request_failed") == 1
    assert "request_completed" not in messages
