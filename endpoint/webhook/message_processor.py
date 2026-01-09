"""Message processor that handles the actual business logic.

This module contains all the heavy processing that was moved out of the
fast webhook handler. It processes JobPayload and performs:
- Database operations
- LLM calls
- WhatsApp API calls
- Game logic
- etc.
"""

import logging
import time
import re
from typing import Optional

from .models import JobPayload
from db.db import (
    get_session, get_or_create_user, get_or_create_bottle,
    get_active_bottle, create_interaction, get_recent_interactions
)
from core.game import (
    start_game, process_emoji_feed, extract_emojis_from_message,
    check_and_decrease_fullness, get_stickers_for_state, get_fullness_state,
    detect_rules_request, detect_rename_request, extract_name_from_message
)
from core.state import (
    classify_message_type, update_bottle_state, select_sticker_by_mood,
    select_gif_by_mood, select_money_gif, select_response_type
)
from core.points import (
    award_points, check_daily_engagement, calculate_milestone_bonus, get_user_stats
)
from llm.llama_client import generate_reply, detect_emotion_from_message
from services.whatsapp import (
    send_whatsapp_text, send_whatsapp_media, send_whatsapp_sticker,
    send_whatsapp_gif, send_whatsapp_audio, send_whatsapp_interactive_list,
    send_whatsapp_interactive_buttons
)
from services.whatsapp.client import WhatsAppCloudError
from models.characters import (
    get_system_prompt_for_character, get_character_id, get_character_config
)
from features.receipt import verify_receipt
from features.stats import (
    send_stats_display, send_text_stats_fallback, generate_stats_image
)
import sys
from pathlib import Path
# Add endpoint directory to path for helpers
_endpoint_dir = Path(__file__).parent.parent
if str(_endpoint_dir) not in sys.path:
    sys.path.insert(0, str(_endpoint_dir))
# Add parent directory (project root) to path for config
_parent_dir = Path(__file__).parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
from helpers.notifications import check_and_notify_hungry_characters

# Import config - try multiple ways to ensure it works
try:
    from config import PUBLIC_BASE_URL, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
except ImportError as e:
    # Fallback: try importing from parent directory
    import importlib.util
    config_path = _parent_dir / "config.py"
    if config_path.exists():
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        PUBLIC_BASE_URL = config_module.PUBLIC_BASE_URL
        WHATSAPP_ACCESS_TOKEN = config_module.WHATSAPP_ACCESS_TOKEN
        WHATSAPP_PHONE_NUMBER_ID = config_module.WHATSAPP_PHONE_NUMBER_ID
    else:
        raise ImportError(f"Could not import config: {e}")

logger = logging.getLogger(__name__)

# Verify imports are available
if 'WHATSAPP_PHONE_NUMBER_ID' not in globals():
    logger.error("WHATSAPP_PHONE_NUMBER_ID not imported - attempting direct import")
    try:
        import config
        WHATSAPP_PHONE_NUMBER_ID = config.WHATSAPP_PHONE_NUMBER_ID
        WHATSAPP_ACCESS_TOKEN = config.WHATSAPP_ACCESS_TOKEN
        PUBLIC_BASE_URL = config.PUBLIC_BASE_URL
        logger.info("Successfully imported config via direct import")
    except Exception as e:
        logger.exception(f"Failed to import config: {e}")
        raise


def process_whatsapp_message(payload: JobPayload) -> None:
    """Process a WhatsApp message job.
    
    This function contains all the business logic that processes incoming
    WhatsApp messages. It's called by the worker after a message is enqueued.
    
    Args:
        payload: Job payload containing message data.
    """
    logger.info("Processing WhatsApp message", extra={
        "request_id": payload.request_id,
        "message_id": payload.message_id,
        "from_number": payload.from_number[:4] + "****",
        "message_type": payload.message_type,
        "product_id": payload.product_id,
        "body_preview": (payload.body or "")[:50] if payload.body else None
    })
    
    # Check WhatsApp credentials at start of processing
    if not WHATSAPP_ACCESS_TOKEN:
        logger.error("WHATSAPP_ACCESS_TOKEN is not set - cannot send messages", extra={
            "request_id": payload.request_id
        })
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not set - cannot send WhatsApp messages")
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WHATSAPP_PHONE_NUMBER_ID is not set - cannot send messages", extra={
            "request_id": payload.request_id
        })
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is not set - cannot send WhatsApp messages")
    
    logger.debug("WhatsApp credentials verified", extra={
        "request_id": payload.request_id,
        "has_access_token": bool(WHATSAPP_ACCESS_TOKEN),
        "has_phone_number_id": bool(WHATSAPP_PHONE_NUMBER_ID)
    })
    
    session = get_session()
    try:
        # Get or create user
        user = get_or_create_user(session, payload.from_number)
        if not user:
            logger.error("Failed to get or create user", extra={
                "request_id": payload.request_id,
                "from_number": payload.from_number[:4] + "****"
            })
            return
        
        # Determine product_id (from message or default)
        product_id = payload.product_id or "00001"
        
        # Handle special commands
        message_body = payload.body or ""
        
        # Character switching
        if message_body.startswith("[SWITCH_CHARACTER:"):
            match = re.search(r"\[SWITCH_CHARACTER:(\d+)\]", message_body)
            if match:
                new_product_id = match.group(1)
                product_id = new_product_id
                logger.info("Character switch requested", extra={
                    "request_id": payload.request_id,
                    "new_product_id": new_product_id
                })
        
        # Stats button
        if message_body.startswith("[STATS_BUTTON:"):
            stats = get_user_stats(session, user.id)
            if stats:
                send_stats_display(session, user.id, payload.from_number, PUBLIC_BASE_URL or "http://localhost:5000")
            else:
                send_text_stats_fallback(session, user.id, payload.from_number)
            session.commit()
            return
        
        # Feed character button
        if message_body.startswith("[FEED_CHARACTER:"):
            match = re.search(r"\[FEED_CHARACTER:(\d+)\]", message_body)
            if match:
                feed_product_id = match.group(1)
                bottle = get_active_bottle(session, user.id, feed_product_id)
                if bottle:
                    # Prompt user to send emojis
                    char_config = get_character_config(feed_product_id)
                    send_whatsapp_text(
                        payload.from_number,
                        f"Envoie-moi des emojis pour nourrir {char_config['name']} ! 🍎🥤"
                    )
                session.commit()
                return
        
        # Get or create bottle for this character
        bottle = get_or_create_bottle(session, user.id, product_id)
        if not bottle:
            logger.error("Failed to get or create bottle", extra={
                "request_id": payload.request_id,
                "user_id": user.id,
                "product_id": product_id
            })
            return
        
        # Check and decrease fullness (time-based)
        check_and_decrease_fullness(bottle)
        session.add(bottle)
        
        # Classify message type
        msg_type = classify_message_type(
            message_body,
            payload.num_media,
            payload.media_type or ""
        )
        
        # Create interaction record
        create_interaction(
            session,
            user.id,
            bottle.id,
            msg_type,
            "true",  # from_user
            message_body or f"[{msg_type}]"
        )
        
        # Handle different message types
        if msg_type == "image" and payload.media_type and "image" in payload.media_type.lower():
            # Receipt verification
            if bottle.game_started and not bottle.returned:
                # Try to get image URL from raw message
                raw_msg = payload.raw_message or {}
                if isinstance(raw_msg, dict):
                    image_data = raw_msg.get("image", {})
                    if isinstance(image_data, dict):
                        image_id = image_data.get("id")
                    else:
                        image_id = None
                else:
                    image_id = None
                
                if image_id:
                    # Get media URL from WhatsApp API
                    # WhatsApp media requires a two-step process:
                    # 1. Get media URL from media ID
                    # 2. Download using that URL with access token
                    # For now, we'll pass the media ID and let verify_receipt handle it
                    # or construct a direct URL (may require access token in headers)
                    media_url = f"https://graph.facebook.com/v18.0/{image_id}"
                    
                    is_verified, error_msg, verification = verify_receipt(
                        session,
                        user.id,
                        bottle.id,
                        media_url,
                        access_token=WHATSAPP_ACCESS_TOKEN
                    )
                    
                    if is_verified:
                        # Calculate savings
                        from core.game.feeding_game import calculate_and_record_savings
                        savings = calculate_and_record_savings(session, bottle.id)
                        
                        bottle.returned = True
                        bottle.return_verified = True
                        session.add(bottle)
                        session.commit()
                        
                        char_config = get_character_config(product_id)
                        send_whatsapp_text(
                            payload.from_number,
                            f"Merci ! {char_config['name']} est de retour ! 💚"
                        )
                        
                        # Award points
                        award_points(session, user.id, 50, "bottle_return")
                        
                        # Check for milestone
                        milestone_bonus = calculate_milestone_bonus(session, user.id)
                        if milestone_bonus > 0:
                            send_whatsapp_text(
                                payload.from_number,
                                f"🎉 Bonus de {milestone_bonus} points pour ton engagement !"
                            )
                    else:
                        send_whatsapp_text(
                            payload.from_number,
                            "Désolé, je n'ai pas pu vérifier le reçu. Peux-tu réessayer ? 📄"
                        )
                else:
                    send_whatsapp_text(
                        payload.from_number,
                        "Je n'ai pas pu récupérer l'image. Peux-tu réessayer ? 📷"
                    )
                return
        
        # Rules request
        if detect_rules_request(message_body):
            rules_url = f"{PUBLIC_BASE_URL or 'http://localhost:5000'}/rules/{product_id}.png"
            send_whatsapp_media(payload.from_number, rules_url, "image/png")
            session.commit()
            return
        
        # Rename request
        if detect_rename_request(message_body):
            new_name = extract_name_from_message(message_body)
            if new_name:
                bottle.name = new_name
                session.add(bottle)
                session.commit()
                char_config = get_character_config(product_id)
                send_whatsapp_text(
                    payload.from_number,
                    f"Parfait ! {char_config['name']} s'appelle maintenant {new_name} ! ✨"
                )
            else:
                send_whatsapp_text(
                    payload.from_number,
                    "Quel nom veux-tu donner à ton personnage ?"
                )
            return
        
        # Game logic
        if not bottle.game_started:
            # Start game
            updated_bottle, name_prompt = start_game(session, bottle, message_body)
            bottle = updated_bottle
            session.add(bottle)
            session.commit()
            
            if name_prompt:
                send_whatsapp_text(payload.from_number, name_prompt)
            else:
                char_config = get_character_config(product_id)
                send_whatsapp_text(
                    payload.from_number,
                    f"Salut ! Je suis {char_config['name']} ! Envoie-moi des emojis pour me nourrir ! 🍎"
                )
            return
        
        # Emoji feeding
        if msg_type == "emoji" or msg_type == "mixed":
            emojis = extract_emojis_from_message(message_body)
            if emojis:
                result = process_emoji_feed(session, bottle, emojis)
                session.add(bottle)
                session.commit()
                
                # Get stickers for current state
                fullness_state = get_fullness_state(bottle.fullness_level)
                stickers = get_stickers_for_state(bottle, PUBLIC_BASE_URL or "http://localhost:5000")
                
                # Send response
                if result.get("success"):
                    # Award points
                    points = result.get("points", 0)
                    if points > 0:
                        award_points(session, user.id, points, "emoji_feed")
                    
                    # Send sticker if available
                    if stickers.get("fullness"):
                        sticker = stickers["fullness"]
                        send_whatsapp_sticker(payload.from_number, sticker["url"])
                    
                    # Send text response
                    response_text = result.get("message", "Merci !")
                    send_whatsapp_text(payload.from_number, response_text)
                else:
                    # Wrong emoji
                    error_msg = result.get("message", "Ce n'est pas le bon emoji !")
                    send_whatsapp_text(payload.from_number, error_msg)
                
                # Check for milestone
                milestone_bonus = calculate_milestone_bonus(session, user.id)
                if milestone_bonus > 0:
                    send_whatsapp_text(
                        payload.from_number,
                        f"🎉 Bonus de {milestone_bonus} points !"
                    )
                
                return
        
        # Get recent interactions for context
        recent_interactions = get_recent_interactions(session, bottle.id, limit=10)
        
        # Update bottle state
        bottle = update_bottle_state(session, bottle, recent_interactions)
        session.add(bottle)
        
        # Detect emotion
        emotion = detect_emotion_from_message(message_body) if message_body else "neutral"
        
        # Get character config
        char_config = get_character_config(product_id)
        system_prompt = get_system_prompt_for_character(product_id)
        
        # Build conversation history
        conversation_history = []
        for interaction in recent_interactions[-5:]:  # Last 5 interactions
            role = "user" if interaction.from_user == "true" else "assistant"
            conversation_history.append({
                "role": role,
                "content": interaction.content[:200]  # Limit length
            })
        
        # Add current message
        conversation_history.append({
            "role": "user",
            "content": message_body[:200] if message_body else "[media]"
        })
        
        # Build bottle state for LLM
        fullness_state = get_fullness_state(bottle.fullness_level)
        bottle_state = {
            "mood": bottle.mood,
            "fullness": bottle.fullness_level,
            "fullness_state": fullness_state,
            "personality_level": bottle.personality_level,
            "name": bottle.name or char_config["name"]
        }
        
        # Generate reply
        try:
            reply = generate_reply(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                bottle_state=bottle_state,
                temperature=0.8,
                max_tokens=150
            )
        except Exception as e:
            logger.exception("Error generating LLM reply", extra={
                "request_id": payload.request_id
            })
            reply = "Désolé, je n'ai pas compris. Peux-tu répéter ?"
        
        # Check if stickers are available before selecting response type
        test_stickers = get_stickers_for_state(bottle, PUBLIC_BASE_URL or "http://localhost:5000")
        has_sticker_available = bool(test_stickers.get("emotional"))
        has_gif_available = bool(select_gif_by_mood(session, bottle.mood, PUBLIC_BASE_URL or "http://localhost:5000", product_id))
        
        logger.debug("Checking media availability", extra={
            "request_id": payload.request_id,
            "has_sticker": has_sticker_available,
            "has_gif": has_gif_available,
            "mood": bottle.mood,
            "product_id": product_id,
            "public_base_url": PUBLIC_BASE_URL or "http://localhost:5000"
        })
        
        # Select response type (sticker, GIF, text)
        response_type = select_response_type(
            session,
            bottle.id,
            bottle.mood,
            has_sticker=has_sticker_available,
            has_gif=has_gif_available
        )
        
        # Send response based on type
        logger.info("Sending response to user", extra={
            "request_id": payload.request_id,
            "response_type": response_type,
            "reply_preview": reply[:50] if reply else None
        })
        
        try:
            if response_type == "text_sticker":
                stickers = get_stickers_for_state(bottle, PUBLIC_BASE_URL or "http://localhost:5000")
                if stickers.get("emotional"):
                    sticker = stickers["emotional"]
                    logger.info("Sending sticker", extra={
                        "request_id": payload.request_id,
                        "sticker_url": sticker["url"],
                        "sticker_filename": sticker.get("filename", "N/A")
                    })
                    send_whatsapp_sticker(payload.from_number, sticker["url"])
                else:
                    logger.warning("No emotional sticker found for response", extra={
                        "request_id": payload.request_id,
                        "mood": bottle.mood,
                        "product_id": product_id,
                        "available_stickers": list(stickers.keys()) if stickers else None
                    })
                logger.info("Sending text reply after sticker", extra={"request_id": payload.request_id})
                send_whatsapp_text(payload.from_number, reply)
            elif response_type == "gif_only":
                gif = select_gif_by_mood(session, bottle.mood, PUBLIC_BASE_URL or "http://localhost:5000", product_id)
                if gif:
                    logger.info("Sending GIF", extra={
                        "request_id": payload.request_id,
                        "gif_url": gif["url"]
                    })
                    try:
                        send_whatsapp_gif(payload.from_number, gif["url"], reply)
                    except WhatsAppCloudError as gif_error:
                        # Check if it's a permission error (code 10) - handle both int and string
                        error_code = gif_error.error_code
                        is_permission_error = (
                            error_code == 10 or 
                            error_code == "10" or 
                            (isinstance(error_code, str) and error_code.isdigit() and int(error_code) == 10)
                        )
                        if is_permission_error:
                            logger.warning("GIF sending failed due to permissions, falling back to text", extra={
                                "request_id": payload.request_id,
                                "error_code": error_code,
                                "error_message": str(gif_error)
                            })
                            send_whatsapp_text(payload.from_number, reply)
                        else:
                            # Re-raise if it's a different error
                            raise
                else:
                    logger.info("No GIF found, sending text only", extra={"request_id": payload.request_id})
                    send_whatsapp_text(payload.from_number, reply)
            else:
                logger.info("Sending text reply only", extra={
                    "request_id": payload.request_id,
                    "response_type": response_type
                })
                send_whatsapp_text(payload.from_number, reply)
            
            logger.info("Response sent successfully", extra={"request_id": payload.request_id})
        except Exception as send_error:
            logger.exception("Failed to send response to user", extra={
                "request_id": payload.request_id,
                "response_type": response_type,
                "send_error": str(send_error)
            })
            raise
        
        # Create interaction for bot response
        create_interaction(
            session,
            user.id,
            bottle.id,
            "text",
            "false",  # from_user = false (bot response)
            reply
        )
        
        # Check daily engagement
        check_daily_engagement(session, user.id)
        
        # Check and notify hungry characters (async, non-blocking)
        try:
            check_and_notify_hungry_characters(session, user.id, payload.from_number)
        except Exception as e:
            logger.exception("Error checking hungry characters", extra={
                "request_id": payload.request_id
            })
        
        session.commit()
        
        logger.info("Message processed successfully", extra={
            "request_id": payload.request_id,
            "message_id": payload.message_id
        })
        
    except Exception as e:
        logger.exception("Error processing WhatsApp message", extra={
            "request_id": payload.request_id,
            "message_id": payload.message_id
        })
        # Try to send error message to user (but don't let this crash the process)
        try:
            logger.info("Attempting to send error notification to user", extra={
                "request_id": payload.request_id,
                "from_number": payload.from_number[:4] + "****"
            })
            send_whatsapp_text(
                payload.from_number,
                "Désolé, une erreur s'est produite. Réessaye dans un instant !"
            )
            logger.info("Error notification sent successfully", extra={
                "request_id": payload.request_id
            })
        except WhatsAppCloudError as notify_error:
            # Log permission/auth errors but don't crash
            logger.error("Failed to send error notification due to API error", extra={
                "request_id": payload.request_id,
                "error_code": notify_error.error_code,
                "error_message": str(notify_error)
            })
        except Exception as notify_error:
            logger.exception("Failed to send error notification to user", extra={
                "request_id": payload.request_id,
                "notification_error": str(notify_error)
            })
        raise
    finally:
        session.close()
