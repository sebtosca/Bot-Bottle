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
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote

from db.db import Bottle, Sticker, User

logger = logging.getLogger(__name__)


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
    
    # Use parent.parent to get project root (core/game -> core -> project root)
    project_root = Path(__file__).parent.parent.parent
    emoji_file = project_root / "emoji_segmentation_corrected.json"
    
    if not emoji_file.exists():
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("emoji_segmentation_corrected.json not found", extra={
            "path": str(emoji_file)
        })
        return {}
    
    try:
        with open(emoji_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _emoji_segmentation = data.get("segmentation", {})
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("Loaded emoji segmentation", extra={
                "count": len(_emoji_segmentation)
            })
            return _emoji_segmentation
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error loading emoji segmentation", extra={
            "path": str(emoji_file),
            "error": str(e)
        })
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
        State string: "full" (100%), "2/3" (66.67-99.99%), "1/3" (33.33-66.66%), "empty" (0-33.32%)
    """
    if fullness_level >= 100.0:
        return "full"
    elif fullness_level >= 66.66:
        return "2/3"
    elif fullness_level >= 33.33:
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
        - fullness_increased: True if fullness actually increased (only when 3 feeds complete)
        - feed_complete: True if 3 correct feeds completed
    """
    if is_correct:
        bottle.current_feed_count += 1
        bottle.last_feed_time = datetime.utcnow()
        
        # Only increase fullness when 3 correct feeds are reached
        if bottle.current_feed_count >= 3:
            # Increase fullness by 1/3 (33.333...%) - one level up
            # Use 100/3 to ensure exact progression: empty → 1/3 → 2/3 → full
            bottle.fullness_level = min(100.0, bottle.fullness_level + (100.0 / 3.0))
            bottle.current_feed_count = 0  # Reset counter
            bottle.incorrect_feed_count = 0  # Reset incorrect counter too
            return True, True  # fullness_increased, feed_complete
        else:
            return False, False  # No increase yet, not complete
    else:
        # Wrong emoji - decrease fullness slightly and reset counter
        bottle.fullness_level = max(0.0, bottle.fullness_level - 5.0)
        bottle.current_feed_count = 0  # Reset on wrong feed
        return False, False


def get_fullness_sticker(accessory_color: str, fullness_state: str, base_url: str, character_id: str = "00001") -> Optional[Dict[str, str]]:
    """Get the appropriate fullness sticker based on color and state.
    
    Args:
        accessory_color: Color string ("GREEN", "YELLOW", "BLACK", "BLUE").
        fullness_state: State string ("full", "2/3", "1/3", "empty").
        base_url: Base URL for serving stickers.
        character_id: Character ID ("00001" for Cherry, "00002" for Pompon).
    
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
    
    # Check if file exists in character-specific directory
    # Use parent.parent to get project root (core/game -> core -> project root)
    project_root = Path(__file__).parent.parent.parent
    from models.characters import get_character_config
    char_config = get_character_config(character_id if character_id else "00001")
    stickers_dir = project_root / char_config["feeding_sticker_dir"]
    sticker_path = stickers_dir / filename
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("get_fullness_sticker", extra={
        "character_id": character_id,
        "sticker_filename": filename,
        "directory": str(stickers_dir)
    })
    
    if not sticker_path.exists():
        logger.warning("Fullness sticker not found", extra={
            "sticker_filename": filename,
            "directory": str(stickers_dir),
            "character_name": char_config.get('name', 'Unknown'),
            "product_id": char_config.get('product_id', 'N/A')
        })
        return None
    
    # Construct URL with character_id query parameter to ensure correct directory is checked
    encoded_filename = quote(filename, safe='')
    sticker_url = f"{base_url.rstrip('/')}/feeding-stickers/{encoded_filename}?character_id={character_id}"
    
    return {
        "url": sticker_url,
        "filename": filename,
        "type": "fullness"
    }


def get_emotional_sticker(mood: str, base_url: str, character_id: str = "00001", accessory_color: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Get emotional sticker based on mood and accessory color (bin color).
    
    Args:
        mood: Mood string (e.g., "happy", "sad", "angry").
        base_url: Base URL for serving stickers.
        character_id: Character ID ("00001" for Cherry, "00002" for Pompon).
        accessory_color: Optional bin color ("GREEN", "YELLOW", "BLUE", "BLACK") to select matching hat color.
    
    Returns:
        Dictionary with sticker info: {"url": str, "filename": str}
        Returns None if sticker not found.
    """
    from models.characters import get_character_config
    
    # Map accessory color to filename color suffix
    color_map = {
        "GREEN": "green",
        "YELLOW": "yellow",
        "BLUE": "blue",
        "BLACK": "black"
    }
    color_suffix = None
    if accessory_color:
        color_suffix = color_map.get(accessory_color.upper())
    
    # Map mood to base sticker name (character-specific)
    char_config = get_character_config(character_id)
    if character_id == "00001":
        # Cherry
        mood_base_map = {
            "happy": "happy_cherry",
            "sad": "scared_cherry",
            "angry": "angry_cherry",
            "shocked": "shocked_cherry",
            "neutral": "diva_cherry",
            # Additional moods mapped to closest emotional match
            "curious": "happy_cherry",  # Curious -> happy
            "content": "happy_cherry",  # Content -> happy
            "playful": "happy_cherry",  # Playful -> happy
            "excited": "happy_cherry",  # Excited -> happy
        }
    elif character_id == "00002":
        # Pompon
        mood_base_map = {
            "happy": "happy_cider",
            "sad": "scared_cider",
            "angry": "angry_cider",
            "shocked": "shocked_cider",
            "neutral": "happy_cider",  # Default to happy for Pompon
            # Additional moods mapped to closest emotional match
            "curious": "happy_cider",  # Curious -> happy
            "content": "happy_cider",  # Content -> happy
            "playful": "happy_cider",  # Playful -> happy
            "excited": "happy_cider",  # Excited -> happy
        }
    else:
        # Default to Cherry
        mood_base_map = {
            "happy": "happy_cherry",
            "sad": "scared_cherry",
            "angry": "angry_cherry",
            "shocked": "shocked_cherry",
            "neutral": "diva_cherry",
            # Additional moods mapped to closest emotional match
            "curious": "happy_cherry",  # Curious -> happy
            "content": "happy_cherry",  # Content -> happy
            "playful": "happy_cherry",  # Playful -> happy
            "excited": "happy_cherry",  # Excited -> happy
        }
    
    base_name = mood_base_map.get(mood, mood_base_map.get("neutral", "happy_cherry"))
    
    # Construct filename with color if available
    if color_suffix:
        filename = f"{base_name}_{color_suffix}.webp"
    else:
        # Fallback: try green first, then any available color
        filename = f"{base_name}_green.webp"
    
    # Check if file exists in character-specific directory
    # Use parent.parent to get project root (core/game -> core -> project root)
    project_root = Path(__file__).parent.parent.parent
    stickers_dir = project_root / char_config["sticker_dir"]
    sticker_path = stickers_dir / filename
    
    # If file doesn't exist and we have a color, try other colors as fallback
    if not sticker_path.exists() and color_suffix:
        for fallback_color in ["green", "yellow", "blue", "black"]:
            if fallback_color != color_suffix:
                fallback_filename = f"{base_name}_{fallback_color}.webp"
                fallback_path = stickers_dir / fallback_filename
                if fallback_path.exists():
                    filename = fallback_filename
                    sticker_path = fallback_path
                    break
    
    # If still not found, try without color suffix (for legacy stickers if any)
    if not sticker_path.exists():
        legacy_filename = f"{base_name}.webp"
        legacy_path = stickers_dir / legacy_filename
        if legacy_path.exists():
            filename = legacy_filename
            sticker_path = legacy_path
        else:
            logger.warning("Emotional sticker not found", extra={
                "sticker_filename": filename,
                "color_suffix": color_suffix
            })
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
    
    # Get character_id from bottle's product_id
    character_id = bottle.product_id if hasattr(bottle, 'product_id') else "00001"
    
    # Debug logging
    logger.debug("get_stickers_for_state", extra={
        "bottle_product_id": bottle.product_id,
        "character_id": character_id,
        "fullness_state": fullness_state
    })
    
    fullness_sticker = None
    if bottle.accessory_color:
        fullness_sticker = get_fullness_sticker(
            bottle.accessory_color,
            fullness_state,
            base_url,
            character_id=character_id
        )
        if fullness_sticker:
            logger.debug("Fullness sticker selected", extra={
                "sticker_filename": fullness_sticker.get('filename', 'N/A'),
                "character_id": character_id
            })
        else:
            logger.warning("No fullness sticker found", extra={
                "character_id": character_id,
                "color": bottle.accessory_color,
                "state": fullness_state
            })
    
    emotional_sticker = get_emotional_sticker(
        bottle.mood, base_url, character_id=character_id, accessory_color=bottle.accessory_color
    )
    
    return {
        "fullness": fullness_sticker,
        "emotional": emotional_sticker
    }


def calculate_and_record_savings(session, bottle_id: int) -> Dict[str, float]:
    """Calculate and record money and CO2 savings when a bottle is returned.
    
    Args:
        session: Database session.
        bottle_id: Bottle ID that was returned.
    
    Returns:
        Dictionary with 'money_saved' and 'co2_saved' values.
    """
    from models.characters import get_character_config
    
    bottle = session.query(Bottle).filter_by(id=bottle_id).first()
    if not bottle:
        return {"money_saved": 0.0, "co2_saved": 0.0}
    
    user = session.query(User).filter_by(id=bottle.user_id).first()
    if not user:
        return {"money_saved": 0.0, "co2_saved": 0.0}
    
    # Get character-specific savings values
    char_config = get_character_config(bottle.product_id)
    money_per_bottle = char_config.get("money_per_bottle", 0.10)  # Default €0.10
    co2_per_bottle = char_config.get("co2_per_bottle", 0.5)  # Default 0.5 kg
    
    # Calculate savings
    money_saved = money_per_bottle
    co2_saved = co2_per_bottle
    
    # Update bottle savings
    bottle.money_saved = money_saved
    bottle.co2_saved = co2_saved
    session.add(bottle)
    
    # Update user total savings
    user.total_money_saved += money_saved
    user.total_co2_saved += co2_saved
    session.add(user)
    
    session.commit()
    
    return {
        "money_saved": money_saved,
        "co2_saved": co2_saved
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
    
    # Calculate net feed count (cancel out mixed feeds)
    net_feed_count = correct_count - incorrect_count
    
    # Process feeds based on net count
    if net_feed_count > 0:
        # Net positive: process as correct feeds
        fullness_increased = False
        feed_complete = False
        
        # Process each correct feed
        for _ in range(net_feed_count):
            inc, complete = update_fullness_after_feed(bottle, True)
            if inc:
                fullness_increased = True
            if complete:
                feed_complete = True
        
        # Rotate color AFTER processing for next feed attempt
        bottle.accessory_color = assign_accessory_color()
        
        session.add(bottle)
        session.commit()
        
        # Get current fullness state for feedback
        current_state = get_fullness_state(bottle.fullness_level)
        
        if feed_complete:
            message = f"Miam ! C’était délicieux 😋 Tu m'as donné 3 bons aliments, je suis maintenant {current_state}!"
        else:
            remaining = 3 - bottle.current_feed_count
            if remaining == 1:
                message = f"Délicieux ! Tu m'as donné {net_feed_count} bon aliment! Il me faut encore {remaining} bon aliment pour me rassasier 😋"
            else:
                message = f"Délicieux ! Tu m'as donné {net_feed_count} bon aliment! Il me faut encore {remaining} bons aliments pour me rassasier 😋"
        
        return {
            "success": True,
            "correct_count": net_feed_count,
            "fullness_increased": fullness_increased,
            "feed_complete": feed_complete,
            "message": message
        }
    elif net_feed_count < 0:
        # Net negative: process as incorrect feeds
        fullness_decreased = False
        
        # Process each incorrect feed
        for _ in range(abs(net_feed_count)):
            bottle.incorrect_feed_count += 1
            
            # Check if we've reached 3 incorrect feeds
            if bottle.incorrect_feed_count >= 3:
                # Decrease fullness by 1/3 (33.33%) - one level down
                bottle.fullness_level = max(0.0, bottle.fullness_level - 33.33)
                bottle.incorrect_feed_count = 0  # Reset incorrect counter
                bottle.current_feed_count = 0  # Reset correct counter too
                fullness_decreased = True
        
        # Reset correct feed counter on incorrect feed (if not already reset by level down)
        if not fullness_decreased:
            bottle.current_feed_count = 0
        
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
            if remaining_incorrect == 1:
                message = f"Oh non… ce n'est pas le bon aliment pour moi 😢 Encore {remaining_incorrect} mauvais aliment et je vais me sentir toute faible."
            else:
                message = f"Oh non… ce n'est pas le bon aliment pour moi 😢 Encore {remaining_incorrect} mauvais aliments et je vais me sentir toute faible."
        
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

