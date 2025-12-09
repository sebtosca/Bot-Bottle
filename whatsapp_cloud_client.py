"""WhatsApp Cloud API client.

This module provides direct calls to Meta's WhatsApp Cloud API,
using a phone number ID and access token for sending messages.

Supports text messages, media (images/GIFs), and stickers.
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

import requests

from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID


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
    if not WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("Missing WHATSAPP_ACCESS_TOKEN environment variable")
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
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body},
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
                print(f"⚠️  Phone number normalization: {input_phone} → {wa_id}")
    
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
                print(f"⚠️  Phone number normalization: {input_phone} → {wa_id}")
    
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
    
    # Log full response for debugging
    if "contacts" in data:
        contacts = data.get("contacts", [])
        if contacts:
            contact = contacts[0]
            wa_id = contact.get("wa_id")
            input_phone = contact.get("input")
            if wa_id != input_phone:
                print(f"⚠️  Phone number normalization: {input_phone} → {wa_id}")
    
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
                print(f"⚠️  Phone number normalization: {input_phone} → {wa_id}")
    
    return message_id
