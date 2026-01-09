"""Input validation and sanitization.

Schema-based validation with strict field control, type checks, length limits,
and sanitization helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional


# Precompiled patterns (fast + less error-prone than re.match)
_E164_RE = re.compile(r"\+[1-9]\d{1,14}$")
_PRODUCT_ID_RE = re.compile(r"\d{5}$")
_WA_MSG_ID_RE = re.compile(r"[a-zA-Z0-9._-]{5,100}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
# Safe filenames: no paths, no weird chars
_SAFE_FILENAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")  # max 255 chars


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field = field


@dataclass(frozen=True)
class FieldValidator:
    field_name: str
    required: bool = False
    field_type: Optional[type] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # regex (full match)
    allowed_values: Optional[list[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None  # may also raise ValidationError
    sanitizer: Optional[Callable[[Any], Any]] = None


class SchemaValidator:
    """Schema-based validator for structured request bodies."""

    def __init__(self, fields: list[FieldValidator], strict: bool = True):
        self._fields = {f.field_name: f for f in fields}
        self._strict = strict
        # Precompile patterns once
        self._compiled_patterns: dict[str, re.Pattern[str]] = {
            f.field_name: re.compile(f.pattern) for f in fields if f.pattern
        }

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValidationError("Invalid payload", field=None)

        if self._strict:
            extra = set(data) - set(self._fields)
            if extra:
                # Avoid leaking schema details to clients
                raise ValidationError("Unexpected fields provided", field=None)

        out: dict[str, Any] = {}

        for name, v in self._fields.items():
            value = data.get(name)

            if v.required and value is None:
                raise ValidationError(f"Missing required field '{name}'", field=name)

            if value is None:
                continue

            if v.field_type and not isinstance(value, v.field_type):
                raise ValidationError(
                    f"Field '{name}' must be {v.field_type.__name__}",
                    field=name,
                )

            if isinstance(value, str):
                if v.min_length is not None and len(value) < v.min_length:
                    raise ValidationError(
                        f"Field '{name}' must be at least {v.min_length} characters",
                        field=name,
                    )
                if v.max_length is not None and len(value) > v.max_length:
                    raise ValidationError(
                        f"Field '{name}' must be at most {v.max_length} characters",
                        field=name,
                    )

                if v.pattern:
                    pat = self._compiled_patterns[name]
                    if not pat.fullmatch(value):
                        raise ValidationError(
                            f"Field '{name}' is not in the expected format",
                            field=name,
                        )

            if v.allowed_values is not None and value not in v.allowed_values:
                raise ValidationError(f"Field '{name}' has an invalid value", field=name)

            if v.custom_validator:
                try:
                    ok = v.custom_validator(value)
                except ValidationError:
                    raise
                except Exception:
                    raise ValidationError(f"Field '{name}' failed validation", field=name)

                if ok is False:
                    raise ValidationError(f"Field '{name}' failed validation", field=name)

            if v.sanitizer:
                value = v.sanitizer(value)

            out[name] = value

        return out


def sanitize_string(value: Any, max_length: Optional[int] = None) -> str:
    """Remove control chars, trim, and optionally truncate."""
    s = value if isinstance(value, str) else str(value)
    s = _CONTROL_CHARS_RE.sub("", s).strip()
    if max_length is not None and len(s) > max_length:
        s = s[:max_length]
    return s


def sanitize_filename(filename: Any) -> str:
    """Sanitize a filename (no paths, safe chars only)."""
    if not isinstance(filename, str):
        raise ValidationError("Filename must be a string")

    name = _CONTROL_CHARS_RE.sub("", filename).strip()

    # Reject any path separators or traversal indicators early
    if any(x in name for x in ("..", "/", "\\", ":", "\x00")):
        raise ValidationError("Invalid filename")

    # Strict allowlist (prevents unicode/path weirdness)
    if not _SAFE_FILENAME_RE.fullmatch(name):
        raise ValidationError("Invalid filename")

    return name


def validate_phone_number(phone: Any) -> bool:
    """E.164: + then 2..15 digits total."""
    return isinstance(phone, str) and _E164_RE.fullmatch(phone) is not None


def validate_whatsapp_message_id(msg_id: Any) -> bool:
    """WhatsApp message IDs: 5..100 chars of [A-Za-z0-9._-]."""
    return isinstance(msg_id, str) and _WA_MSG_ID_RE.fullmatch(msg_id) is not None


def validate_product_id(product_id: Any) -> bool:
    """Product IDs: exactly 5 digits (e.g., 00001)."""
    return isinstance(product_id, str) and _PRODUCT_ID_RE.fullmatch(product_id) is not None