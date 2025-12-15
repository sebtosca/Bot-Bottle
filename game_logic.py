"""Game logic for the feeding game mechanic.

This module handles:
- Emoji segmentation and validation
- Game initialization
- Fullness management
- Feeding mechanics
- Sticker selection for game states
"""

import json
import random
import emoji
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote

from db.db import Bottle, Sticker


# Global emoji segmentation cache
_emoji_segmentation = None


def load_emoji_segmentation() -> Dict[str, str]:
    """Load emoji segmentation data from JSON file.
    
    Returns:
        Dictionary mapping emoji characters to categories (GREEN, YELLOW, BLACK, BLUE).
    """
    global _emoji_segmentation
    
    if _emoji_segmentation is not None:
        return _emoji_segmentation
    
    project_root = Path(__file__).parent
    emoji_file = project_root / "emoji_segmentation_corrected.json"
    
    if not emoji_file.exists():
        print(f"⚠️  Warning: emoji_segmentation_corrected.json not found at {emoji_file}")
        return {}
    
    try:
        with open(emoji_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _emoji_segmentation = data.get("segmentation", {})
            print(f"✅ Loaded {len(_emoji_segmentation)} emoji categories")
            return _emoji_segmentation
    except Exception as e:
        print(f"❌ Error loading emoji segmentation: {e}")
        return {}


def get_emoji_category(emoji_char: str) -> str:
    """Get the recycling category for an emoji.
    
    Args:
        emoji_char: Single emoji character.
    
    Returns:
        Category string: "GREEN", "YELLOW", "BLACK", or "BLUE".
        Returns "BLACK" if not found (default non-recyclable).
    """
    segmentation = load_emoji_segmentation()
    return segmentation.get(emoji_char, "BLACK")


def extract_emojis_from_message(content: str) -> List[str]:
    """Extract all emojis from a message.
    
    Args:
        content: Message content text.
    
    Returns:
        List of emoji characters found in the message.
    """
    if not content:
        return []
    
    emoji_list = emoji.emoji_list(content)
    return [item["emoji"] for item in emoji_list]


def validate_emoji_for_color(emoji_char: str, accessory_color: str) -> bool:
    """Check if an emoji matches the required accessory color.
    
    Args:
        emoji_char: Single emoji character.
        accessory_color: Required color ("GREEN", "YELLOW", "BLACK", "BLUE").
    
    Returns:
        True if emoji category matches accessory color, False otherwise.
    """
    if not accessory_color:
        return False
    
    emoji_category = get_emoji_category(emoji_char)
    return emoji_category == accessory_color


def assign_accessory_color() -> str:
    """Randomly assign an accessory color.
    
    Returns:
        One of: "GREEN", "YELLOW", "BLACK", "BLUE"
    """
    colors = ["GREEN", "YELLOW", "BLACK", "BLUE"]
    return random.choice(colors)


def detect_rules_request(message: str) -> bool:
    """Detect if user is asking for game rules.
    
    Args:
        message: User message text.
    
    Returns:
        True if message contains French keywords for rules request.
    """
    if not message:
        return False
    
    message_lower = message.lower().strip()
    
    # French keywords for rules requests
    rules_keywords = [
        "règles",
        "règles du jeu",
        "règle",
        "comment jouer",
        "comment ça marche",
        "règlement",
        "les règles",
        "règles du",
    ]
    
    # Check if any keyword is in the message
    for keyword in rules_keywords:
        if keyword in message_lower:
            return True
    
    return False


def detect_rename_request(message: str) -> bool:
    """Detect if user wants to rename the character.
    
    Args:
        message: User message text.
    
    Returns:
        True if message contains French keywords for renaming request.
    """
    if not message:
        return False
    
    message_lower = message.lower().strip()
    
    # French keywords for renaming requests
    rename_keywords = [
        "renommer",
        "changer nom",
        "nouveau nom",
        "appeler",
        "nommer",
        "changer de nom",
        "renomme",
        "appelle",
        "nomme",
    ]
    
    # Check if any keyword is in the message
    for keyword in rename_keywords:
        if keyword in message_lower:
            return True
    
    return False


def extract_name_from_message(message: str) -> Optional[str]:
    """Extract name from message if present.
    
    Args:
        message: User message text.
    
    Returns:
        Extracted name string, or None if no valid name found.
    """
    if not message:
        return None
    
    message_clean = message.strip()
    
    # If message is too long, probably not a name
    if len(message_clean) > 50:
        return None
    
    # Check for question words - if present, probably not a name
    question_words = ["?", "what", "how", "why", "when", "where", "who", "quel", "comment", "pourquoi"]
    if any(word in message_clean.lower() for word in question_words):
        return None
    
    # If message is reasonable length and doesn't look like a question, treat as name
    if message_clean and len(message_clean) > 0:
        return message_clean
    
    return None


def get_fullness_state(fullness_level: float) -> str:
    """Get the fullness state string based on level.
    
    Args:
        fullness_level: Fullness percentage (0.0 to 100.0).
    
    Returns:
        State string: "full" (100%), "2/3" (67-99%), "1/3" (34-66%), "empty" (0-33%)
    """
    if fullness_level >= 100.0:
        return "full"
    elif fullness_level >= 67.0:
        return "2/3"
    elif fullness_level >= 34.0:
        return "1/3"
    else:
        return "empty"


def check_and_decrease_fullness(bottle: Bottle) -> bool:
    """Check if 8 hours have passed and decrease fullness if needed.
    
    Args:
        bottle: Bottle object to check.
    
    Returns:
        True if fullness was decreased, False otherwise.
    """
    if not bottle.last_fullness_decrease:
        # First time - set initial timestamp
        bottle.last_fullness_decrease = datetime.utcnow()
        return False
    
    # Check if 8 hours have passed
    time_since_decrease = datetime.utcnow() - bottle.last_fullness_decrease
    eight_hours = timedelta(hours=8)
    
    if time_since_decrease >= eight_hours:
        # Decrease by 33%
        bottle.fullness_level = max(0.0, bottle.fullness_level - 33.0)
        bottle.last_fullness_decrease = datetime.utcnow()
        return True
    
    return False


def update_fullness_after_feed(bottle: Bottle, is_correct: bool) -> Tuple[bool, bool]:
    """Update fullness after a feed attempt.
    
    Args:
        bottle: Bottle object to update.
        is_correct: True if correct emoji was fed, False otherwise.
    
    Returns:
        Tuple of (fullness_increased, feed_complete) where:
        - fullness_increased: True if fullness actually increased
        - feed_complete: True if 3 correct feeds completed
    """
    if is_correct:
        bottle.current_feed_count += 1
        bottle.last_feed_time = datetime.utcnow()
        
        # Check if we've reached 3 correct feeds
        if bottle.current_feed_count >= 3:
            # Increase fullness by 1/3 (33.33%)
            bottle.fullness_level = min(100.0, bottle.fullness_level + 33.33)
            bottle.current_feed_count = 0  # Reset counter
            return True, True
        else:
            return False, False
    else:
        # Wrong emoji - decrease fullness slightly and reset counter
        bottle.fullness_level = max(0.0, bottle.fullness_level - 5.0)
        bottle.current_feed_count = 0  # Reset on wrong feed
        return False, False


def get_fullness_sticker(accessory_color: str, fullness_state: str, base_url: str) -> Optional[Dict[str, str]]:
    """Get the appropriate fullness sticker based on color and state.
    
    Args:
        accessory_color: Color string ("GREEN", "YELLOW", "BLACK", "BLUE").
        fullness_state: State string ("full", "2/3", "1/3", "empty").
        base_url: Base URL for serving stickers.
    
    Returns:
        Dictionary with sticker info: {"url": str, "filename": str}
        Returns None if sticker not found.
    """
    color_map = {
        "GREEN": "vert",
        "YELLOW": "jaune",
        "BLACK": "noir",
        "BLUE": "bleu"
    }
    
    category_map = {
        "GREEN": "verre",
        "YELLOW": "plastique",
        "BLACK": "non_recyclable",
        "BLUE": "papier_carton"
    }
    
    state_map = {
        "full": "pleine",
        "2/3": "deux_tiers_plein",
        "1/3": "un_tiers_plein",
        "empty": "vide"
    }
    
    color_fr = color_map.get(accessory_color)
    category_fr = category_map.get(accessory_color)
    state_fr = state_map.get(fullness_state)
    
    if not all([color_fr, category_fr, state_fr]):
        return None
    
    filename = f"{color_fr}_bouteille_affamee_{category_fr}_{state_fr}.webp"
    
    # Check if file exists
    project_root = Path(__file__).parent
    sticker_path = project_root / "feeding_game_logic_stickers" / filename
    
    if not sticker_path.exists():
        print(f"⚠️  Warning: Fullness sticker not found: {filename}")
        return None
    
    # Construct URL
    encoded_filename = quote(filename, safe='')
    sticker_url = f"{base_url.rstrip('/')}/feeding-stickers/{encoded_filename}"
    
    return {
        "url": sticker_url,
        "filename": filename,
        "type": "fullness"
    }


def get_emotional_sticker(mood: str, base_url: str) -> Optional[Dict[str, str]]:
    """Get emotional sticker based on mood.
    
    Args:
        mood: Mood string (e.g., "happy", "sad", "angry").
        base_url: Base URL for serving stickers.
    
    Returns:
        Dictionary with sticker info: {"url": str, "filename": str}
        Returns None if sticker not found.
    """
    # Map mood to sticker filename
    mood_map = {
        "happy": "happy_cherry.webp",
        "sad": "scared_cherry.webp",  # Using scared as sad alternative
        "angry": "angry_cherry.webp",
        "shocked": "shocked_cherry.webp",
        "neutral": "diva_cherry.webp"
    }
    
    filename = mood_map.get(mood, "diva_cherry.webp")
    
    # Check if file exists
    project_root = Path(__file__).parent
    sticker_path = project_root / "stickers" / filename
    
    if not sticker_path.exists():
        print(f"⚠️  Warning: Emotional sticker not found: {filename}")
        return None
    
    # Construct URL
    encoded_filename = quote(filename, safe='')
    sticker_url = f"{base_url.rstrip('/')}/stickers/{encoded_filename}"
    
    return {
        "url": sticker_url,
        "filename": filename,
        "type": "emotional"
    }


def get_stickers_for_state(bottle: Bottle, base_url: str) -> Dict[str, Optional[Dict[str, str]]]:
    """Get both fullness and emotional stickers for current bottle state.
    
    Args:
        bottle: Bottle object.
        base_url: Base URL for serving stickers.
    
    Returns:
        Dictionary with "fullness" and "emotional" sticker info (or None if not found).
    """
    fullness_state = get_fullness_state(bottle.fullness_level)
    
    fullness_sticker = None
    if bottle.accessory_color:
        fullness_sticker = get_fullness_sticker(
            bottle.accessory_color,
            fullness_state,
            base_url
        )
    
    emotional_sticker = get_emotional_sticker(bottle.mood, base_url)
    
    return {
        "fullness": fullness_sticker,
        "emotional": emotional_sticker
    }


def start_game(session, bottle: Bottle, user_message: str) -> Tuple[Bottle, str]:
    """Initialize the game for a bottle.
    
    Args:
        session: Database session.
        bottle: Bottle object to initialize.
        user_message: First user message (may contain name).
    
    Returns:
        Tuple of (updated_bottle, name_prompt_message).
        If name extracted, returns bottle and empty string.
        If name needed, returns bottle and prompt message.
    """
    # Initialize fullness
    # Note: Accessory color will be assigned on first feed attempt
    bottle.fullness_level = 100.0
    bottle.last_fullness_decrease = datetime.utcnow()
    bottle.game_started = True
    bottle.current_feed_count = 0
    
    # Try to extract name from message
    # Simple extraction: if message is short and doesn't look like a question, use it as name
    message_clean = user_message.strip()
    
    # If message is reasonable length and doesn't contain question words, use as name
    if message_clean and len(message_clean) < 50:
        question_words = ["?", "what", "how", "why", "when", "where", "who", "quel", "comment", "pourquoi"]
        if not any(word in message_clean.lower() for word in question_words):
            bottle.name = message_clean
            session.add(bottle)
            session.commit()
            return bottle, ""
    
    # Otherwise, prompt for name
    prompt = "What would you like to name your character?"
    return bottle, prompt


def process_emoji_feed(session, bottle: Bottle, emojis: List[str]) -> Dict[str, any]:
    """Process emoji feeding logic.
    
    Args:
        session: Database session.
        bottle: Bottle object.
        emojis: List of emoji characters from user message.
    
    Returns:
        Dictionary with:
        - "success": bool - Whether any correct emoji was found
        - "correct_count": int - Number of correct emojis in this feed
        - "fullness_increased": bool - Whether fullness actually increased
        - "feed_complete": bool - Whether 3 feeds completed
        - "message": str - Feedback message
    """
    # Initialize color if not set (first feed)
    if not bottle.accessory_color:
        bottle.accessory_color = assign_accessory_color()
    
    # Validate against CURRENT color (what user sees in sticker)
    current_color = bottle.accessory_color
    
    correct_count = 0
    incorrect_count = 0
    
    # Process each emoji
    for emoji_char in emojis:
        if validate_emoji_for_color(emoji_char, current_color):
            correct_count += 1
        else:
            incorrect_count += 1
    
    # If we have correct emojis, process the feed
    if correct_count > 0:
        # Process each correct emoji (but only count once per message)
        # For simplicity, we'll treat the message as one feed attempt
        is_correct = correct_count > 0
        fullness_increased, feed_complete = update_fullness_after_feed(bottle, is_correct)
        
        # Rotate color AFTER processing for next feed attempt
        bottle.accessory_color = assign_accessory_color()
        
        session.add(bottle)
        session.commit()
        
        if feed_complete:
            message = f"Miam ! C’était délicieux 😋 Encore {correct_count} bon aliment à me donner 👍"
        elif correct_count > 0:
            remaining = 3 - bottle.current_feed_count
            message = f"Deliceux ! Tu m'as donné {correct_count} bon aliment! Il me faut encore {remaining} bon aliment pour me rassasier 😋"
        else:
            message = "Merci pour la nourriture !"
        
        return {
            "success": True,
            "correct_count": correct_count,
            "fullness_increased": fullness_increased,
            "feed_complete": feed_complete,
            "message": message
        }
    elif incorrect_count > 0:
        # Wrong emoji fed - track incorrect feeds
        bottle.incorrect_feed_count += 1
        bottle.current_feed_count = 0  # Reset correct feed counter on wrong feed
        
        # Check if we've reached 3 incorrect feeds
        fullness_decreased = False
        if bottle.incorrect_feed_count >= 3:
            # Decrease fullness by 1/3 (33.33%)
            bottle.fullness_level = max(0.0, bottle.fullness_level - 33.33)
            bottle.incorrect_feed_count = 0  # Reset incorrect counter
            fullness_decreased = True
        
        # Update mood to sad/angry
        if bottle.mood == "happy" or bottle.mood == "neutral":
            bottle.mood = "sad"
        
        # Rotate color AFTER processing for next feed attempt
        bottle.accessory_color = assign_accessory_color()
        
        session.add(bottle)
        session.commit()
        
        if fullness_decreased:
            message = f"Oups… ce n'est pas ce qu'il me faut 😢 Attention, après 3 mauvais aliments, ma santé baisse !"
        else:
            remaining_incorrect = 3 - bottle.incorrect_feed_count
            message = f"Oh non… ce n'est pas le bon aliment pour moi 😢 Encore {remaining_incorrect} mauvais aliment et je vais me sentir toute faible."
        
        return {
            "success": False,
            "correct_count": 0,
            "fullness_increased": False,
            "feed_complete": False,
            "message": message
        }
    else:
        return {
            "success": False,
            "correct_count": 0,
            "fullness_increased": False,
            "feed_complete": False,
            "message": "I didn't find any emojis in your message."
        }

