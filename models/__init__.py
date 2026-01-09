"""Data models and configuration.

Character models, configuration helpers, etc.
"""

from .characters import (
    get_system_prompt_for_character,
    get_character_id,
    get_character_config,
)

__all__ = [
    "get_system_prompt_for_character",
    "get_character_id",
    "get_character_config",
]
