from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

# Reject IDs that could forge log lines or bloat the log (e.g. newlines, very long values).
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear context left over from a previous request handled by this worker.
        clear_contextvars()

        incoming = request.headers.get("x-request-id", "").strip()
        correlation_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else f"req-{uuid.uuid4().hex[:8]}"
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)

        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = str(int((time.perf_counter() - start) * 1000))
        return response
