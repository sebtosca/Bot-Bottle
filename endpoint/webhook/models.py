"""Data models for webhook processing."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal


@dataclass
class WebhookEvent:
    """Structured representation of a parsed webhook event."""
    event_type: Literal["message", "status", "unknown"]
    message: Optional[Dict[str, Any]] = None
    message_id: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def is_message(self) -> bool:
        """Check if this is a message event that should be processed."""
        return self.event_type == "message" and self.message is not None
    
    @property
    def is_duplicate(self) -> bool:
        """Check if this event was marked as duplicate."""
        return self.error == "duplicate"


@dataclass
class ParsedMessage:
    """Structured representation of a parsed WhatsApp message."""
    message_id: str
    from_number: str
    message_type: str
    body: str
    num_media: int
    media_type: str
    product_id: str
    raw_message: Dict[str, Any]
    
    @classmethod
    def from_webhook_message(cls, message: Dict[str, Any]) -> "ParsedMessage":
        """Create ParsedMessage from webhook message dict."""
        message_id = message.get("id", "unknown")
        from_number = message.get("from", "")
        message_type = message.get("type", "")
        
        # Extract product_id from context
        product_id = "00001"  # Default to Cherry
        context = message.get("context", {})
        if context:
            product_id = context.get("product") or context.get("product_id") or product_id
        
        # Extract message content
        body = ""
        num_media = 0
        media_type = ""
        
        if message_type == "interactive":
            interactive_data = message.get("interactive", {})
            list_reply = interactive_data.get("list_reply")
            button_reply = interactive_data.get("button_reply")
            
            if list_reply:
                selected_product_id = list_reply.get("id")
                body = f"[SWITCH_CHARACTER:{selected_product_id}]"
            elif button_reply:
                selected_id = button_reply.get("id")
                if selected_id.startswith("stats_"):
                    body = f"[STATS_BUTTON:{selected_id}]"
                elif selected_id.startswith("FEED_"):
                    selected_product_id = selected_id.replace("FEED_", "")
                    body = f"[FEED_CHARACTER:{selected_product_id}]"
                else:
                    selected_product_id = selected_id
                    body = f"[SWITCH_CHARACTER:{selected_product_id}]"
        elif message_type == "text":
            text_data = message.get("text", {})
            if isinstance(text_data, dict):
                body = text_data.get("body", "")
            else:
                body = str(text_data) if text_data else ""
        elif message_type in ["image", "video", "audio", "document", "sticker"]:
            num_media = 1
            media_data = message.get(message_type, {})
            if isinstance(media_data, dict):
                media_type = media_data.get("mime_type", message_type)
            else:
                media_type = message_type
            
            if message_type == "sticker":
                media_type = "image/webp"
            elif message_type == "image":
                if isinstance(media_type, str) and "gif" in media_type.lower():
                    media_type = "image/gif"
                else:
                    media_type = media_type or "image/jpeg"
        
        return cls(
            message_id=message_id,
            from_number=from_number,
            message_type=message_type,
            body=body,
            num_media=num_media,
            media_type=media_type,
            product_id=product_id,
            raw_message=message
        )


@dataclass
class JobPayload:
    """Payload for enqueued message processing job."""
    request_id: str
    message_id: str
    from_number: str
    message_type: str
    body: str
    num_media: int
    media_type: str
    product_id: str
    raw_message: Dict[str, Any]
    timestamp: float
