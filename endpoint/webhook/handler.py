"""Fast webhook handler that ACKs quickly and enqueues work.

This module implements the webhook ingestion flow:
1. Verify signature (if enabled)
2. Parse payload
3. Check idempotency
4. Enqueue job
5. Return 200 OK quickly

All heavy processing happens in the worker, not in the request handler.
"""

import logging
import uuid
import time
from typing import Tuple, Optional
from flask import Request, jsonify, g

from .parser import parse_webhook_payload, parse_message, extract_stable_id
from .validator import verify_webhook_signature, verify_webhook_token
from .idempotency import get_idempotency_store, IdempotencyStore
from .queue import get_message_queue, MessageQueue
from .models import WebhookEvent, ParsedMessage, JobPayload

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    """Extract or generate request ID for request correlation.
    
    Prefers X-Request-ID header if present, otherwise generates uuid4.
    This ID is used for correlating logs across the request lifecycle.
    
    Args:
        request: Flask request object.
    
    Returns:
        Request ID string (UUID format).
    """
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        # Validate format (basic check)
        if len(request_id) > 100:  # Sanity check
            logger.warning("Request ID too long, generating new one", extra={
                "provided_id_length": len(request_id)
            })
            return str(uuid.uuid4())
        return request_id
    return str(uuid.uuid4())


class WebhookHandler:
    """Webhook handler with fast ACK and async processing."""
    
    def __init__(
        self,
        idempotency_store: Optional[IdempotencyStore] = None,
        message_queue: Optional[MessageQueue] = None,
        enable_signature_verification: bool = True
    ):
        """Initialize webhook handler.
        
        Args:
            idempotency_store: Idempotency store instance. If None, auto-detects.
            message_queue: Message queue instance. If None, auto-detects.
            enable_signature_verification: Whether to verify webhook signatures.
        """
        self.idempotency_store = idempotency_store or get_idempotency_store()
        self.message_queue = message_queue or get_message_queue()
        self.enable_signature_verification = enable_signature_verification
    
    def handle_verification(self, request: Request) -> Tuple[dict, int]:
        """Handle webhook verification (GET request).
        
        Args:
            request: Flask request object.
        
        Returns:
            Tuple of (response dict, status code).
        """
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if verify_webhook_token(mode, token):
            logger.info("Webhook verification successful", extra={"mode": mode})
            return challenge, 200
        else:
            logger.warning("Webhook verification failed", extra={"mode": mode})
            return jsonify({"error": "Verification failed"}), 403
    
    def handle_webhook(self, request: Request, request_id: Optional[str] = None) -> Tuple[dict, int]:
        """Handle incoming webhook (POST request).
        
        Fast ACK pattern: verify → parse → idempotency → enqueue → 200 OK.
        
        Args:
            request: Flask request object.
            request_id: Optional request correlation ID. If None, gets from Flask g.
        
        Returns:
            Tuple of (response dict, status code).
        """
        # Get request_id from Flask g if not provided (set by middleware)
        if not request_id:
            request_id = getattr(g, 'request_id', None) or get_request_id(request)
        
        # Log request details for debugging
        client_ip = request.remote_addr or "unknown"
        logger.info("Webhook request received", extra={
            "request_id": request_id,
            "method": request.method,
            "client_ip": client_ip,
            "url": request.url,
            "content_type": request.content_type,
            "has_signature_header": "X-Hub-Signature-256" in request.headers
        })
        
        # 1. Verify signature (if enabled)
        if self.enable_signature_verification:
            # Skip signature verification for localhost/test requests if WHATSAPP_APP_SECRET is not set
            import os
            app_secret = os.environ.get("WHATSAPP_APP_SECRET")
            is_localhost = client_ip in ("127.0.0.1", "localhost", "::1") or request.host.startswith("localhost")
            
            if not app_secret and is_localhost:
                logger.info("Skipping signature verification for localhost request (WHATSAPP_APP_SECRET not set)", extra={
                    "request_id": request_id,
                    "client_ip": client_ip
                })
            elif not verify_webhook_signature(request):
                logger.error("Webhook signature verification failed", extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "has_signature_header": "X-Hub-Signature-256" in request.headers,
                    "app_secret_set": bool(app_secret)
                })
                return jsonify({"error": "Invalid signature"}), 403
            else:
                logger.info("Webhook signature verification passed", extra={"request_id": request_id})
        
        # 2. Parse JSON payload
        try:
            data = request.get_json()
        except Exception as json_error:
            logger.exception("Failed to parse JSON payload", extra={"request_id": request_id})
            # Log truncated payload preview (DEBUG only)
            raw_body = request.get_data(cache=False)
            if raw_body:
                preview = raw_body[:200].decode('utf-8', errors='replace')
                logger.debug("Payload preview: %s", preview, extra={"request_id": request_id})
            return jsonify({"error": "Invalid JSON payload"}), 400
        
        if not data:
            logger.warning("No JSON data received", extra={"request_id": request_id})
            return jsonify({"error": "No JSON data received"}), 400
        
        logger.info("Webhook payload parsed", extra={
            "request_id": request_id,
            "object": data.get("object"),
            "entry_count": len(data.get("entry", [])),
            "payload_keys": list(data.keys())[:10]  # First 10 keys for debugging
        })
        
        # 3. Parse webhook payload (pure function)
        event = parse_webhook_payload(data)
        
        logger.debug("Parsed webhook event", extra={
            "request_id": request_id,
            "event_type": event.event_type,
            "message_id": event.message_id
        })
        
        # 4. Handle different event types
        if event.event_type == "status":
            # Status update - acknowledge, no processing
            logger.info("Status update received, acknowledging", extra={
                "request_id": request_id,
                "message_id": event.message_id
            })
            return jsonify({"status": "ok"}), 200
        
        if event.event_type == "unknown":
            # Unknown event - acknowledge, log debug
            logger.debug("Unknown event type, acknowledging", extra={
                "request_id": request_id,
                "message_id": event.message_id
            })
            return jsonify({"status": "ok"}), 200
        
        if event.event_type != "message" or not event.message:
            # Should not happen, but handle gracefully
            logger.warning("Unexpected event state", extra={
                "request_id": request_id,
                "event_type": event.event_type
            })
            return jsonify({"status": "ok"}), 200
        
        # 5. Extract stable ID for idempotency
        stable_id = extract_stable_id(event)
        if not stable_id:
            logger.warning("No stable ID found for message", extra={"request_id": request_id})
            # Still process, but can't dedupe
        else:
            # 6. Check idempotency
            if self.idempotency_store.is_duplicate(stable_id):
                logger.info("Duplicate message detected, skipping", extra={
                    "request_id": request_id,
                    "message_id": stable_id
                })
                return jsonify({"status": "ok", "message": "duplicate"}), 200
        
        # 7. Parse message
        try:
            parsed_message = parse_message(event.message)
        except ValueError as e:
            logger.warning("Failed to parse message", extra={
                "request_id": request_id,
                "error": str(e)
            })
            return jsonify({"error": "Invalid message format"}), 400
        
        # 8. Create job payload
        job_payload = JobPayload(
            request_id=request_id,
            message_id=parsed_message.message_id,
            from_number=parsed_message.from_number,
            message_type=parsed_message.message_type,
            body=parsed_message.body,
            num_media=parsed_message.num_media,
            media_type=parsed_message.media_type,
            product_id=parsed_message.product_id,
            raw_message=parsed_message.raw_message,
            timestamp=time.time()
        )
        
        # 9. Enqueue job
        logger.info("Attempting to enqueue message", extra={
            "request_id": request_id,
            "message_id": parsed_message.message_id,
            "from_number": parsed_message.from_number[:4] + "****",
            "message_type": parsed_message.message_type,
            "product_id": parsed_message.product_id,
            "queue_type": type(self.message_queue).__name__,
            "queue_id": id(self.message_queue)
        })
        
        if self.message_queue.enqueue(job_payload):
            # Mark as processed (idempotency)
            if stable_id:
                self.idempotency_store.mark_processed(stable_id, ttl_seconds=86400)  # 24 hours
            
            logger.info("Message enqueued successfully", extra={
                "request_id": request_id,
                "message_id": parsed_message.message_id,
                "from_number": parsed_message.from_number[:4] + "****",
                "message_type": parsed_message.message_type
            })
            
            return jsonify({"status": "ok", "message": "enqueued", "request_id": request_id}), 200
        else:
            logger.error("Failed to enqueue message", extra={
                "request_id": request_id,
                "message_id": parsed_message.message_id,
                "queue_type": type(self.message_queue).__name__
            })
            # Still return 200 to avoid retries from WhatsApp
            return jsonify({"status": "ok", "message": "enqueue_failed", "request_id": request_id}), 200
