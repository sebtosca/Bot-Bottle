"""State management logic for BotBottle.

This module handles:
- Message type classification
- Bottle state updates based on interactions
- Personality evolution
"""

from typing import List, Optional
import re
import emoji
import random
from urllib.parse import quote

from db.db import Interaction, Bottle, Sticker


def classify_message_type(content: str, num_media: int = 0, media_type: str = "") -> str:
    """Classify the type of message.
    
    Args:
        content: Message content text.
        num_media: Number of media attachments (0 or 1 for WhatsApp Cloud API).
        media_type: Media content type (MIME type from WhatsApp Cloud API).
    
    Returns:
        Message type: "text", "emoji", "sticker", "image", "video", "audio", "gif", or "mixed".
    """
    # Check for media first
    if num_media > 0:
        media_type_lower = media_type.lower()
        if "sticker" in media_type_lower:
            return "sticker"
        elif "image" in media_type_lower:
            if "gif" in media_type_lower:
                return "gif"
            return "image"
        elif "video" in media_type_lower:
            return "video"
        elif "audio" in media_type_lower or "voice" in media_type_lower:
            return "audio"
        else:
            return "media"
    
    # Check for emoji-only or emoji-heavy messages
    if content:
        # Count emojis in content
        emoji_list = emoji.emoji_list(content)
        emoji_count = len(emoji_list)
        text_without_emoji = emoji.replace_emoji(content, replace="")
        # Remove all whitespace to check if there's actual text
        text_length = len(text_without_emoji.strip())
        
        # If mostly emojis or only emojis
        if emoji_count > 0:
            if text_length == 0:
                return "emoji"  # Only emojis (no text characters)
            elif text_length > 0:
                # Mixed: has both text and emoji
                # Consider it "mixed" if emojis are a noticeable part
                total_length = len(content)
                # Count non-emoji, non-whitespace characters
                actual_text_chars = len([c for c in text_without_emoji if c.strip()])
                if actual_text_chars == 0:
                    return "emoji"  # Only emojis and whitespace
                # If emoji ratio is significant or message is short with emojis
                emoji_ratio = emoji_count / total_length if total_length > 0 else 0
                if emoji_ratio >= 0.15 or (total_length < 20 and emoji_count >= 1 and actual_text_chars > 0):
                    return "mixed"  # Mixed text and emoji
    
    # Default to text
    return "text"


def update_bottle_state(
    session,
    bottle: Bottle,
    recent_interactions: List[Interaction],
) -> Bottle:
    """Update bottle state based on recent interactions.
    
    This function deterministically updates the bottle's mood and personality_level
    based on the types and frequency of interactions.
    
    Args:
        bottle: Bottle object to update.
        recent_interactions: List of recent interactions for this bottle.
    
    Returns:
        Updated Bottle object (already committed to database).
    """
    from datetime import datetime
    
    if not recent_interactions:
        return bottle
    
    # Count interaction types
    interaction_counts = {
        "text": 0,
        "emoji": 0,
        "sticker": 0,
        "image": 0,
        "video": 0,
        "audio": 0,
        "gif": 0,
        "mixed": 0,
    }
    
    for interaction in recent_interactions:
        msg_type = interaction.message_type
        if msg_type in interaction_counts:
            interaction_counts[msg_type] += 1
    
    total_interactions = len(recent_interactions)
    
    # Update mood based on interaction patterns
    # More diverse interactions = happier
    unique_types = sum(1 for count in interaction_counts.values() if count > 0)
    
    if unique_types >= 4:
        new_mood = "happy"
    elif unique_types >= 2:
        new_mood = "content"
    elif interaction_counts["emoji"] > interaction_counts["text"]:
        new_mood = "playful"
    elif interaction_counts["sticker"] + interaction_counts["gif"] > 0:
        new_mood = "excited"
    elif total_interactions <= 2:
        new_mood = "neutral"  # Stay neutral for first 2 interactions
    else:
        new_mood = "curious"
    
    # Update personality_level based on engagement
    # More interactions = higher personality level (0-10 scale)
    if total_interactions >= 20:
        new_personality_level = min(10, 5 + (total_interactions // 10))
    elif total_interactions >= 10:
        new_personality_level = min(8, 3 + (total_interactions // 5))
    elif total_interactions >= 5:
        new_personality_level = min(5, 1 + (total_interactions // 2))
    else:
        new_personality_level = 0
    
    # Apply updates
    bottle.mood = new_mood
    bottle.personality_level = new_personality_level
    bottle.updated_at = datetime.utcnow()
    
    return bottle


def select_sticker_by_mood(
    session,
    mood: str,
    base_url: str = "http://localhost:5000"
) -> Optional[dict]:
    """Select an appropriate sticker based on bottle mood.
    
    Args:
        session: Database session.
        mood: Current bottle mood (e.g., "happy", "neutral", "excited").
        base_url: Base URL for serving stickers (default: Flask local server).
                  Should be set to Cloudflare Tunnel URL in production (e.g., https://xxx.trycloudflare.com),
                  or other tunnel service URL if using one (e.g., https://xxx.ngrok-free.app).
    
    Returns:
        Dictionary with sticker info: {"url": str, "filename": str, "description": str}
        Returns None if no matching sticker found.
        
    Note:
        Prefers WebP format (supported by WhatsApp Cloud API) for better compression.
    """
    if not session:
        return None
    
    try:
        # Query for stickers matching mood
        # Match stickers where mood_tags contains the current mood
        # or mood_tags is None/empty (universal stickers)
        
        # Query only stickers (not GIFs)
        all_stickers = session.query(Sticker).filter(
            Sticker.media_type == "sticker"
        ).all()
        matching_stickers = []
        
        for sticker in all_stickers:
            if not sticker.mood_tags or sticker.mood_tags.strip() == "":
                # Universal sticker (no mood restriction)
                matching_stickers.append(sticker)
            else:
                # Check if mood is in the comma-separated list
                mood_list = [m.strip().lower() for m in sticker.mood_tags.split(",")]
                if mood.lower() in mood_list:
                    matching_stickers.append(sticker)
        
        if not matching_stickers:
            # Fallback: try to find any sticker
            fallback_sticker = session.query(Sticker).filter(
                Sticker.media_type == "sticker"
            ).first()
            if fallback_sticker:
                matching_stickers = [fallback_sticker]
            else:
                return None
        
        # Prefer WebP over PNG (WhatsApp Cloud API supports WebP, which is more efficient)
        # Sort: WebP first, then PNG, then JPEG last
        def sort_key(sticker):
            filename_lower = sticker.filename.lower()
            if filename_lower.endswith('.webp'):
                return 0  # WebP is preferred (smaller file size, better quality)
            elif filename_lower.endswith('.png'):
                return 1
            elif filename_lower.endswith(('.jpg', '.jpeg')):
                return 2
            else:
                return 3  # Unknown format
        
        # Sort and select (prefer WebP)
        matching_stickers.sort(key=sort_key)
        selected = matching_stickers[0]  # Take first (best format)
        
        # Construct full URL (include /stickers/ path)
        # URL-encode the filename to handle spaces and special characters
        encoded_filename = quote(selected.filename, safe='')
        sticker_url = f"{base_url.rstrip('/')}/stickers/{encoded_filename}"
        
        return {
            "url": sticker_url,
            "filename": selected.filename,
            "description": selected.description or "",
            "id": selected.id
        }
        
    except Exception as e:
        print(f"Error selecting sticker: {e}")
        return None


def get_recent_bot_response_types(
    session,
    bottle_id: int,
    limit: int = 10
) -> List[str]:
    """Get recent bot response types from interactions.
    
    This function analyzes recent bot responses (from_user="false") to determine
    what types of responses were sent (text_only, text_sticker, or gif_only).
    
    Args:
        session: Database session.
        bottle_id: Bottle ID to get responses for.
        limit: Maximum number of recent interactions to analyze.
    
    Returns:
        List of response type strings: ["text_only", "text_sticker", "gif_only", ...]
        Ordered from oldest to newest.
    """
    if not session:
        return []
    
    try:
        # Get recent bot responses (from_user="false")
        recent_bot_responses = (
            session.query(Interaction)
            .filter_by(bottle_id=bottle_id, from_user="false")
            .order_by(Interaction.created_at.desc())
            .limit(limit)
            .all()
        )
        
        # Reverse to get oldest first
        recent_bot_responses.reverse()
        
        response_types = []
        i = 0
        while i < len(recent_bot_responses):
            current = recent_bot_responses[i]
            
            # Check if this is a GIF response
            if current.message_type == "gif":
                response_types.append("gif_only")
                i += 1
            # Check if this is a sticker response
            elif current.message_type == "sticker":
                # Look back to see if there was a text message just before this
                # (within a short time window, e.g., 5 seconds)
                if i > 0:
                    prev = recent_bot_responses[i - 1]
                    time_diff = (current.created_at - prev.created_at).total_seconds()
                    if prev.message_type == "text" and time_diff < 5.0:
                        response_types.append("text_sticker")
                        i += 2  # Skip both text and sticker
                        continue
                
                # Sticker without preceding text (shouldn't happen with new logic, but handle gracefully)
                response_types.append("text_sticker")  # Assume text was sent
                i += 1
            # Check if this is a text response
            elif current.message_type == "text":
                # Look ahead to see if there's a sticker right after
                if i + 1 < len(recent_bot_responses):
                    next_resp = recent_bot_responses[i + 1]
                    time_diff = (next_resp.created_at - current.created_at).total_seconds()
                    if next_resp.message_type == "sticker" and time_diff < 5.0:
                        response_types.append("text_sticker")
                        i += 2  # Skip both text and sticker
                        continue
                
                # Text without following sticker
                response_types.append("text_only")
                i += 1
            else:
                # Unknown message type, skip it
                i += 1
        
        return response_types
        
    except Exception as e:
        print(f"Error getting recent bot response types: {e}")
        return []


def select_response_type(
    session,
    bottle_id: int,
    mood: str,
    has_sticker: bool = True,
    has_gif: bool = True,
    user_sentiment: Optional[dict[str, any]] = None
) -> str:
    """Select response type based on mood, sentiment analysis, and rotation logic.
    
    This function implements a smart rotation system that:
    - Uses mood to influence base probabilities
    - Adjusts probabilities based on user message sentiment (emotion and intensity)
    - Tracks recent response types to avoid repetition
    - Ensures variety in responses
    
    Args:
        session: Database session.
        bottle_id: Bottle ID to get response history for.
        mood: Current bottle mood (e.g., "happy", "neutral", "excited").
        has_sticker: Whether stickers are available for this mood.
        has_gif: Whether GIFs are available for this mood.
        user_sentiment: Optional dict with sentiment analysis:
            {
                "emotion": str,
                "intensity": float (0.0-1.0),
                "should_send_media": bool
            }
    
    Returns:
        Response type string: "text_only", "text_sticker", or "gif_only"
    """
    # Get recent bot response types
    recent_types = get_recent_bot_response_types(session, bottle_id, limit=8)
    
    # Count recent response types
    type_counts = {
        "text_only": 0,
        "text_sticker": 0,
        "gif_only": 0
    }
    
    for resp_type in recent_types:
        if resp_type in type_counts:
            type_counts[resp_type] += 1
    
    # Define mood-based base probabilities (increased media probabilities)
    mood_probs = {
        "happy": {"text_only": 0.15, "text_sticker": 0.35, "gif_only": 0.5},
        "excited": {"text_only": 0.1, "text_sticker": 0.3, "gif_only": 0.6},
        "playful": {"text_only": 0.2, "text_sticker": 0.4, "gif_only": 0.4},
        "content": {"text_only": 0.2, "text_sticker": 0.4, "gif_only": 0.4},
        "neutral": {"text_only": 0.3, "text_sticker": 0.35, "gif_only": 0.35},
        "curious": {"text_only": 0.25, "text_sticker": 0.4, "gif_only": 0.35},
    }
    
    # Get base probabilities for current mood (default to neutral if unknown)
    base_probs = mood_probs.get(mood.lower(), mood_probs["neutral"]).copy()
    
    # Adjust probabilities based on sentiment analysis
    if user_sentiment:
        sentiment_emotion = user_sentiment.get("emotion", "neutral")
        sentiment_intensity = user_sentiment.get("intensity", 0.3)
        should_send_media = user_sentiment.get("should_send_media", False)
        
        # Map sentiment emotion to media preferences
        # High intensity + positive emotions favor GIFs
        # Medium intensity favors text+sticker
        # Low intensity/neutral favors text
        
        if sentiment_intensity > 0.7:  # High intensity
            if sentiment_emotion in ["happy", "excited", "playful", "surprised"]:
                # Strong positive emotions → strongly favor GIFs
                base_probs["gif_only"] = min(0.8, base_probs["gif_only"] + 0.3)
                base_probs["text_sticker"] = min(0.2, base_probs["text_sticker"] + 0.1)
                base_probs["text_only"] = max(0.0, base_probs["text_only"] - 0.4)
            elif sentiment_emotion in ["sad", "angry", "frustrated"]:
                # Strong negative emotions → favor GIFs but also text+sticker
                base_probs["gif_only"] = min(0.6, base_probs["gif_only"] + 0.2)
                base_probs["text_sticker"] = min(0.3, base_probs["text_sticker"] + 0.1)
                base_probs["text_only"] = max(0.1, base_probs["text_only"] - 0.3)
            else:
                # Other strong emotions
                base_probs["gif_only"] = min(0.6, base_probs["gif_only"] + 0.2)
                base_probs["text_sticker"] = min(0.3, base_probs["text_sticker"] + 0.1)
                base_probs["text_only"] = max(0.1, base_probs["text_only"] - 0.3)
        elif sentiment_intensity > 0.4:  # Medium intensity
            # Moderate emotions → favor text+sticker and some GIFs
            base_probs["text_sticker"] = min(0.5, base_probs["text_sticker"] + 0.15)
            base_probs["gif_only"] = min(0.4, base_probs["gif_only"] + 0.1)
            base_probs["text_only"] = max(0.1, base_probs["text_only"] - 0.25)
        else:  # Low intensity
            # Weak emotions → slightly favor text but still include media
            base_probs["text_only"] = min(0.5, base_probs["text_only"] + 0.1)
            base_probs["text_sticker"] = max(0.2, base_probs["text_sticker"] - 0.05)
            base_probs["gif_only"] = max(0.2, base_probs["gif_only"] - 0.05)
        
        # If sentiment explicitly suggests media, boost media probabilities
        if should_send_media:
            media_boost = 0.2
            base_probs["gif_only"] = min(0.7, base_probs["gif_only"] + media_boost * 0.6)
            base_probs["text_sticker"] = min(0.5, base_probs["text_sticker"] + media_boost * 0.4)
            base_probs["text_only"] = max(0.0, base_probs["text_only"] - media_boost)
    
    # Adjust probabilities based on availability
    if not has_sticker:
        # If no sticker available, redistribute its probability
        sticker_prob = base_probs["text_sticker"]
        base_probs["text_sticker"] = 0
        base_probs["text_only"] += sticker_prob * 0.6
        base_probs["gif_only"] += sticker_prob * 0.4
    
    if not has_gif:
        # If no GIF available, redistribute its probability
        gif_prob = base_probs["gif_only"]
        base_probs["gif_only"] = 0
        base_probs["text_only"] += gif_prob * 0.5
        base_probs["text_sticker"] += gif_prob * 0.5
    
    # Normalize probabilities (in case we adjusted them)
    total = sum(base_probs.values())
    if total > 0:
        for key in base_probs:
            base_probs[key] /= total
    
    # Adjust probabilities based on recent history (reduce probability of recently used types)
    # This implements rotation to ensure variety
    adjustment_factor = 0.3  # Reduce probability by 30% for each recent occurrence
    
    adjusted_probs = base_probs.copy()
    for resp_type, count in type_counts.items():
        if count > 0 and resp_type in adjusted_probs:
            # Reduce probability based on how many times it was used recently
            reduction = min(adjustment_factor * count, 0.8)  # Cap at 80% reduction
            adjusted_probs[resp_type] *= (1 - reduction)
    
    # Normalize again after adjustments
    total = sum(adjusted_probs.values())
    if total > 0:
        for key in adjusted_probs:
            adjusted_probs[key] /= total
    else:
        # Fallback: if all probabilities became 0, use equal distribution
        available_types = [t for t in adjusted_probs.keys() if adjusted_probs[t] > 0 or base_probs[t] > 0]
        if available_types:
            for key in adjusted_probs:
                adjusted_probs[key] = 1.0 / len(available_types) if key in available_types else 0.0
        else:
            # Ultimate fallback: equal distribution of all types
            for key in adjusted_probs:
                adjusted_probs[key] = 1.0 / len(adjusted_probs)
    
    # Select response type using weighted random choice
    response_types = list(adjusted_probs.keys())
    probabilities = [adjusted_probs[t] for t in response_types]
    
    selected = random.choices(response_types, weights=probabilities, k=1)[0]
    
    # Log selection details for debugging
    if user_sentiment:
        print(f"   Sentiment-based adjustment applied:")
        print(f"      Emotion: {user_sentiment.get('emotion', 'N/A')}")
        print(f"      Intensity: {user_sentiment.get('intensity', 0.0):.2f}")
        print(f"      Final probabilities: {adjusted_probs}")
    
    return selected


def select_gif_by_mood(
    session,
    mood: str,
    base_url: str = "http://localhost:5000"
) -> Optional[dict]:
    """Select an appropriate GIF based on bottle mood.
    
    Args:
        session: Database session.
        mood: Current bottle mood (e.g., "happy", "neutral", "excited").
        base_url: Base URL for serving GIF/MP4 media via Flask.
    
    Returns:
        Dictionary with GIF info:
            {
                "url": str,         # Full HTTPS URL to /gifs/<filename>
                "filename": str,    # Local filename in GIF directory
                "description": str,
                "id": int,
                "media_type": "gif"
            }
        Returns None if no matching GIF found.
    """
    if not session:
        return None
    
    try:
        # Query only GIFs (not stickers)
        all_gifs = session.query(Sticker).filter(
            Sticker.media_type == "gif"
        ).all()
        matching_gifs = []
        
        for gif in all_gifs:
            if not gif.mood_tags or gif.mood_tags.strip() == "":
                # Universal GIF (no mood restriction)
                matching_gifs.append(gif)
            else:
                # Check if mood is in the comma-separated list
                mood_list = [m.strip().lower() for m in gif.mood_tags.split(",")]
                if mood.lower() in mood_list:
                    matching_gifs.append(gif)
        
        if not matching_gifs:
            # Fallback: try to find any GIF
            fallback_gif = session.query(Sticker).filter(
                Sticker.media_type == "gif"
            ).first()
            if fallback_gif:
                matching_gifs = [fallback_gif]
            else:
                return None
        
        # Select random GIF from matching ones
        import random
        selected = random.choice(matching_gifs)
        
        # Build URL from local filename using the /gifs/<filename> route.
        # For WhatsApp, the underlying file SHOULD be an MP4 that meets
        # their GIF requirements (short, muted, < ~1.5MB).
        if not selected.filename:
            # Legacy safety: if filename is missing, we cannot construct URL.
            return None
        
        # URL-encode the filename to handle spaces and special characters
        encoded_filename = quote(selected.filename, safe='')
        gif_url = f"{base_url.rstrip('/')}/gifs/{encoded_filename}"
        
        return {
            "url": gif_url,
            "filename": selected.filename,
            "description": selected.description or "",
            "id": selected.id,
            "media_type": "gif"
        }
        
    except Exception as e:
        print(f"Error selecting GIF: {e}")
        return None

