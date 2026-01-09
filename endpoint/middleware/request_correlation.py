"""Request correlation middleware for Flask."""

from __future__ import annotations

import logging
import uuid
from flask import Flask, g, has_request_context, request

logger = logging.getLogger(__name__)

_DEFAULT_FACTORY = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _DEFAULT_FACTORY(*args, **kwargs)
    # Always present, safe in any context
    record.request_id = getattr(g, "request_id", None) if has_request_context() else None
    return record


def setup_request_correlation(app: Flask) -> None:
    """Attach request_id to Flask context + make it available on all log records."""
    logging.setLogRecordFactory(_record_factory)

    @app.before_request
    def _add_request_id():
        rid = request.headers.get("X-Request-ID")
        if not rid or len(rid) > 100:
            rid = str(uuid.uuid4())
        g.request_id = rid

        # Keep this minimal to avoid log volume blow-ups
        logger.info("Request started", extra={"method": request.method, "path": request.path})

    @app.after_request
    def _after(response):
        rid = getattr(g, "request_id", None)
        if rid:
            response.headers["X-Request-ID"] = rid
            logger.info("Request completed", extra={"status_code": response.status_code})
        return response
