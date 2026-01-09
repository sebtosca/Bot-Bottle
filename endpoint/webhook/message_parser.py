"""Parse incoming WhatsApp webhook messages.

DEPRECATED: This module is kept for backward compatibility.
New code should use endpoint.webhook.parser instead.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from werkzeug.exceptions import BadRequest
from flask import request

logger = logging.getLogger(__name__)


def parse_webhook_data() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Parse incoming webhook JSON data and extract message.
    
    Returns:
        Tuple of (message dict, error message). If error, message is None.
    """
    try:
        data = request.get_json()
    except BadRequest as json_error:
        logger.exception("Failed to parse JSON payload from webhook")
        raw_body = request.get_data(cache=False)
        if raw_body:
            preview = raw_body[:200].decode('utf-8', errors='replace')
            logger.debug("Payload preview: %s", preview)
        return None, f"Invalid JSON payload: {json_error}"
    
    if not data:
        logger.warning("No JSON data received")
        raw_body = request.get_data(cache=False)
        if raw_body:
            preview = raw_body[:200].decode('utf-8', errors='replace')
            logger.debug("Raw data preview: %s", preview)
        return None, "No JSON data received"
    
    logger.info("Webhook data received", extra={
        "object": data.get("object"),
        "entry_count": len(data.get("entry", []))
    })
    
    # Extract message from Cloud API webhook structure
    entry = data.get("entry", [])
    value = None
    messages = []
    
    if entry and isinstance(entry, list) and len(entry) > 0:
        # Standard production webhook structure
        logger.debug("Detected production webhook structure")
        changes = entry[0].get("changes", [])
        if changes and isinstance(changes, list) and len(changes) > 0:
            value = changes[0].get("value", {})
            if isinstance(value, dict):
                messages = value.get("messages", [])
    elif "value" in data:
        # Test payload structure (direct value)
        logger.debug("Detected test payload structure (direct value)")
        value = data.get("value", {})
        if isinstance(value, dict):
            messages = value.get("messages", [])
    else:
        # No recognizable structure - might be status update
        logger.debug("No recognizable message structure, acknowledging webhook")
        return None, None  # Not an error, just not a message
    
    if not messages or not isinstance(messages, list) or len(messages) == 0:
        # Status update or other webhook event, not a message
        logger.info("No messages in webhook (status update or other event)")
        if value and isinstance(value, dict):
            logger.debug("Value keys: %s", list(value.keys()))
        return None, None  # Not an error, just not a message
    
    message = messages[0]
    if not isinstance(message, dict):
        logger.warning("Message is not a valid dict")
        return None, "Invalid message format"
    
    return message, None


def extract_message_info(message: Dict[str, Any]) -> Tuple[str, str, str, Optional[str]]:
    """Extract basic information from a message.
    
    Args:
        message: Message dict from webhook.
    
    Returns:
        Tuple of (from_number, message_type_api, message_id, product_id).
    """
    from_number = message.get("from", "")
    message_type_api = message.get("type", "")
    message_id = message.get("id", "unknown")
    
    # Extract product_id from message context
    product_id = None
    context = message.get("context", {})
    if context:
        product_id = context.get("product") or context.get("product_id")
        if product_id:
            logger.debug("Product ID from context: %s", product_id)
    
    # Default to Cherry if no product_id
    if not product_id:
        product_id = "00001"
        logger.debug("No product_id in context, defaulting to: %s", product_id)
    
    return from_number, message_type_api, message_id, product_id


def extract_message_content(message: Dict[str, Any], message_type_api: str) -> Tuple[str, int, str]:
    """Extract message content based on type.
    
    Args:
        message: Message dict from webhook.
        message_type_api: Type of message from API.
    
    Returns:
        Tuple of (body, num_media, media_type).
    """
    body = ""
    num_media = 0
    media_type = ""
    
    # Handle interactive messages (button/list responses)
    if message_type_api == "interactive":
        interactive_data = message.get("interactive", {})
        list_reply = interactive_data.get("list_reply")
        button_reply = interactive_data.get("button_reply")
        
        if list_reply:
            selected_product_id = list_reply.get("id")
            body = f"[SWITCH_CHARACTER:{selected_product_id}]"
            logger.debug("Interactive list selection", extra={"product_id": selected_product_id})
        elif button_reply:
            selected_id = button_reply.get("id")
            # Handle stats buttons (will be processed separately)
            if selected_id.startswith("stats_"):
                body = f"[STATS_BUTTON:{selected_id}]"
            elif selected_id.startswith("FEED_"):
                selected_product_id = selected_id.replace("FEED_", "")
                body = f"[FEED_CHARACTER:{selected_product_id}]"
                logger.debug("Feed selection button", extra={"product_id": selected_product_id})
            else:
                selected_product_id = selected_id
                body = f"[SWITCH_CHARACTER:{selected_product_id}]"
                logger.debug("Interactive button selection", extra={"product_id": selected_product_id})
    
    # Extract message content based on type
    elif message_type_api == "text":
        text_data = message.get("text", {})
        if isinstance(text_data, dict):
            body = text_data.get("body", "")
        else:
            body = str(text_data) if text_data else ""
    elif message_type_api in ["image", "video", "audio", "document", "sticker"]:
        num_media = 1
        media_data = message.get(message_type_api, {})
        if isinstance(media_data, dict):
            media_type = media_data.get("mime_type", message_type_api)
        else:
            media_type = message_type_api
        # For stickers, Cloud API doesn't always provide mime_type
        if message_type_api == "sticker":
            media_type = "image/webp"
        elif message_type_api == "image":
            if isinstance(media_type, str) and "gif" in media_type.lower():
                media_type = "image/gif"
            else:
                media_type = media_type or "image/jpeg"
    else:
        logger.warning("Unknown message type", extra={"message_type": message_type_api})
        body = ""
    
    return body, num_media, media_type
