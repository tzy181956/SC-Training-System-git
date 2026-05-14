from __future__ import annotations

import contextvars
import json
import logging as python_logging
import sys
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


REQUEST_ID_HEADER = "X-Request-ID"
_request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


class JsonLogFormatter(python_logging.Formatter):
    def format(self, record: python_logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        for key in (
            "event",
            "method",
            "path",
            "status",
            "duration_ms",
            "check",
            "closed_count",
            "backup_path",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    logger = python_logging.getLogger("sc_training")
    if not any(isinstance(handler.formatter, JsonLogFormatter) for handler in logger.handlers):
        handler = python_logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
    logger.setLevel(python_logging.INFO)
    logger.propagate = False


def get_logger(name: str | None = None) -> python_logging.Logger:
    configure_logging()
    logger_name = "sc_training" if not name else f"sc_training.{name}"
    return python_logging.getLogger(logger_name)


def get_request_id() -> str | None:
    return _request_id_context.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, logger: python_logging.Logger | None = None) -> None:
        super().__init__(app)
        self.logger = logger or get_logger("request")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        token = _request_id_context.set(request_id)
        request.state.request_id = request_id
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "request_failed",
                extra={
                    "event": "request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self.logger.info(
                "request_completed",
                extra={
                    "event": "request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            _request_id_context.reset(token)
