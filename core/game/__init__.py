"""Game logic module.

Feeding game, emoji processing, and game state management.
"""

from .feeding_game import (
    start_game,
    process_emoji_feed,
    extract_emojis_from_message,
    check_and_decrease_fullness,
    get_stickers_for_state,
    get_fullness_state,
    detect_rules_request,
    detect_rename_request,
    extract_name_from_message,
)

__all__ = [
    "start_game",
    "process_emoji_feed",
    "extract_emojis_from_message",
    "check_and_decrease_fullness",
    "get_stickers_for_state",
    "get_fullness_state",
    "detect_rules_request",
    "detect_rename_request",
    "extract_name_from_message",
]
