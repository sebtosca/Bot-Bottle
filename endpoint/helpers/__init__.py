"""Helper functions for the endpoint module."""

from .slang import apply_breton_slang, apply_norman_slang
from .notifications import check_and_notify_hungry_characters

__all__ = [
    "apply_breton_slang",
    "apply_norman_slang",
    "check_and_notify_hungry_characters",
]
