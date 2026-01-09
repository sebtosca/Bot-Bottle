"""Webhook signature verification and validation."""

import os
import hmac
import hashlib
from typing import Optional
from flask import Request


def verify_webhook_signature(request: Request) -> bool:
    """Verify WhatsApp webhook signature.
    
    WhatsApp Cloud API sends a signature in the X-Hub-Signature-256 header.
    The signature is computed as: HMAC-SHA256(payload, app_secret)
    
    Args:
        request: Flask request object.
    
    Returns:
        True if signature is valid, False otherwise.
    
    Note:
        If WHATSAPP_APP_SECRET is not set, returns True (verification disabled).
    """
    app_secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not app_secret:
        # Signature verification disabled
        return True
    
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        return False
    
    # Extract signature (format: sha256=<signature>)
    if not signature_header.startswith("sha256="):
        return False
    
    expected_signature = signature_header[7:]  # Remove "sha256=" prefix
    
    # Get raw request body
    raw_body = request.get_data(cache=False)
    if not raw_body:
        return False
    
    # Compute expected signature
    computed_signature = hmac.new(
        app_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, expected_signature)


def verify_webhook_token(mode: Optional[str], token: Optional[str]) -> bool:
    """Verify webhook verification token (for GET requests).
    
    Args:
        mode: hub.mode parameter (should be "subscribe").
        token: hub.verify_token parameter.
    
    Returns:
        True if token matches, False otherwise.
    """
    expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN")
    if not expected_token:
        return False
    
    return mode == "subscribe" and token == expected_token
