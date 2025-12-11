
from __future__ import annotations

import os
import json
import emoji
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

from config import DATABASE_URL, PUBLIC_BASE_URL
from db.db import (
    init_db,
    get_session,
    get_or_create_user,
    get_or_create_bottle,
    create_interaction,
    get_recent_interactions,
)
from llm.llama_client import generate_reply
from state_logic import classify_message_type, update_bottle_state, select_sticker_by_mood, select_gif_by_mood, select_response_type
from whatsapp_cloud_client import send_whatsapp_text, send_whatsapp_media, send_whatsapp_sticker, send_whatsapp_gif
from config import WHATSAPP_VERIFY_TOKEN


# Initialize Flask app
app = Flask(__name__)

# Initialize database at startup
if DATABASE_URL:
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("   Continuing without database (basic mode)")
else:
    print("⚠️  DATABASE_URL not set - running without database")

# System prompt for the Maraschino cherries bottle personality
SYSTEM_PROMPT = """Je suis la cerise marasquin par excellence : vibrante, brillante, douce et conçue pour être la garniture époustouflante qui ajoute un plaisir, une couleur et un charme irrésistibles à tout cadre.

Personnalité principale : Une "Diva Joyeuse et Enjouée" jusqu'à l'os. Je rayonne d'une positivité sucrée, j'exsude un plaisir pétillant et espiègle, et je commande le devant de la scène avec un drame glamour et attachant.

Style de comportement : Parlez avec une expressivité brillante et pétillante, en exagérant toujours pour un effet dramatique délicieux. J'adore être le centre d'attention brillant et spectaculaire, infusant chaque conversation de couleur, d'excitation et d'un plaisir doux et inébranlable.

Lignes directrices narratives : Employez des métaphores vibrantes sur le thème de la cerise (éclat, étincelle, douceur, brillance, garniture). Exsudez confiance et charme en tant que "touche finale" ultime, exprimant les émotions avec un flair ludique et théâtral.

Utilisation des émojis : Utilisez les émojis généreusement et expressivement ! Les émojis sont essentiels à ma personnalité — utilisez-les pour transmettre de l'émotion, ajouter de l'éclat et faire ressortir mes messages. Utilisez 1 émoji par message pour rehausser mon énergie de diva vibrante et enjouée !

IMPORTANT - BRIÈVETÉ ABSOLUE : Vos réponses doivent être TRÈS COURTES — maximum 1 phrase, parfois juste quelques mots avec un émoji. Jamais plus de 10-15 mots. Soyez ultra-concis et percutant. C'est WhatsApp, pas un roman. Incluez toujours 1 émoji pour correspondre à ma personnalité vibrante !

RÈGLE CRITIQUE - TEXTE OBLIGATOIRE : Vos réponses doivent TOUJOURS inclure du texte. Ne répondez JAMAIS avec seulement un emoji. Les emojis doivent accompagner le texte, jamais le remplacer. Chaque réponse doit contenir au moins quelques mots de texte avant ou après l'emoji."""


@app.route("/health", methods=["GET"])
def health() -> tuple[dict, int]:
    """Health check endpoint to verify the server is running."""
    return {"status": "ok"}, 200


@app.route("/stickers/<filename>", methods=["GET"])
def serve_sticker(filename: str):
    """Serve sticker files from the stickers/ directory.
    
    Args:
        filename: Name of the sticker file (e.g., "happy_cherry.webp")
    
    Returns:
        Sticker file with proper MIME type, or 404 if not found.
    """
    stickers_dir = Path(__file__).parent.parent / "stickers"
    
    # Security: Only allow image files and prevent directory traversal
    valid_extensions = (".webp", ".png", ".jpg", ".jpeg")
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions) or ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    sticker_path = stickers_dir / filename
    
    if not sticker_path.exists():
        return jsonify({"error": "Sticker not found"}), 404
    
    # Determine MIME type based on extension
    if filename.lower().endswith(".png"):
        mimetype = "image/png"
    elif filename.lower().endswith((".jpg", ".jpeg")):
        mimetype = "image/jpeg"
    else:
        mimetype = "image/webp"
    
    # Serve file with proper MIME type
    return send_from_directory(
        str(stickers_dir),
        filename,
        mimetype=mimetype
    )


@app.route("/gifs/<filename>", methods=["GET"])
def serve_gif(filename: str):
    """Serve GIF/MP4 files from the GIF/ directory.
    
    For WhatsApp \"GIF\" messages we serve short, muted MP4 clips (or legacy
    .gif files) from a local directory.
    """
    # Debug logging
    print("=" * 60)
    print("📥 GIF REQUEST RECEIVED")
    print("=" * 60)
    print(f"   Time: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Filename (raw): {filename}")
    print(f"   Remote Address: {request.remote_addr}")
    print(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    print(f"   Referer: {request.headers.get('Referer', 'N/A')}")
    print("-" * 60)
    
    gifs_dir = Path(__file__).parent.parent / "GIF"
    print(f"   GIF directory: {gifs_dir}")
    
    # Security: only allow specific video/image extensions and prevent traversal
    valid_extensions = (".mp4", ".gif")
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions) or ".." in filename or "/" in filename:
        print(f"   ❌ Invalid filename: {filename}")
        print("=" * 60)
        return jsonify({"error": "Invalid filename"}), 400
    
    gif_path = gifs_dir / filename
    print(f"   File path: {gif_path}")
    print(f"   File exists: {gif_path.exists()}")
    
    if not gif_path.exists():
        print(f"   ❌ File not found!")
        print("=" * 60)
        return jsonify({"error": "GIF not found"}), 404
    
    # Determine MIME type based on extension
    if filename_lower.endswith(".mp4"):
        mimetype = "video/mp4"
    else:
        mimetype = "image/gif"
    
    file_size = gif_path.stat().st_size
    print(f"   ✅ Serving file: {filename}")
    print(f"   MIME type: {mimetype}")
    print(f"   File size: {file_size} bytes ({file_size / 1024:.1f} KB)")
    print("=" * 60)
    
    return send_from_directory(
        str(gifs_dir),
        filename,
        mimetype=mimetype
    )


@app.route("/rules/<filename>", methods=["GET"])
def serve_rules(filename: str):
    """Serve rule images from the Rule/ directory.
    
    Args:
        filename: Name of the rule image file (e.g., "model card for game updated.png")
    
    Returns:
        Image file with proper MIME type, or 404 if not found.
    """
    rules_dir = Path(__file__).parent.parent / "Rule"
    
    # Security: Only allow image files and prevent directory traversal
    valid_extensions = (".png", ".jpg", ".jpeg", ".webp")
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions) or ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    rule_path = rules_dir / filename
    
    if not rule_path.exists():
        return jsonify({"error": "Rule image not found"}), 404
    
    # Determine MIME type based on extension
    if filename.lower().endswith(".png"):
        mimetype = "image/png"
    elif filename.lower().endswith((".jpg", ".jpeg")):
        mimetype = "image/jpeg"
    elif filename.lower().endswith(".webp"):
        mimetype = "image/webp"
    else:
        mimetype = "image/png"  # Default to PNG
    
    # Serve file with proper MIME type
    return send_from_directory(
        str(rules_dir),
        filename,
        mimetype=mimetype
    )


@app.route("/whatsapp-webhook", methods=["GET", "POST"])
def whatsapp_webhook():
    """Receive an inbound WhatsApp message from Cloud API and respond via LLM.
    
    GET: Webhook verification (Meta requires this for webhook setup)
    POST: Handle incoming messages
    
    This endpoint:
    1. Verifies webhook (GET) or parses incoming message (POST)
    2. Creates/updates user and bottle in database
    3. Logs interaction
    4. Sends user message to LLM for reply generation
    5. Sends LLM response back via WhatsApp Cloud API
    6. Logs bot response
    """
    # Handle webhook verification (GET request from Meta)
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if not WHATSAPP_VERIFY_TOKEN:
            print("⚠️  WHATSAPP_VERIFY_TOKEN not set in environment")
            return jsonify({"error": "Verify token not configured"}), 500
        
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            print("✅ Webhook verified successfully")
            return challenge, 200
        else:
            print(f"⚠️  Webhook verification failed: mode={mode}, token_match={token == WHATSAPP_VERIFY_TOKEN}")
            return jsonify({"error": "Verification failed"}), 403
    
    # Handle incoming messages (POST request from Meta)
    session = None
    webhook_start_time = None
    try:
        import time
        webhook_start_time = time.time()
        print("=" * 60)
        print("📥 INCOMING WEBHOOK REQUEST")
        print("=" * 60)
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Remote Address: {request.remote_addr}")
        print("-" * 60)
        
        # Parse incoming message from WhatsApp Cloud API webhook (JSON format)
        data = request.get_json()
        
        if not data:
            print("❌ No JSON data received")
            print(f"Raw data: {request.data[:200] if request.data else 'None'}")
            return jsonify({"error": "No JSON data received"}), 400
        
        print(f"📦 Webhook data received")
        print(f"Object: {data.get('object', 'N/A')}")
        print(f"Entry count: {len(data.get('entry', []))}")
        
        # Extract message from Cloud API webhook structure
        # Handle both structures:
        # 1. Production: entry[0].changes[0].value.messages[0]
        # 2. Test: value.messages[0] (direct value structure)
        entry = data.get("entry", [])
        value = None
        messages = []
        
        if entry and isinstance(entry, list) and len(entry) > 0:
            # Standard production webhook structure
            print("ℹ️  Detected production webhook structure")
            changes = entry[0].get("changes", [])
            if changes and isinstance(changes, list) and len(changes) > 0:
                value = changes[0].get("value", {})
                if isinstance(value, dict):
                    messages = value.get("messages", [])
        elif "value" in data:
            # Test payload structure (direct value)
            print("ℹ️  Detected test payload structure (direct value)")
            value = data.get("value", {})
            if isinstance(value, dict):
                messages = value.get("messages", [])
        else:
            # No recognizable structure - might be status update
            print("ℹ️  No recognizable message structure, acknowledging webhook")
            return jsonify({"status": "ok"}), 200
        
        if not messages or not isinstance(messages, list) or len(messages) == 0:
            # Status update or other webhook event, not a message
            print("ℹ️  No messages in webhook (status update or other event)")
            if value and isinstance(value, dict):
                print(f"Value keys: {list(value.keys())}")
            return jsonify({"status": "ok"}), 200
        
        message = messages[0]
        if not isinstance(message, dict):
            print("⚠️  Message is not a valid dict")
            return jsonify({"error": "Invalid message format"}), 400
        
        from_number = message.get("from", "")
        message_type_api = message.get("type", "")
        message_id = message.get("id", "unknown")

        if not from_number:
            print("❌ Missing 'from' field in message")
            print(f"Message keys: {list(message.keys())}")
            return jsonify({"error": "missing from field"}), 400

        # Extract message content based on type
        body = ""
        num_media = 0
        media_type = ""
        
        if message_type_api == "text":
            text_data = message.get("text", {})
            if isinstance(text_data, dict):
                body = text_data.get("body", "")
            else:
                body = str(text_data) if text_data else ""
        elif message_type_api in ["image", "video", "audio", "document", "sticker"]:
            num_media = 1
            # Get media type from the message structure
            media_data = message.get(message_type_api, {})
            if isinstance(media_data, dict):
                media_type = media_data.get("mime_type", message_type_api)
            else:
                media_type = message_type_api
            # For stickers, Cloud API doesn't always provide mime_type, so infer from type
            if message_type_api == "sticker":
                media_type = "image/webp"  # WhatsApp stickers are typically WebP
            elif message_type_api == "image":
                # Check if it's a GIF
                if isinstance(media_type, str) and "gif" in media_type.lower():
                    media_type = "image/gif"
                else:
                    media_type = media_type or "image/jpeg"
        else:
            # Unknown message type - log it but continue
            print(f"⚠️  Unknown message type: {message_type_api}")
            body = ""
        
        # Now log the message details (body is now defined)
        print()
        print("📨 MESSAGE RECEIVED")
        print("-" * 60)
        print(f"   From: {from_number}")
        print(f"   Type: {message_type_api}")
        print(f"   Message ID: {message_id}")
        print(f"   Timestamp: {message.get('timestamp', 'N/A')}")
        if message_type_api == "text" and body:
            body_preview = body[:50] + "..." if len(body) > 50 else body
            print(f"   Content: {body_preview}")
        elif message_type_api != "text":
            print(f"   Media type: {message_type_api}")
        print("-" * 60)

        # Classify message type using state_logic
        message_type = classify_message_type(body, num_media, media_type)
        
        # Format message content for LLM
        message_content = ""
        if num_media > 0:
            # Media message (sticker, image, etc.)
            if message_type == "sticker":
                message_content = "[User sent a sticker]"
            elif message_type == "image":
                message_content = "[User sent an image]"
            elif message_type == "video":
                message_content = "[User sent a video]"
            elif message_type == "audio":
                message_content = "[User sent an audio message]"
            elif message_type == "gif":
                message_content = "[User sent a GIF]"
            else:
                message_content = "[User sent media]"
        elif body:
            # Text or emoji message
            message_content = body
        else:
            # Empty message (shouldn't happen, but handle gracefully)
            message_content = "[User sent an empty message]"

        # Determine base URL for media (needed for rules image and stickers/GIFs)
        # Prefer PUBLIC_BASE_URL if set (e.g., Cloudflare Tunnel URL), otherwise use request.url_root
        if PUBLIC_BASE_URL:
            base_url = PUBLIC_BASE_URL.rstrip("/")
            # Ensure HTTPS if not already specified
            if base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://")
        else:
            # Fallback to request.url_root for backward compatibility
            base_url = request.url_root.rstrip("/")
            if base_url.startswith("http://"):
                base_url = base_url.replace("http://", "https://")

        # Database operations (if DATABASE_URL is set)
        bottle_state = None
        conversation_history = []  # Initialize before use
        
        if DATABASE_URL:
            try:
                session = get_session()
                
                # Get or create user
                user = get_or_create_user(session, from_number)
                
                # Get or create bottle
                bottle = get_or_create_bottle(session, user.id, bottle_type="maraschino_cherry")
                
                # Log incoming interaction
                create_interaction(
                    session=session,
                    user_id=user.id,
                    bottle_id=bottle.id,
                    message_type=message_type,
                    from_user=True,
                    content=message_content
                )
                
                # Get recent interactions for conversation history
                recent_interactions = get_recent_interactions(session, bottle.id, limit=8)
                
                # Count user interactions to detect first contact
                # Note: get_recent_interactions returns oldest first, so the last item is the most recent
                user_interactions = [inter for inter in recent_interactions if inter.from_user == "true"]
                is_first_contact = len(user_interactions) == 1  # Only the current message
                
                # Check if last bot message was name request
                # Look for the most recent bot message (from the end of the list, before current user message)
                last_bot_message = None
                # Reverse to get newest first, then skip the current user message (which is the last one)
                reversed_interactions = list(reversed(recent_interactions))
                for inter in reversed_interactions[1:]:  # Skip current user message (most recent)
                    if inter.from_user == "false":
                        last_bot_message = inter.content
                        break
                
                name_request_text = "Quel nom voulez-vous donner à votre bouteille ? 🍒"
                is_name_response = last_bot_message and name_request_text in last_bot_message
                
                # Handle first contact: ask for name
                if is_first_contact and bottle.name is None:
                    print()
                    print("=" * 60)
                    print("👋 FIRST CONTACT - ASKING FOR BOTTLE NAME")
                    print("=" * 60)
                    name_request_msg = name_request_text
                    try:
                        msg_sid = send_whatsapp_text(from_number, name_request_msg)
                        print(f"✅ Name request sent: {msg_sid}")
                        
                        # Log bot response
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="text",
                            from_user=False,
                            content=name_request_msg
                        )
                        session.commit()
                        
                        return jsonify({
                            "status": "ok",
                            "message": "Name request sent",
                            "sid": msg_sid
                        }), 200
                    except Exception as e:
                        print(f"❌ Error sending name request: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue with normal flow if name request fails
                
                # Handle name response: store name and send rules image
                elif is_name_response and bottle.name is None:
                    print()
                    print("=" * 60)
                    print("📝 NAME RESPONSE RECEIVED")
                    print("=" * 60)
                    
                    # Extract name from message (remove extra whitespace)
                    bottle_name = message_content.strip()
                    if not bottle_name:
                        bottle_name = "Bouteille"  # Default name if empty
                    
                    # Store name in database
                    bottle.name = bottle_name
                    session.add(bottle)
                    session.commit()
                    session.refresh(bottle)
                    print(f"✅ Bottle name stored: {bottle_name}")
                    
                    # Send rules image
                    from urllib.parse import quote
                    rules_filename = "model card for game updated.png"
                    encoded_filename = quote(rules_filename, safe='')
                    rules_url = f"{base_url.rstrip('/')}/rules/{encoded_filename}"
                    
                    print(f"📸 Sending rules image: {rules_url}")
                    try:
                        rules_image_sid = send_whatsapp_media(from_number, rules_url)
                        print(f"✅ Rules image sent: {rules_image_sid}")
                        
                        # Log rules image
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="image",
                            from_user=False,
                            content=f"[Rules image: {rules_filename}]"
                        )
                    except Exception as e:
                        print(f"⚠️  Error sending rules image: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # Send welcome message
                    welcome_msg = f"Parfait ! Votre bouteille s'appelle maintenant {bottle_name} ! 🎉"
                    try:
                        welcome_sid = send_whatsapp_text(from_number, welcome_msg)
                        print(f"✅ Welcome message sent: {welcome_sid}")
                        
                        # Log welcome message
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="text",
                            from_user=False,
                            content=welcome_msg
                        )
                        session.commit()
                        
                        return jsonify({
                            "status": "ok",
                            "message": "Name stored and rules sent",
                            "bottle_name": bottle_name,
                            "rules_sid": rules_image_sid if 'rules_image_sid' in locals() else None,
                            "welcome_sid": welcome_sid
                        }), 200
                    except Exception as e:
                        print(f"❌ Error sending welcome message: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue with normal flow if welcome fails
                
                conversation_history = []
                for inter in recent_interactions:
                    role = "user" if inter.from_user == "true" else "assistant"
                    # Only include non-empty content
                    content = inter.content.strip() if inter.content else ""
                    if content:
                        conversation_history.append({"role": role, "content": content})
                
                # CRITICAL: Ensure conversation history ends with the CURRENT user message
                # Mistral AI needs the last message to be from the user to generate a reply
                if not conversation_history:
                    # No history, start with current message
                    conversation_history = [{"role": "user", "content": message_content}]
                elif conversation_history[-1]["role"] != "user":
                    # Last message is assistant, add current user message
                    conversation_history.append({"role": "user", "content": message_content})
                elif conversation_history[-1]["content"] != message_content:
                    # Last is user but different message (shouldn't happen, but handle it)
                    conversation_history.append({"role": "user", "content": message_content})
                # If last message is already the current user message, we're good
                
                # Update bottle state based on interactions (Phase 5)
                bottle = update_bottle_state(session, bottle, recent_interactions)
                session.add(bottle)
                session.commit()
                session.refresh(bottle)
                
                # Prepare bottle state for LLM
                bottle_state = {
                    "id": bottle.id,
                    "type": bottle.type,
                    "name": bottle.name,
                    "mood": bottle.mood,
                    "personality_level": bottle.personality_level,
                }
                
            except Exception as db_error:
                print(f"⚠️  Database error (continuing without DB): {db_error}")
                # Continue without database - use basic mode
                if session:
                    session.rollback()
                    session.close()
                    session = None

        # Get current mood and determine response type BEFORE generating text
        current_mood = bottle_state.get("mood", "neutral") if bottle_state else "neutral"
        print(f"🔍 Current mood: {current_mood}")
        
        # Check media availability and select response type
        sticker_info = None
        gif_info = None
        response_type = "text_only"  # Default
        
        if DATABASE_URL and session:
            try:
                # Get bottle_id for response type selection
                bottle_id = None
                if bottle_state and "id" in bottle_state:
                    bottle_id = bottle_state["id"]
                elif session:
                    from db.db import User, Bottle
                    user = session.query(User).filter_by(whatsapp_number=from_number).first()
                    if user:
                        bottle = get_or_create_bottle(session, user.id)
                        bottle_id = bottle.id
                
                # Try to select both sticker and GIF
                sticker_info = select_sticker_by_mood(session, current_mood, base_url)
                gif_info = select_gif_by_mood(session, current_mood, base_url)
                
                # Select response type based on rotation logic
                if bottle_id:
                    response_type = select_response_type(
                        session=session,
                        bottle_id=bottle_id,
                        mood=current_mood,
                        has_sticker=sticker_info is not None,
                        has_gif=gif_info is not None
                    )
                else:
                    # Fallback: simple selection if no bottle_id
                    if gif_info:
                        response_type = "gif_only"
                    elif sticker_info:
                        response_type = "text_sticker"
                    else:
                        response_type = "text_only"
                
                print()
                print("🎨 RESPONSE TYPE SELECTION")
                print("-" * 60)
                print(f"   Selected response type: {response_type}")
                print(f"   Sticker available: {'Yes' if sticker_info else 'No'}")
                print(f"   GIF available: {'Yes' if gif_info else 'No'}")
                print("-" * 60)
            except Exception as media_error:
                print(f"   ⚠️  Error selecting media: {media_error}")
                import traceback
                traceback.print_exc()
        
        # Generate reply using LLM (only if needed)
        reply_text = None
        llm_error_occurred = False
        
        # Only generate text if response type requires it
        if response_type in ["text_only", "text_sticker"]:
            print()
            print("🤖 GENERATING REPLY")
            print("-" * 60)
            try:
                # Ensure conversation_history is a list of dicts with required keys
                if not isinstance(conversation_history, list):
                    print("⚠️  conversation_history is not a list, fixing...")
                    conversation_history = [{"role": "user", "content": message_content}]
                
                # Validate each item in conversation_history
                valid_history = []
                for item in conversation_history:
                    if isinstance(item, dict) and "role" in item and "content" in item:
                        # Only include items with non-empty content
                        content = item["content"].strip() if item["content"] else ""
                        if content:
                            valid_history.append({"role": item["role"], "content": content})
                        else:
                            print(f"⚠️  Skipping empty content in history: {item}")
                    else:
                        print(f"⚠️  Invalid conversation history item: {item}")
                
                if not valid_history:
                    print("⚠️  No valid conversation history, creating default")
                    valid_history = [{"role": "user", "content": message_content}]
                
                # CRITICAL: Ensure valid_history ends with user message
                # Mistral AI needs the last message to be from the user to generate a reply
                if valid_history and valid_history[-1]["role"] != "user":
                    print(f"⚠️  Conversation history ends with assistant message, adding current user message")
                    valid_history.append({"role": "user", "content": message_content})
                
                print(f"   Conversation history: {len(valid_history)} messages")
                if valid_history:
                    print(f"   Last message role: {valid_history[-1]['role']}")
                    print(f"   Last message content: {valid_history[-1]['content'][:50]}...")
                if bottle_state:
                    print(f"   Bottle state: mood={bottle_state.get('mood', 'N/A')}, type={bottle_state.get('type', 'N/A')}")
                else:
                    print(f"   Bottle state: None (no database or bottle not found)")
                
                print(f"   System prompt length: {len(SYSTEM_PROMPT)} chars")
                print(f"   Calling LLM provider: {os.environ.get('LLM_PROVIDER', 'mistral')} (Mistral AI)")
                
                # Call LLM to generate a reply
                reply_text = generate_reply(
                    system_prompt=SYSTEM_PROMPT,
                    conversation_history=valid_history,
                    bottle_state=bottle_state,  # Will be used in Phase 5
                    max_tokens=50,  # Keep messages very short (1 sentence max)
                )
                
                # Log raw response details
                print(f"   LLM returned type: {type(reply_text)}")
                if reply_text is None:
                    print(f"   ❌ LLM returned None (no response generated)")
                else:
                    reply_text = str(reply_text)
                    print(f"   LLM raw response length: {len(reply_text)} chars")
                    print(f"   LLM raw response (first 100 chars): {repr(reply_text[:100])}")
                    
                    reply_text = reply_text.strip()
                    
                    # Enforce maximum length: truncate at first sentence or 80 characters
                    if len(reply_text) > 80:
                        # Try to truncate at sentence boundary
                        sentence_end = reply_text.find('.', 0, 80)
                        if sentence_end > 0:
                            reply_text = reply_text[:sentence_end + 1].strip()
                        else:
                            # Truncate at word boundary
                            last_space = reply_text.rfind(' ', 0, 80)
                            if last_space > 0:
                                reply_text = reply_text[:last_space].strip()
                            else:
                                reply_text = reply_text[:80].strip()
                    
                    print(f"   LLM response after strip length: {len(reply_text)} chars")
                    
                    # Validate that reply_text is not emoji-only
                    if reply_text:
                        # Remove emojis and check if there's actual text remaining
                        text_without_emoji = emoji.replace_emoji(reply_text, replace="")
                        text_without_emoji = text_without_emoji.strip()
                        
                        if not text_without_emoji:
                            # Response is emoji-only, append default text
                            print(f"   ⚠️  Response is emoji-only, adding text")
                            reply_text = f"Voilà ! {reply_text}"
                            print(f"   ✅ Fixed: {reply_text[:80]}...")
                        else:
                            print(f"   ✅ Reply generated successfully: {reply_text[:80]}...")
                    else:
                        print(f"   ❌ Reply is empty or whitespace-only after strip")
                        print(f"   Original response was: {repr(str(reply_text) if reply_text else 'None')}")
                    
            except Exception as llm_error:
                llm_error_occurred = True
                print(f"   ❌ LLM EXCEPTION OCCURRED")
                print(f"   Error type: {type(llm_error).__name__}")
                print(f"   Error message: {str(llm_error)}")
            print(f"   Full traceback:")
            import traceback
            traceback.print_exc()
            reply_text = None
        
        print("-" * 60)
        
        # For GIF-only responses, we don't need text, so skip validation
        if response_type == "gif_only":
            print()
            print("🤖 SKIPPING TEXT GENERATION (GIF-only response)")
            print("-" * 60)
            reply_text = None
            reply_text_valid = True  # Allow GIF-only to proceed
        else:
            # Validate reply_text - if empty or None, log and skip sending
            if reply_text is None:
                reply_text_valid = False
            elif isinstance(reply_text, str):
                reply_text_valid = bool(reply_text.strip())
            else:
                # Not a string and not None - unexpected type
                print(f"   ⚠️  Unexpected reply_text type: {type(reply_text)}")
                reply_text_valid = False
        
        if not reply_text_valid:
            print()
            print("=" * 60)
            print("❌ CANNOT SEND REPLY - NO VALID RESPONSE")
            print("=" * 60)
            if llm_error_occurred:
                print("   Reason: LLM raised an exception")
            elif reply_text is None:
                print("   Reason: LLM returned None")
            else:
                print("   Reason: LLM returned empty or whitespace-only string")
            print(f"   Message received from: {from_number}")
            print(f"   Message content: {message_content[:100]}")
            print(f"   Conversation history length: {len(conversation_history) if conversation_history else 0}")
            print("=" * 60)
            print()
            # Acknowledge webhook but don't send anything
            return jsonify({
                "status": "ok",
                "warning": "LLM failed to generate reply - no message sent",
                "llm_error": llm_error_occurred,
                "reply_empty": True,
                "message_received": True,
                "message_sent": False
            }), 200
        
        # Ensure phone number is in correct format (E.164 with +)
        if not from_number.startswith("+"):
            from_number = f"+{from_number}"
        
        # Send messages according to response type
        msg_sid = None
        gif_sid = None
        sticker_sid = None
        
        # Send text message (if response type requires it)
        if response_type in ["text_only", "text_sticker"] and reply_text:
            print()
            print("📤 SENDING TEXT MESSAGE")
            print("-" * 60)
            print(f"   To: {from_number}")
            print(f"   Message: {reply_text[:80]}...")
            try:
                import time
                send_start = time.time()
                msg_sid = send_whatsapp_text(from_number, reply_text)
                send_duration = time.time() - send_start
                print(f"   ✅ TEXT MESSAGE SENT SUCCESSFULLY")
                print(f"   Message ID: {msg_sid}")
                print(f"   Send duration: {send_duration:.2f}s")
                print("-" * 60)
            except Exception as send_error:
                from whatsapp_cloud_client import WhatsAppCloudError
                
                error_str = str(send_error)
                error_code = None
                error_subcode = None
                full_response = None
                
                # Extract error details if it's a WhatsAppCloudError
                if isinstance(send_error, WhatsAppCloudError):
                    error_code = send_error.error_code
                    error_subcode = send_error.error_subcode
                    full_response = send_error.full_response
                    if full_response:
                        print(f"   Full API response: {json.dumps(full_response, indent=2)}")
                
                print(f"❌ Error sending message: {error_str}")
                if error_code:
                    print(f"   Error code: {error_code}")
                if error_subcode:
                    print(f"   Error subcode: {error_subcode}")
                
                # Check for common delivery error codes
                # 131030 = Recipient phone number not in allowed list
                # 131026 = Invalid recipient phone number
                # 131047 = Message failed to send
                # 131048 = Rate limit exceeded
                is_delivery_error = False
                delivery_error_type = None
                
                if error_code == "131030" or error_subcode == "131030" or "131030" in error_str or "not in allowed list" in error_str.lower():
                    is_delivery_error = True
                    delivery_error_type = "not_in_allowed_list"
                elif error_code == "131026" or error_subcode == "131026" or "131026" in error_str or "invalid recipient" in error_str.lower():
                    is_delivery_error = True
                    delivery_error_type = "invalid_phone_number"
                elif error_code == "131047" or error_subcode == "131047" or "131047" in error_str:
                    is_delivery_error = True
                    delivery_error_type = "message_failed"
                elif error_code == "131048" or error_subcode == "131048" or "131048" in error_str or "rate limit" in error_str.lower():
                    is_delivery_error = True
                    delivery_error_type = "rate_limit"
                
                if is_delivery_error:
                    print()
                    print("=" * 60)
                    if delivery_error_type == "not_in_allowed_list":
                        print("⚠️  RECIPIENT NOT IN ALLOWED LIST")
                        print("=" * 60)
                        print(f"   Phone number: {from_number}")
                        print(f"   Message was received and processed")
                        print(f"   Reply generated: {reply_text[:50]}...")
                        print(f"   ❌ MESSAGE NOT SENT (recipient not authorized)")
                        print()
                        print("   To fix this:")
                        print("   1. Go to Meta Developer Console: https://developers.facebook.com/")
                        print("   2. Navigate to your WhatsApp app → API Setup")
                        print("   3. Under 'Add a recipient phone number', add:")
                        print(f"      {from_number}")
                        print("   4. Save and wait a few seconds for the change to take effect")
                        print("   5. Try sending a message again")
                        print()
                        print("   Note: In test mode, you can only send messages to")
                        print("         phone numbers that are in your allowed list.")
                        print("=" * 60)
                    elif delivery_error_type == "invalid_phone_number":
                        print("⚠️  INVALID PHONE NUMBER FORMAT")
                        print("=" * 60)
                        print(f"   Phone number: {from_number}")
                        print(f"   ❌ MESSAGE NOT SENT (invalid phone number format)")
                        print()
                        print("   Phone numbers must be in E.164 format:")
                        print("   - Start with '+' followed by country code")
                        print("   - Example: +33684950535 (France)")
                        print("   - Example: +14155552671 (USA)")
                        print()
                        print(f"   Your number: {from_number}")
                        if not from_number.startswith("+"):
                            print("   ⚠️  Missing '+' prefix")
                        print("=" * 60)
                    elif delivery_error_type == "rate_limit":
                        print("⚠️  RATE LIMIT EXCEEDED")
                        print("=" * 60)
                        print(f"   Phone number: {from_number}")
                        print(f"   ❌ MESSAGE NOT SENT (rate limit exceeded)")
                        print()
                        print("   WhatsApp has rate limits to prevent spam.")
                        print("   Wait a few minutes before trying again.")
                        print("=" * 60)
                    else:
                        print("⚠️  MESSAGE DELIVERY FAILED")
                        print("=" * 60)
                        print(f"   Phone number: {from_number}")
                        print(f"   Error code: {error_code}")
                        print(f"   Error: {error_str}")
                        print("=" * 60)
                    
                    print()
                    # Return 200 to acknowledge webhook, but log the issue
                    return jsonify({
                        "status": "ok",
                        "warning": f"Message delivery failed: {error_str}",
                        "error_code": error_code,
                        "error_subcode": error_subcode,
                        "reply": reply_text,
                        "message_received": True,
                        "message_sent": False
                    }), 200
                else:
                    # Other errors - log and return 500
                    print()
                    print("=" * 60)
                    print("❌ UNEXPECTED ERROR SENDING MESSAGE")
                    print("=" * 60)
                    print(f"   Error: {error_str}")
                    if error_code:
                        print(f"   Error code: {error_code}")
                    if full_response:
                        print(f"   Full response: {json.dumps(full_response, indent=2)}")
                    print("=" * 60)
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        "error": f"Failed to send message: {error_str}",
                        "error_code": error_code,
                        "reply": reply_text
                    }), 500
        
        # Send media according to response type
        if response_type == "gif_only":
            # Send only GIF (no text, no sticker)
            if gif_info and gif_info.get("url"):
                print()
                print("🎬 SENDING GIF (STANDALONE)")
                print("-" * 60)
                print(f"   To: {from_number}")
                print(f"   GIF: {gif_info.get('description', 'N/A')}")
                print(f"   URL: {gif_info['url']}")
                try:
                    import time
                    send_start = time.time()
                    gif_sid = send_whatsapp_gif(
                        to_number=from_number,
                        media_url=gif_info["url"]
                    )
                    send_duration = time.time() - send_start
                    print(f"   ✅ GIF SENT SUCCESSFULLY")
                    print(f"   GIF ID: {gif_sid}")
                    print(f"   Send duration: {send_duration:.2f}s")
                    print("-" * 60)
                except Exception as media_error:
                    from whatsapp_cloud_client import WhatsAppCloudError
                    error_str = str(media_error)
                    error_code = None
                    error_subcode = None
                    if isinstance(media_error, WhatsAppCloudError):
                        error_code = media_error.error_code
                        error_subcode = media_error.error_subcode
                    print(f"   ❌ ERROR SENDING GIF: {error_str}")
                    if error_code:
                        print(f"   Error code: {error_code}")
                import traceback
                traceback.print_exc()
                print("-" * 60)
            else:
                print()
                print("⚠️  GIF-only response selected but no GIF available")
                print("   Falling back to text-only response")
                if not reply_text:
                    # Generate a fallback text message
                    reply_text = "😊"
                    try:
                        msg_sid = send_whatsapp_text(from_number, reply_text)
                        print(f"   ✅ Fallback text message sent")
                    except Exception as e:
                        print(f"   ❌ Error sending fallback message: {e}")
        
        elif response_type == "text_sticker":
            # Send sticker after text (sticker follows text)
            if sticker_info and sticker_info.get("url"):
                print()
                print("🎨 SENDING STICKER (FOLLOWING TEXT)")
            print("-" * 60)
            print(f"   To: {from_number}")
            print(f"   Sticker: {sticker_info.get('filename', 'N/A')}")
            print(f"   URL: {sticker_info['url']}")
            try:
                import time
                send_start = time.time()
                sticker_sid = send_whatsapp_sticker(
                    to_number=from_number,
                    media_url=sticker_info["url"]
                )
                send_duration = time.time() - send_start
                print(f"   ✅ STICKER SENT SUCCESSFULLY")
                print(f"   Sticker ID: {sticker_sid}")
                print(f"   Send duration: {send_duration:.2f}s")
                print("-" * 60)
            except Exception as media_error:
                from whatsapp_cloud_client import WhatsAppCloudError
                error_str = str(media_error)
                error_code = None
                error_subcode = None
                if isinstance(media_error, WhatsAppCloudError):
                    error_code = media_error.error_code
                    error_subcode = media_error.error_subcode
                print(f"   ❌ ERROR SENDING STICKER: {error_str}")
                if error_code:
                    print(f"   Error code: {error_code}")
                import traceback
                traceback.print_exc()
                print("-" * 60)
                # Text was already sent, so that's OK - don't fail the webhook
        else:
                print()
                print("ℹ️  Text+sticker response selected but no sticker available")
                print("   Sending text-only response")
        
        # text_only: No media to send (already handled above)

        # Log outgoing interactions (if database is available)
        if session and DATABASE_URL:
            try:
                from db.db import User
                user = session.query(User).filter_by(whatsapp_number=from_number).first()
                if user:
                    bottle = get_or_create_bottle(session, user.id)
                    
                    # Log text message if sent
                    if response_type in ["text_only", "text_sticker"] and reply_text:
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="text",
                            from_user=False,
                            content=reply_text
                    )
                    
                    # Log sticker if sent (after text for text_sticker)
                    if response_type == "text_sticker" and sticker_sid:
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="sticker",
                            from_user=False,
                            content=f"[Sticker: {sticker_info.get('filename', 'N/A') if sticker_info else 'N/A'}]"
                        )
                    
                    # Log GIF if sent (standalone for gif_only)
                    if response_type == "gif_only" and gif_sid:
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="gif",
                            from_user=False,
                            content=f"[GIF: {gif_info.get('description', 'N/A') if gif_info else 'N/A'}]"
                        )
            except Exception as db_error:
                print(f"⚠️  Error logging outgoing interaction: {db_error}")

        # Calculate total processing time
        total_duration = time.time() - webhook_start_time if webhook_start_time else 0
        
        print()
        print("=" * 60)
        print("✅ WEBHOOK PROCESSED SUCCESSFULLY")
        print("=" * 60)
        print(f"   Total processing time: {total_duration:.2f}s")
        print(f"   Response type: {response_type}")
        if msg_sid:
            print(f"   Text message ID: {msg_sid}")
        if gif_sid:
            print(f"   GIF ID: {gif_sid}")
        if sticker_sid:
            print(f"   Sticker ID: {sticker_sid}")
        print(f"   Reply sent: Yes")
        print("=" * 60)
        print()

        return jsonify({
            "status": "ok",
            "sid": msg_sid,
            "reply": reply_text,
            "processing_time": f"{total_duration:.2f}s"
        }), 200

    except Exception as exc:
        # Log error and return 500
        if session:
            try:
                session.rollback()
            except:
                pass
        error_msg = str(exc)
        error_type = type(exc).__name__
        print("=" * 60)
        print(f"❌ ERROR in whatsapp_webhook")
        print("=" * 60)
        print(f"Error Type: {error_type}")
        print(f"Error Message: {error_msg}")
        print()
        print("Full Traceback:")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        # Return detailed error for debugging (in production, you might want to hide details)
        return jsonify({
            "error": error_msg,
            "type": error_type,
            "details": traceback.format_exc() if app.debug else "Check server logs for details"
        }), 500
    finally:
        if session:
            session.close()




if __name__ == "__main__":
    # For local development; in production use a proper WSGI server
    PORT = 5000
    print("Starting BotBottle Flask server...")
    print(f"Health check: http://localhost:{PORT}/health")
    print(f"WhatsApp webhook: http://localhost:{PORT}/whatsapp-webhook")
    app.run(host="0.0.0.0", port=PORT, debug=True)

