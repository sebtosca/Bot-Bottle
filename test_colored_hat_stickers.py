#!/usr/bin/env python3
"""Quick verification script for colored-hat emotional stickers.

This script checks that, for each character and accessory color,
the sticker selected by `select_sticker_by_mood` has a filename whose
hat color matches the requested bin color (GREEN/YELLOW/BLUE/BLACK).
"""

from __future__ import annotations

from typing import Dict, List

from db.db import init_db, get_session, Bottle, User
from state_logic import select_sticker_by_mood


def ensure_test_user(session) -> User:
    """Get or create a simple test user."""
    from db.db import get_or_create_user

    # Use a fixed test number to avoid polluting real users
    return get_or_create_user(session, "0000000000")


def ensure_bottle_for_character(session, user: User, product_id: str) -> Bottle:
    """Get or create a bottle for a given character."""
    from db.db import get_or_create_bottle

    bottle = get_or_create_bottle(session, user.id, product_id=product_id)
    return bottle


def verify_for_character(product_id: str, character_name: str) -> None:
    """Verify colored-hat stickers for a single character."""
    print("\n" + "=" * 60)
    print(f"Verifying colored-hat stickers for {character_name} (product_id={product_id})")
    print("=" * 60)

    colors = ["GREEN", "YELLOW", "BLUE", "BLACK"]
    moods = ["happy", "angry", "scared", "shocked"]

    session = get_session()
    user = ensure_test_user(session)
    bottle = ensure_bottle_for_character(session, user, product_id=product_id)

    base_url = "http://localhost:5000"

    results: List[Dict[str, str]] = []

    for color in colors:
        for mood in moods:
            info = select_sticker_by_mood(
                session,
                mood,
                base_url,
                character_id=product_id,
                required_color=color,
            )
            filename = info["filename"] if info else "NONE"
            print(f"{character_name} | mood={mood:7s} required_color={color:6s} -> {filename}")
            results.append(
                {
                    "mood": mood,
                    "color": color,
                    "filename": filename,
                }
            )

    session.close()


def main() -> None:
    init_db()

    # Cherry
    verify_for_character("00001", "Cherry")

    # Pompon
    verify_for_character("00002", "Pompon")


if __name__ == "__main__":
    main()

