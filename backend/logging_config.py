import contextvars
import logging
import uuid

from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Per-async-task context variable — safe for concurrent requests
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


class _TraceIDFilter(logging.Filter):
    """Injects the current request's trace_id from the ContextVar into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace_id_var.get("-")  # type: ignore[attr-defined]
        return True


def configure_logging(log_level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(trace_id)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addFilter(_TraceIDFilter())


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Injects a per-request trace_id into log records via a ContextVar.

    Using a ContextVar (rather than mutating the global log record factory) ensures
    that concurrent async requests each see their own trace ID with no cross-request
    bleed.
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id
        token = _trace_id_var.set(trace_id)
        try:
            response = await call_next(request)
        finally:
            _trace_id_var.reset(token)
        response.headers["X-Trace-ID"] = trace_id
        return response
