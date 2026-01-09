"""Secure API key handling and validation."""

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KeySpec:
    name: str
    required: bool = True
    description: str = ""


KEYS: tuple[KeySpec, ...] = (
    KeySpec("WHATSAPP_ACCESS_TOKEN", True, "WhatsApp Cloud API access token"),
    KeySpec("WHATSAPP_PHONE_NUMBER_ID", True, "WhatsApp phone number ID"),
    KeySpec("WHATSAPP_VERIFY_TOKEN", True, "Webhook verification token"),
    KeySpec("MISTRAL_API_KEY", True, "Mistral AI API key"),
    KeySpec("WHATSAPP_APP_SECRET", False, "App secret for signature verification"),
    KeySpec("WHATSAPP_ACCOUNT_ID", False, "WhatsApp business account ID"),
)


def get_key(name: str, *, required: bool = True, description: str = "") -> str | None:
    """Read env key safely. Never logs the value."""
    val = os.getenv(name)
    if required and not val:
        raise RuntimeError(
            f"{name} is required but not set. Please set it in env or .env. {description}".strip()
        )
    return val or None


def mask_key(value: str | None) -> str:
    if not value or len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def validate_api_keys() -> dict[str, dict[str, bool]]:
    """Validate required keys. Returns status map."""
    status: dict[str, dict[str, bool]] = {}
    missing: list[str] = []

    for spec in KEYS:
        val = os.getenv(spec.name)  # raw read for status
        is_set = bool(val)          # ✅ empty string is treated as missing
        status[spec.name] = {"set": is_set, "required": spec.required}
        if spec.required and not is_set:
            missing.append(spec.name)

    if missing:
        raise RuntimeError(
            f"Missing required API keys: {', '.join(missing)}. Please set them in env or .env."
        )

    # Optional: log only set/missing (no length)
    logger.info("API key validation ok", extra={"missing_required": 0})
    return status
