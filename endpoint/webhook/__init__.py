"""Webhook handling modules for WhatsApp messages."""

# Core modules (no Flask dependency) - import immediately
from .models import WebhookEvent, ParsedMessage, JobPayload
from .parser import parse_webhook_payload, parse_message, extract_stable_id
from .idempotency import IdempotencyStore, get_idempotency_store
from .queue import MessageQueue, get_message_queue

# Flask-dependent modules - lazy import to avoid errors when Flask not installed
def _lazy_import_flask_modules():
    """Lazy import Flask-dependent modules."""
    from .handler import WebhookHandler, get_request_id
    from .worker import MessageWorker, setup_in_memory_worker
    from .validator import verify_webhook_signature, verify_webhook_token
    return {
        "WebhookHandler": WebhookHandler,
        "get_request_id": get_request_id,
        "MessageWorker": MessageWorker,
        "setup_in_memory_worker": setup_in_memory_worker,
        "verify_webhook_signature": verify_webhook_signature,
        "verify_webhook_token": verify_webhook_token,
    }

# Expose core modules immediately
__all__ = [
    "WebhookEvent",
    "ParsedMessage",
    "JobPayload",
    "parse_webhook_payload",
    "parse_message",
    "extract_stable_id",
    "IdempotencyStore",
    "get_idempotency_store",
    "MessageQueue",
    "get_message_queue",
]

# Try to import Flask modules, but don't fail if Flask not installed
try:
    flask_modules = _lazy_import_flask_modules()
    for name, obj in flask_modules.items():
        globals()[name] = obj
        __all__.append(name)
except ImportError:
    # Flask not installed - core modules still available
    pass
