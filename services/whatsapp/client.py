"""WhatsApp Cloud API client.

This module provides direct calls to Meta's WhatsApp Cloud API,
using a phone number ID and access token for sending messages.

Supports text messages, media (images/GIFs), stickers, and audio.
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

import requests

from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
import logging

logger = logging.getLogger(__name__)


API_BASE_URL = "https://graph.facebook.com/v18.0"  # Version can be updated as needed


class WhatsAppCloudError(Exception):
    """Raised when the WhatsApp Cloud API returns an error."""

    def __init__(self, message: str, error_code: Optional[str] = None, error_subcode: Optional[str] = None, full_response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.full_response = full_response


def _check_api_response(data: Dict[str, Any], response_text: str) -> None:
    """Check API response for errors even when HTTP status is 200.
    
    WhatsApp Cloud API can return 200 OK with errors in the response body.
    This function checks for common error patterns and raises appropriate exceptions.
    
    Args:
        data: Parsed JSON response from API
        response_text: Raw response text for logging
        
    Raises:
        WhatsAppCloudError: If errors are found in the response
    """
    # Check for top-level 'error' field
    if "error" in data:
        error = data["error"]
        error_message = error.get("message", "Unknown error")
        error_code = error.get("code")
        error_subcode = error.get("error_subcode")
        error_type = error.get("type", "Unknown")
        
        # Build detailed error message
        error_msg = f"WhatsApp Cloud API error: {error_message}"
        if error_code:
            error_msg += f" (code: {error_code})"
        if error_subcode:
            error_msg += f" (subcode: {error_subcode})"
        if error_type:
            error_msg += f" (type: {error_type})"
        
        raise WhatsAppCloudError(error_msg, error_code=error_code, error_subcode=error_subcode, full_response=data)
    
    # Check for 'errors' array (plural)
    if "errors" in data and isinstance(data["errors"], list) and len(data["errors"]) > 0:
        error = data["errors"][0]  # Get first error
        error_message = error.get("message", "Unknown error")
        error_code = error.get("code")
        error_subcode = error.get("error_subcode")
        
        error_msg = f"WhatsApp Cloud API error: {error_message}"
        if error_code:
            error_msg += f" (code: {error_code})"
        if error_subcode:
            error_msg += f" (subcode: {error_subcode})"
        
        raise WhatsAppCloudError(error_msg, error_code=error_code, error_subcode=error_subcode, full_response=data)
    
    # Check for common error codes in messages array
    # Sometimes errors are embedded in the messages response
    if "messages" in data and isinstance(data["messages"], list):
        for msg in data["messages"]:
            if "errors" in msg:
                error = msg["errors"][0] if isinstance(msg["errors"], list) else msg["errors"]
                error_message = error.get("message", "Unknown error")
                error_code = error.get("code")
                raise WhatsAppCloudError(
                    f"WhatsApp Cloud API error in message: {error_message} (code: {error_code})",
                    error_code=error_code,
                    full_response=data
                )


def _get_headers() -> Dict[str, str]:
    """Get HTTP headers for WhatsApp API requests.
    
    Security:
    - Validates that access token is set
    - Never logs the actual token value
    """
    if not WHATSAPP_ACCESS_TOKEN:
        logger.error("WHATSAPP_ACCESS_TOKEN is not set")
        raise RuntimeError("Missing WHATSAPP_ACCESS_TOKEN environment variable")
    
    # Log that token is being used (but not the value)
    logger.debug("Using WhatsApp access token", extra={
        "token_set": True,
        "token_length": len(WHATSAPP_ACCESS_TOKEN) if WHATSAPP_ACCESS_TOKEN else 0
    })
    
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _get_messages_url() -> str:
    if not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError("Missing WHATSAPP_PHONE_NUMBER_ID environment variable")
    return f"{API_BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"


def send_whatsapp_text(to_number: str, body: str) -> str:
    """Send a plain-text WhatsApp message via Cloud API.

    Args:
        to_number: Recipient phone number in international format (e.g., "+33684950535").
        body: Text content to send.

    Returns:
        The Cloud API message ID.
    """
    logger.info("Sending WhatsApp text message", extra={
        "to_number": to_number[:4] + "****",
        "body_length": len(body),
        "body_preview": body[:50] if len(body) > 50 else body
    })
    
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body},
    }

    url = _get_messages_url()
    logger.debug("WhatsApp API request", extra={
        "url": url,
        "to_number": to_number[:4] + "****",
        "has_access_token": bool(WHATSAPP_ACCESS_TOKEN),
        "has_phone_number_id": bool(WHATSAPP_PHONE_NUMBER_ID)
    })
    
    try:
        resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)
    except requests.exceptions.RequestException as e:
        logger.exception("Failed to send WhatsApp message - network error", extra={
            "to_number": to_number[:4] + "****",
            "error": str(e)
        })
        raise WhatsAppCloudError(f"Network error sending WhatsApp message: {str(e)}")

    # Try to parse JSON response even for error status codes
    try:
        data = resp.json()
    except json.JSONDecodeError:
        # If we can't parse JSON, raise generic error
        if resp.status_code >= 400:
            raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")

    # Log response status
    logger.debug("WhatsApp API response", extra={
        "status_code": resp.status_code,
        "to_number": to_number[:4] + "****",
        "has_messages": "messages" in data,
        "has_error": "error" in data or "errors" in data
    })

    # Check for errors in response (works for both 200 and 400+ status codes)
    if resp.status_code >= 400 or "error" in data or "errors" in data:
        logger.error("WhatsApp API returned error", extra={
            "status_code": resp.status_code,
            "to_number": to_number[:4] + "****",
            "response_data": str(data)[:500]  # Truncate for logging
        })
        _check_api_response(data, resp.text)

    messages = data.get("messages", [])
    if not messages:
        logger.error("No messages field in WhatsApp API response", extra={
            "to_number": to_number[:4] + "****",
            "response_data": str(data)[:500]
        })
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        logger.error("Message ID missing in WhatsApp API response", extra={
            "to_number": to_number[:4] + "****",
            "response_data": str(data)[:500]
        })
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    logger.info("WhatsApp text message sent successfully", extra={
        "to_number": to_number[:4] + "****",
        "message_id": message_id
    })
    
    # Log full response for debugging (can be removed in production)
    # This helps diagnose delivery issues
    if "contacts" in data:
        contacts = data.get("contacts", [])
        if contacts:
            contact = contacts[0]
            wa_id = contact.get("wa_id")
            input_phone = contact.get("input")
            if wa_id != input_phone:
                logger.debug("Phone number normalized", extra={
                    "input": input_phone[:4] + "****",
                    "normalized": wa_id[:4] + "****" if wa_id else None
                })
    
    return message_id


def send_whatsapp_sticker(to_number: str, media_url: str) -> str:
    """Send a sticker message via Cloud API.

    Args:
        to_number: Recipient phone number in international format.
        media_url: Public URL to the sticker file (supports WebP, PNG, etc.).

    Returns:
        The Cloud API message ID.
    """
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "sticker",
        "sticker": {"link": media_url},
    }

    url = _get_messages_url()
    resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)

    if resp.status_code >= 400:
        raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")

    # Check for errors even when status is 200
    _check_api_response(data, resp.text)

    messages = data.get("messages", [])
    if not messages:
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    # Log full response for debugging (can be removed in production)
    # This helps diagnose delivery issues
    if "contacts" in data:
        contacts = data.get("contacts", [])
        if contacts:
            contact = contacts[0]
            wa_id = contact.get("wa_id")
            input_phone = contact.get("input")
            if wa_id != input_phone:
                logger.debug("Phone number normalized", extra={
                    "input": input_phone[:4] + "****",
                    "normalized": wa_id[:4] + "****" if wa_id else None
                })
    
    return message_id


def send_whatsapp_gif(to_number: str, media_url: str, body: Optional[str] = None) -> str:
    """Send a GIF message (MP4 video) via Cloud API.
    
    For WhatsApp "GIF" messages, you send a short MP4 video (under 6 seconds,
    no audio, under ~1.5MB). WhatsApp will display it as a looping GIF.
    
    Args:
        to_number: Recipient phone number in international format.
        media_url: Public URL to the MP4 file.
        body: Optional caption text.
    
    Returns:
        The Cloud API message ID.
    """
    video: Dict[str, Any] = {"link": media_url}
    if body:
        video["caption"] = body

    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "video",
        "video": video,
    }

    url = _get_messages_url()
    resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)

    if resp.status_code >= 400:
        raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")

    # Check for errors even when status is 200
    _check_api_response(data, resp.text)

    messages = data.get("messages", [])
    if not messages:
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    # Extract message data for logging and status checks
    msg_data = messages[0]
    
    # Log full response for debugging
    logger.debug("GIF message API response", extra={
        "message_id": message_id,
        "status": msg_data.get("status") if msg_data else None
    })
    
    # Check for any warnings or status indicators
    if "status" in msg_data:
        logger.warning("Unexpected message status in response", extra={
            "status": msg_data.get("status")
        })
    
    if "contacts" in data:
        contacts = data.get("contacts", [])
        if contacts:
            contact = contacts[0]
            wa_id = contact.get("wa_id")
            input_phone = contact.get("input")
            if wa_id != input_phone:
                logger.debug("Phone number normalized", extra={
                    "input": input_phone[:4] + "****",
                    "normalized": wa_id[:4] + "****" if wa_id else None
                })
    
    return message_id


def send_whatsapp_media(to_number: str, media_url: str, body: Optional[str] = None) -> str:
    """Send a media message (e.g., image) via Cloud API.

    Sends media via WhatsApp Cloud API
    image messages pointing at a public URL. For stickers, use send_whatsapp_sticker().
    For GIFs (MP4 videos), use send_whatsapp_gif().

    Args:
        to_number: Recipient phone number in international format.
        media_url: Public URL to the media file.
        body: Optional caption text.

    Returns:
        The Cloud API message ID.
    """
    media: Dict[str, Any] = {"link": media_url}
    if body:
        media["caption"] = body

    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "image",
        "image": media,
    }

    url = _get_messages_url()
    resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)

    if resp.status_code >= 400:
        raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")

    # Check for errors even when status is 200
    _check_api_response(data, resp.text)

    messages = data.get("messages", [])
    if not messages:
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    # Log full response for debugging (can be removed in production)
    # This helps diagnose delivery issues
    if "contacts" in data:
        contacts = data.get("contacts", [])
        if contacts:
            contact = contacts[0]
            wa_id = contact.get("wa_id")
            input_phone = contact.get("input")
            if wa_id != input_phone:
                logger.debug("Phone number normalized", extra={
                    "input": input_phone[:4] + "****",
                    "normalized": wa_id[:4] + "****" if wa_id else None
                })
    
    return message_id


def send_whatsapp_audio(to_number: str, media_url: str) -> str:
    """Send an audio/voice message via Cloud API.
    
    Args:
        to_number: Recipient phone number in international format.
        media_url: Public URL to the audio file (MP3, OGG, etc.).
    
    Returns:
        The Cloud API message ID.
    """
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "audio",
        "audio": {"link": media_url},
    }

    url = _get_messages_url()
    resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)

    if resp.status_code >= 400:
        raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")

    # Check for errors even when status is 200
    _check_api_response(data, resp.text)

    messages = data.get("messages", [])
    if not messages:
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    # Extract message data for logging and status checks
    msg_data = messages[0]
    
    # Log full response for debugging
    logger.debug("Audio message API response", extra={
        "message_id": message_id,
        "status": msg_data.get("status") if msg_data else None
    })
    
    # Check for any warnings or status indicators
    if "status" in msg_data:
        logger.warning("Unexpected message status in response", extra={
            "status": msg_data.get("status")
        })
    
    if "contacts" in data:
        contacts = data.get("contacts", [])
        if contacts:
            contact = contacts[0]
            wa_id = contact.get("wa_id")
            input_phone = contact.get("input")
            if wa_id != input_phone:
                logger.debug("Phone number normalized", extra={
                    "input": input_phone[:4] + "****",
                    "normalized": wa_id[:4] + "****" if wa_id else None
                })
    
    return message_id



def send_whatsapp_interactive_list(
    to_number: str,
    header_text: str,
    body_text: str,
    button_text: str,
    options: list[dict]
) -> str:
    """Send an interactive list message via Cloud API.
    
    Args:
        to_number: Recipient phone number in international format.
        header_text: Header text for the list (max 60 chars).
        body_text: Body text explaining the list (max 1024 chars).
        button_text: Text for the button that opens the list (max 20 chars).
        options: List of option dicts, each with:
            - "id": str (unique identifier, max 200 chars)
            - "title": str (option title, max 24 chars)
            - "description": str (optional description, max 72 chars)
        Maximum 10 options allowed.
    
    Returns:
        The Cloud API message ID.
    """
    if len(options) > 10:
        raise ValueError("Maximum 10 options allowed in interactive list")
    
    # Build sections with rows
    rows = []
    for opt in options:
        row = {
            "id": opt["id"],
            "title": opt["title"]
        }
        if "description" in opt:
            row["description"] = opt["description"]
        rows.append(row)
    
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text
            },
            "body": {
                "text": body_text
            },
            "footer": {
                "text": button_text
            },
            "action": {
                "button": button_text,
                "sections": [
                    {
                        "title": "Personnages",
                        "rows": rows
                    }
                ]
            }
        }
    }
    
    url = _get_messages_url()
    resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)
    
    if resp.status_code >= 400:
        raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")
    
    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")
    
    _check_api_response(data, resp.text)
    
    messages = data.get("messages", [])
    if not messages:
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    return message_id


def send_whatsapp_interactive_buttons(
    to_number: str,
    body_text: str,
    buttons: list[dict]
) -> str:
    """Send an interactive button message via Cloud API.
    
    Args:
        to_number: Recipient phone number in international format.
        body_text: Body text explaining the buttons (max 1024 chars).
        buttons: List of button dicts, each with:
            - "id": str (unique identifier, max 256 chars)
            - "title": str (button text, max 20 chars)
        Maximum 3 buttons allowed.
    
    Returns:
        The Cloud API message ID.
    """
    if len(buttons) > 3:
        raise ValueError("Maximum 3 buttons allowed in interactive message")
    
    button_list = []
    for btn in buttons:
        button_list.append({
            "type": "reply",
            "reply": {
                "id": btn["id"],
                "title": btn["title"]
            }
        })
    
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": button_list
            }
        }
    }
    
    url = _get_messages_url()
    resp = requests.post(url, headers=_get_headers(), data=json.dumps(payload), timeout=10)
    
    if resp.status_code >= 400:
        raise WhatsAppCloudError(f"WhatsApp Cloud API error {resp.status_code}: {resp.text}")
    
    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise WhatsAppCloudError(f"Invalid JSON response from WhatsApp API: {resp.text}")
    
    _check_api_response(data, resp.text)
    
    messages = data.get("messages", [])
    if not messages:
        raise WhatsAppCloudError(f"No messages field in response: {data}", full_response=data)
    
    message_id = messages[0].get("id", "")
    if not message_id:
        raise WhatsAppCloudError(f"Message ID missing in response: {data}", full_response=data)
    
    return message_id
