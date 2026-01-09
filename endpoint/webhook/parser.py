"""Pure parsing functions for WhatsApp webhook payloads.

All functions are pure (no Flask/request dependencies) and accept Python dicts.
This makes them easily testable without network or framework dependencies.
"""

from typing import Dict, Any, Optional
from .models import WebhookEvent, ParsedMessage


def parse_webhook_payload(data: Dict[str, Any]) -> WebhookEvent:
    """Parse webhook payload and classify event type.
    
    Supports both common webhook payload shapes:
    - Production: entry[0].changes[0].value.messages[0]
    - Test: value.messages[0]
    
    Args:
        data: Already-decoded JSON payload as dict.
    
    Returns:
        WebhookEvent with event_type, message (if any), message_id (if any), error (if any).
    """
    if not data or not isinstance(data, dict):
        return WebhookEvent(
            event_type="unknown",
            error="Invalid payload: not a dict"
        )
    
    # Extract message from Cloud API webhook structure
    entry = data.get("entry", [])
    value = None
    messages = []
    
    if entry and isinstance(entry, list) and len(entry) > 0:
        # Standard production webhook structure
        changes = entry[0].get("changes", [])
        if changes and isinstance(changes, list) and len(changes) > 0:
            value = changes[0].get("value", {})
            if isinstance(value, dict):
                messages = value.get("messages", [])
    elif "value" in data:
        # Test payload structure (direct value)
        value = data.get("value", {})
        if isinstance(value, dict):
            messages = value.get("messages", [])
    
    # Check for status updates
    if value and isinstance(value, dict):
        statuses = value.get("statuses", [])
        if statuses:
            return WebhookEvent(
                event_type="status",
                message_id=statuses[0].get("id") if statuses else None
            )
    
    # Check for messages
    if messages and isinstance(messages, list) and len(messages) > 0:
        message = messages[0]
        if not isinstance(message, dict):
            return WebhookEvent(
                event_type="unknown",
                error="Invalid message format: not a dict"
            )
        
        message_id = message.get("id")
        return WebhookEvent(
            event_type="message",
            message=message,
            message_id=message_id
        )
    
    # No messages, no statuses - unknown event type
    return WebhookEvent(
        event_type="unknown",
        message_id=None
    )


def parse_message(message: Dict[str, Any]) -> ParsedMessage:
    """Parse a message dict into structured ParsedMessage.
    
    Args:
        message: Message dict from webhook.
    
    Returns:
        ParsedMessage with all extracted fields.
    
    Raises:
        ValueError: If required fields are missing.
    """
    if not isinstance(message, dict):
        raise ValueError("Message must be a dict")
    
    message_id = message.get("id")
    from_number = message.get("from", "")
    
    if not message_id:
        raise ValueError("Missing required field: id")
    if not from_number:
        raise ValueError("Missing required field: from")
    
    return ParsedMessage.from_webhook_message(message)


def extract_stable_id(event: WebhookEvent) -> Optional[str]:
    """Extract a stable unique ID for idempotency checking.
    
    Uses WhatsApp message ID when available, otherwise None.
    
    Args:
        event: Parsed webhook event.
    
    Returns:
        Stable unique ID for the event, or None if not available.
    """
    if event.message_id:
        return event.message_id
    
    # Fallback: try to extract from message dict
    if event.message and isinstance(event.message, dict):
        return event.message.get("id")
    
    return None
