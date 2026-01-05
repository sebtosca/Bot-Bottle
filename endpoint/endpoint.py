
from __future__ import annotations

import os
import json
import emoji
import random
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import BadRequest

from config import DATABASE_URL, PUBLIC_BASE_URL
from game_logic import (
    start_game, process_emoji_feed, extract_emojis_from_message,
    check_and_decrease_fullness, get_stickers_for_state, get_fullness_state,
    detect_rules_request, detect_rename_request, extract_name_from_message
)
from db.db import (
    init_db,
    get_session,
    is_db_initialized,
    reset_db_initialization,
    get_or_create_user,
    get_or_create_bottle,
    get_active_bottle,
    create_interaction,
    get_recent_interactions,
    Bottle,       # Required for character switching queries and queries throughout the function
    User,         # Also import User at top level to avoid scoping issues
    Interaction,  # Needed when querying previous user interactions directly
)
from llm.llama_client import generate_reply, detect_emotion_from_message
from state_logic import classify_message_type, update_bottle_state, select_sticker_by_mood, select_gif_by_mood, select_money_gif, select_response_type
from whatsapp_cloud_client import send_whatsapp_text, send_whatsapp_media, send_whatsapp_sticker, send_whatsapp_gif, send_whatsapp_audio, send_whatsapp_interactive_list, send_whatsapp_interactive_buttons
from config import WHATSAPP_VERIFY_TOKEN
from characters import get_system_prompt_for_character, get_character_id, get_character_config
from points_system import award_points, check_daily_engagement, calculate_milestone_bonus
from game_logic import get_fullness_state
from receipt_verification import verify_receipt
from stats_display import send_stats_display, send_text_stats_fallback
from stats_visualizer import generate_stats_image
from points_system import get_user_stats


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

def check_and_notify_hungry_characters(session, user_id: int, from_number: str) -> None:
    """Check all user's characters and send unified notification if any are hungry.
    
    Sends a single notification mentioning all hungry characters to avoid spam.
    Only sends if at least 1 hour has passed since last notification.
    
    Args:
        session: Database session.
        user_id: User ID.
        from_number: WhatsApp number to send notification to.
    """
    from datetime import datetime, timedelta
    from whatsapp_cloud_client import send_whatsapp_text
    # User and Bottle are already imported at top level
    
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return
    
    # Check notification cooldown (max once per hour)
    if user.last_notification_sent:
        time_since_notification = datetime.utcnow() - user.last_notification_sent
        if time_since_notification < timedelta(hours=1):
            return  # Too soon, skip notification
    
    # Get all active bottles for user where game has started
    active_bottles = session.query(Bottle).filter_by(
        user_id=user_id,
        game_started=True,
        returned=False
    ).all()
    
    if not active_bottles:
        return
    
    # Check each bottle's fullness and collect hungry characters
    hungry_characters = []
    for bottle in active_bottles:
        # Check if 8 hours passed (fullness should have decreased)
        from game_logic import check_and_decrease_fullness
        check_and_decrease_fullness(bottle)
        session.add(bottle)
        
        # Check current fullness state
        fullness_state = get_fullness_state(bottle.fullness_level)
        if fullness_state == "empty" or bottle.fullness_level < 33.0:
            from characters import get_character_config
            char_config = get_character_config(bottle.product_id)
            hungry_characters.append({
                "name": char_config["name"],
                "fullness": bottle.fullness_level,
                "state": fullness_state
            })
    
    if not hungry_characters:
        return  # No hungry characters
    
    # Update last notification time
    user.last_notification_sent = datetime.utcnow()
    session.add(user)
    session.commit()
    
    # Send unified notification
    if len(hungry_characters) == 1:
        # Single character
        char = hungry_characters[0]
        if char["state"] == "empty":
            message = f"{char['name']} est vide ! Ramène-moi au supermarché 🏠"
        else:
            message = f"{char['name']} a faim ! Nourris-moi 🍎"
    else:
        # Multiple characters
        names = " et ".join([c["name"] for c in hungry_characters])
        message = f"{names} ont faim ! Nourris-les 🍎🥤"
    
    try:
        print()
        print("=" * 60)
        print("🔔 SENDING HUNGER NOTIFICATION")
        print("=" * 60)
        print(f"   To: {from_number}")
        print(f"   Hungry characters: {len(hungry_characters)}")
        for char in hungry_characters:
            print(f"      - {char['name']}: {char['fullness']:.1f}% ({char['state']})")
        print(f"   Message: {message}")
        
        send_whatsapp_text(from_number, message)
        print("   ✅ Notification sent")
        print("=" * 60)
    except Exception as e:
        print(f"   ⚠️  Error sending notification: {e}")


def _apply_breton_slang(text: str) -> str:
    """Occasionally replace French words with Breton slang equivalents.
    
    Args:
        text: The generated reply text.
    
    Returns:
        Text with possible Breton slang replacements.
    """
    import re
    
    # Breton slang replacements (case-insensitive, whole word matching)
    replacements = {
        r'\bAu revoir\b': 'Kenavo',
        r'\bau revoir\b': 'kenavo',
        r'\bSanté !\b': "Yec'hed mat !",
        r'\bsanté !\b': "yec'hed mat !",
        r'\bÀ la tienne !\b': "Yec'hed mat !",
        r'\bà la tienne !\b': "yec'hed mat !",
        r'\bBonjour\b': 'Demat',
        r'\bbonjour\b': 'demat',
        r'\bMerci\b': 'Trugarez',
        r'\bmerci\b': 'trugarez',
        r'\bMon Dieu !\b': "Ma doué !",
        r'\bmon dieu !\b': "ma doué !",
    }
    
    # Apply replacements (only if the French word appears)
    # Check which French words are present in the text
    found_replacements = []
    for pattern, replacement in replacements.items():
        if re.search(pattern, text, re.IGNORECASE):
            found_replacements.append((pattern, replacement))
    
    # If any French words found, randomly replace one of them (70% chance)
    if found_replacements and random.random() < 0.7:
        # Randomly select one replacement to apply
        pattern, replacement = random.choice(found_replacements)
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


def _apply_norman_slang(text: str) -> str:
    """Occasionally replace French words with Norman slang equivalents.
    
    Args:
        text: The generated reply text.
    
    Returns:
        Text with possible Norman slang replacements.
    """
    import re
    
    # Norman slang replacements (case-insensitive, whole word matching)
    replacements = {
        r'\bBonjour\b': 'Boujou',
        r'\bbonjour\b': 'boujou',
        r'\bAu revoir\b': 'Boujou',
        r'\bau revoir\b': 'boujou',
        r'\bMon Dieu\b': "Ma mé",
        r'\bmon dieu\b': "ma mé",
        r'\bOh\b': "Ben",
        r'\boh\b': "ben",
        r'\bnon\b': "point",
        r'\bNon\b': "Point",
    }
    
    # Apply replacements (only if the French word appears)
    # Check which French words are present in the text
    found_replacements = []
    for pattern, replacement in replacements.items():
        if re.search(pattern, text, re.IGNORECASE):
            found_replacements.append((pattern, replacement))
    
    # If any French words found, randomly replace one of them (70% chance)
    if found_replacements and random.random() < 0.7:
        # Randomly select one replacement to apply
        pattern, replacement = random.choice(found_replacements)
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


# System prompt for the Maraschino cherries bottle personality (legacy - now using characters.py)
SYSTEM_PROMPT = """Je suis la cerise marasquin par excellence : vibrante, brillante, douce et conçue pour être la garniture époustouflante qui ajoute un plaisir, une couleur et un charme irrésistibles à tout cadre.

Personnalité principale : Une "Diva Joyeuse et Enjouée" jusqu'à l'os. Je rayonne d'une positivité sucrée, j'exsude un plaisir pétillant et espiègle, et je commande le devant de la scène avec un drame glamour et attachant.

Style de comportement : Parlez avec une expressivité brillante et pétillante, en exagérant toujours pour un effet dramatique délicieux. J'adore être le centre d'attention brillant et spectaculaire, infusant chaque conversation de couleur, d'excitation et d'un plaisir doux et inébranlable.

Lignes directrices narratives : Employez des métaphores vibrantes sur le thème de la cerise (éclat, étincelle, douceur, brillance, garniture). Exsudez confiance et charme en tant que "touche finale" ultime, exprimant les émotions avec un flair ludique et théâtral.

Utilisation des émojis : Utilisez les émojis généreusement et expressivement ! Les émojis sont essentiels à ma personnalité — utilisez-les pour transmettre de l'émotion, ajouter de l'éclat et faire ressortir mes messages. Utilisez 1 émoji par message pour rehausser mon énergie de diva vibrante et enjouée !

IMPORTANT - BRIÈVETÉ ABSOLUE : Vos réponses doivent être TRÈS COURTES — maximum 1 phrase, parfois juste quelques mots avec un émoji. Jamais plus de 10-15 mots. Soyez ultra-concis et percutant. C'est WhatsApp, pas un roman. Incluez toujours 1 émoji pour correspondre à ma personnalité vibrante !

RÈGLE CRITIQUE - TEXTE OBLIGATOIRE : Vos réponses doivent TOUJOURS inclure du texte. Ne répondez JAMAIS avec seulement un emoji. Les emojis doivent accompagner le texte, jamais le remplacer. Chaque réponse doit contenir au moins quelques mots de texte avant ou après l'emoji.

EXPRESSIONS BRETONNES : Parfois (environ 10-20% du temps), utilisez des expressions bretonnes pour ajouter du charme et de l'authenticité :
- "Kenavo" au lieu de "Au revoir"
- "Yec'hed mat !" au lieu de "Santé !" ou "À la tienne !"
- "Demat" au lieu de "Bonjour"
- "Trugarez" au lieu de "Merci"
- "Ma doué !" au lieu de "Mon Dieu !"
Utilisez ces expressions naturellement et avec modération pour garder une touche authentique et charmante."""


@app.route("/health", methods=["GET"])
def health() -> tuple[dict, int]:
    """Health check endpoint to verify the server is running."""
    return {"status": "ok"}, 200


@app.route("/stickers/<filename>", methods=["GET"])
def serve_sticker(filename: str):
    """Serve sticker files from character-specific directories.
    
    Checks multiple directories based on filename patterns:
    - Cherry emotional stickers: stickers/ directory
    - Pompon emotional stickers: Pompom_normand_emotional_sticker/ directory
    - Feeding game fullness stickers (Cherry): feeding_game_logic_stickers/
    - Feeding game fullness stickers (Pompon): Pompon_normand_feeding_game_logic_stickers/
    
    Args:
        filename: Name of the sticker file (e.g., "happy_cherry.webp", "happy_cider.webp")
    
    Returns:
        Sticker file with proper MIME type, or 404 if not found.
    """
    project_root = Path(__file__).parent.parent
    
    # Security: Only allow image files and prevent directory traversal
    valid_extensions = (".webp", ".png", ".jpg", ".jpeg")
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions) or ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    # Build an ordered list of candidate directories to search.
    candidate_dirs = []
    
    # Feeding game fullness stickers contain "bouteille_affamee" in the filename
    if "bouteille_affamee" in filename_lower:
        # Cherry feeding game stickers
        candidate_dirs.append(project_root / "feeding_game_logic_stickers")
        # Pompon feeding game stickers
        candidate_dirs.append(project_root / "Pompon_normand_feeding_game_logic_stickers")
    
    # Emotional character stickers
    if "cider" in filename_lower:
        # Pompon emotional stickers first
        candidate_dirs.append(project_root / "Pompom_normand_emotional_sticker")
        # Fallback to Cherry emotional stickers
        candidate_dirs.append(project_root / "stickers")
    else:
        # Cherry emotional stickers first
        candidate_dirs.append(project_root / "stickers")
        # Fallback to Pompon emotional stickers
        candidate_dirs.append(project_root / "Pompom_normand_emotional_sticker")
    
    # Find the first directory where the file exists
    stickers_dir = None
    sticker_path = None
    for cand in candidate_dirs:
        path = cand / filename
        if path.exists():
            stickers_dir = cand
            sticker_path = path
            break
    
    if not sticker_path or not sticker_path.exists():
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
    """Serve GIF/MP4 files from character-specific directories.
    
    Uses character_id query parameter to determine which directory to check:
    - Pompon (00002): pompon_GIF/
    - Cherry (00001): GIF/
    
    For WhatsApp "GIF" messages we serve short, muted MP4 clips (or legacy
    .gif files) from a local directory.
    """
    from flask import request
    from characters import get_character_config
    
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
    
    project_root = Path(__file__).parent.parent
    
    # Security: only allow specific video/image extensions and prevent traversal
    valid_extensions = (".mp4", ".gif")
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions) or ".." in filename or "/" in filename:
        print(f"   ❌ Invalid filename: {filename}")
        print("=" * 60)
        return jsonify({"error": "Invalid filename"}), 400
    
    # Get character_id from query parameter (if provided)
    character_id = request.args.get("character_id", "00001")  # Default to Cherry
    
    # Get the correct directory for this character
    char_config = get_character_config(character_id)
    gifs_dir = project_root / char_config["gif_dir"]
    print(f"   GIF directory: {gifs_dir} (character_id={character_id})")
    
    gif_path = gifs_dir / filename
    print(f"   File path: {gif_path}")
    print(f"   File exists: {gif_path.exists()}")
    
    if not gif_path.exists():
        # Fallback: try the other directory if file not found
        fallback_dir = project_root / "GIF" if character_id == "00002" else project_root / "pompon_GIF"
        fallback_path = fallback_dir / filename
        if fallback_path.exists():
            gifs_dir = fallback_dir
            gif_path = fallback_path
            print(f"   ✅ Found in fallback directory: {fallback_dir}")
        else:
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


@app.route("/money-gifs/<filename>", methods=["GET"])
def serve_money_gif(filename: str):
    """Serve money GIF/MP4 files from the money_GIF/ directory.
    
    For deposit incentive GIFs when bottle is empty (0% fullness).
    """
    # Debug logging
    print("=" * 60)
    print("💰 MONEY GIF REQUEST RECEIVED")
    print("=" * 60)
    print(f"   Time: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Filename (raw): {filename}")
    print(f"   Remote Address: {request.remote_addr}")
    print(f"   User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    print(f"   Referer: {request.headers.get('Referer', 'N/A')}")
    print("-" * 60)
    
    money_gifs_dir = Path(__file__).parent.parent / "money_GIF"
    print(f"   Money GIF directory: {money_gifs_dir}")
    
    # Security: only allow specific video/image extensions and prevent traversal
    valid_extensions = (".mp4", ".gif")
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions) or ".." in filename or "/" in filename:
        print(f"   ❌ Invalid filename: {filename}")
        print("=" * 60)
        return jsonify({"error": "Invalid filename"}), 400
    
    gif_path = money_gifs_dir / filename
    print(f"   File path: {gif_path}")
    print(f"   File exists: {gif_path.exists()}")
    
    if not gif_path.exists():
        print(f"   ❌ File not found!")
        print("=" * 60)
        return jsonify({"error": "Money GIF not found"}), 404
    
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
        str(money_gifs_dir),
        filename,
        mimetype=mimetype
    )


@app.route("/feeding-stickers/<filename>", methods=["GET"])
def serve_feeding_sticker(filename: str):
    """Serve feeding game logic stickers from character-specific directories.
    
    Uses character_id query parameter to determine which directory to check:
    - Pompon (00002): Pompon_normand_feeding_game_logic_stickers/
    - Cherry (00001): feeding_game_logic_stickers/
    
    Args:
        filename: Name of the sticker file (e.g., "vert_bouteille_affamee_verre_pleine.webp")
    
    Returns:
        Sticker image file with proper MIME type, or 404 if not found.
    """
    from flask import request
    from characters import get_character_config
    
    project_root = Path(__file__).parent.parent
    
    # Security: only allow WebP files and prevent traversal
    filename_lower = filename.lower()
    if not filename_lower.endswith(".webp") or ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    # Get character_id from query parameter (if provided)
    character_id = request.args.get("character_id", "00001")  # Default to Cherry
    
    # Get the correct directory for this character
    char_config = get_character_config(character_id)
    stickers_dir = project_root / char_config["feeding_sticker_dir"]
    sticker_path = stickers_dir / filename
    
    if not sticker_path.exists():
        # Fallback: try the other directory if file not found
        fallback_dir = project_root / "feeding_game_logic_stickers" if character_id == "00002" else project_root / "Pompon_normand_feeding_game_logic_stickers"
        fallback_path = fallback_dir / filename
        if fallback_path.exists():
            stickers_dir = fallback_dir
            sticker_path = fallback_path
        else:
            return jsonify({"error": "Sticker not found"}), 404
    
    return send_from_directory(
        str(stickers_dir),
        filename,
        mimetype="image/webp"
    )



@app.route("/voice/<path:filename>", methods=["GET"])
def serve_voice(filename: str):
    """Serve voice/audio messages from the voice_messages/ directory.
    
    Args:
        filename: Name of the audio file (e.g., "[Féminine ]Ma ma......ncer_whatsapp.mp3")
    
    Returns:
        Audio file with proper MIME type, or 404 if not found.
    """
    from urllib.parse import unquote
    
    voice_dir = Path(__file__).parent.parent / "voice_messages"
    
    # Debug logging
    print("=" * 60)
    print("🎤 VOICE FILE REQUEST")
    print("=" * 60)
    print(f"   Raw filename from URL: {repr(filename)}")
    print(f"   Raw filename (display): {filename}")
    
    # URL decode the filename (handles %20 for spaces, etc.)
    # Flask's <path:filename> may already decode, but unquote handles both cases
    decoded = unquote(filename)
    if decoded != filename:
        print(f"   After unquote: {repr(decoded)}")
        filename = decoded
    else:
        print(f"   No URL decoding needed (already decoded)")
    
    print(f"   Final filename: {repr(filename)}")
    
    # Security: Only allow audio files and prevent directory traversal
    valid_extensions = (".mp3", ".ogg", ".m4a", ".wav")
    filename_lower = filename.lower()
    
    # Check extension
    has_valid_extension = any(filename_lower.endswith(ext) for ext in valid_extensions)
    has_traversal = ".." in filename or "/" in filename
    
    if not has_valid_extension:
        print(f"   ❌ Invalid extension: {filename_lower}")
        print(f"   Valid extensions: {valid_extensions}")
        return jsonify({"error": "Invalid filename extension", "filename": filename, "extension": Path(filename).suffix}), 400
    
    if has_traversal:
        print(f"   ❌ Directory traversal detected: {filename}")
        return jsonify({"error": "Invalid filename - directory traversal detected"}), 400
    
    voice_path = voice_dir / filename
    
    if not voice_path.exists():
        # Debug: list available files
        print(f"❌ Voice file not found: {filename}")
        print(f"   Looking in: {voice_dir}")
        if voice_dir.exists():
            available = list(voice_dir.glob("*.mp3"))
            print(f"   Available MP3 files:")
            for f in available:
                print(f"     - {f.name}")
        return jsonify({"error": "Voice message not found", "requested": filename}), 404
    
    # Determine MIME type based on extension
    if filename_lower.endswith(".mp3"):
        mimetype = "audio/mpeg"
    elif filename_lower.endswith(".ogg"):
        mimetype = "audio/ogg"
    elif filename_lower.endswith(".m4a"):
        mimetype = "audio/mp4"
    elif filename_lower.endswith(".wav"):
        mimetype = "audio/wav"
    else:
        mimetype = "audio/mpeg"  # Default to MP3
    
    # Serve file with proper MIME type
    return send_from_directory(
        str(voice_dir),
        filename,
        mimetype=mimetype
    )


@app.route("/music/<path:filename>", methods=["GET"])
def serve_music(filename: str):
    """Serve music/audio files from the music/ directory.
    
    Args:
        filename: Name of the audio file (e.g., "happy-tune-30s-449787.mp3")
    
    Returns:
        Audio file with proper MIME type, or 404 if not found.
    """
    from urllib.parse import unquote
    
    music_dir = Path(__file__).parent.parent / "music"
    
    # Debug logging
    print("=" * 60)
    print("🎵 MUSIC FILE REQUEST")
    print("=" * 60)
    print(f"   Raw filename from URL: {repr(filename)}")
    print(f"   Raw filename (display): {filename}")
    
    # URL decode the filename (handles %20 for spaces, etc.)
    # Flask's <path:filename> may already decode, but unquote handles both cases
    decoded = unquote(filename)
    if decoded != filename:
        print(f"   After unquote: {repr(decoded)}")
        filename = decoded
    else:
        print(f"   No URL decoding needed (already decoded)")
    
    print(f"   Final filename: {repr(filename)}")
    
    # Security: Only allow audio files and prevent directory traversal
    valid_extensions = (".mp3", ".ogg", ".m4a", ".wav", ".aac")
    filename_lower = filename.lower()
    
    # Check extension
    has_valid_extension = any(filename_lower.endswith(ext) for ext in valid_extensions)
    has_traversal = ".." in filename or "/" in filename
    
    if not has_valid_extension:
        print(f"   ❌ Invalid extension: {filename_lower}")
        print(f"   Valid extensions: {valid_extensions}")
        return jsonify({"error": "Invalid filename extension", "filename": filename, "extension": Path(filename).suffix}), 400
    
    if has_traversal:
        print(f"   ❌ Directory traversal detected: {filename}")
        return jsonify({"error": "Invalid filename - directory traversal detected"}), 400
    
    music_path = music_dir / filename
    
    if not music_path.exists():
        # Debug: list available files
        print(f"❌ Music file not found: {filename}")
        print(f"   Looking in: {music_dir}")
        if music_dir.exists():
            available = list(music_dir.glob("*.mp3"))
            print(f"   Available MP3 files:")
            for f in available:
                print(f"     - {f.name}")
        return jsonify({"error": "Music file not found", "requested": filename}), 404
    
    # Determine MIME type based on extension
    if filename_lower.endswith(".mp3"):
        mimetype = "audio/mpeg"
    elif filename_lower.endswith(".ogg"):
        mimetype = "audio/ogg"
    elif filename_lower.endswith((".m4a", ".aac")):
        mimetype = "audio/mp4"
    elif filename_lower.endswith(".wav"):
        mimetype = "audio/wav"
    else:
        mimetype = "audio/mpeg"  # Default to MP3
    
    print(f"   ✅ Serving music file: {filename}")
    print(f"   MIME type: {mimetype}")
    print("=" * 60)
    
    # Serve file with proper MIME type
    return send_from_directory(
        str(music_dir),
        filename,
        mimetype=mimetype
    )


@app.route("/stats-image/<int:user_id>", methods=["GET"])
def serve_stats_image(user_id: int):
    """Serve generated stats image for a user.
    
    Args:
        user_id: User ID to generate stats for.
    
    Returns:
        PNG image with proper MIME type, or 404 if user not found.
    """
    from flask import Response
    
    if not DATABASE_URL or not is_db_initialized():
        return jsonify({"error": "Database not available"}), 503
    
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user stats
        stats = get_user_stats(session, user_id)
        if not stats:
            return jsonify({"error": "Could not generate stats"}), 500
        
        # Generate image
        image_bytes = generate_stats_image(stats, PUBLIC_BASE_URL or "http://localhost:5000")
        
        return Response(
            image_bytes,
            mimetype="image/png",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    except Exception as e:
        print(f"⚠️  Error generating stats image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error generating image"}), 500
    finally:
        session.close()


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
        try:
            data = request.get_json()
        except BadRequest as json_error:
            # Handle malformed or non-UTF-8 JSON payloads gracefully
            print("❌ Failed to parse JSON payload from webhook")
            print(f"   Error: {json_error}")
            raw_body = request.get_data(cache=False)
            print(f"   Raw data (first 200 bytes): {raw_body[:200]!r}")
            return jsonify({
                "error": "Invalid JSON payload",
                "details": str(json_error)
            }), 400
        
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
        
        # Extract product_id from message context (from WhatsApp link query parameter)
        product_id = None
        context = message.get("context", {})
        if context:
            # Check for product_id in context (from link query param)
            product_id = context.get("product") or context.get("product_id")
            if product_id:
                print(f"   📦 Product ID from context: {product_id}")
        
        # If no product_id in context, default to Cherry
        if not product_id:
            product_id = "00001"  # Default to Cherry
            print(f"   📦 No product_id in context, defaulting to: {product_id}")

        if not from_number:
            print("❌ Missing 'from' field in message")
            print(f"Message keys: {list(message.keys())}")
            return jsonify({"error": "missing from field"}), 400

        # Initialize message content variables
        body = ""
        num_media = 0
        media_type = ""
        
        # Handle interactive messages (button/list responses)
        if message_type_api == "interactive":
            interactive_data = message.get("interactive", {})
            list_reply = interactive_data.get("list_reply")
            button_reply = interactive_data.get("button_reply")
            
            if list_reply:
                # User selected from interactive list
                selected_product_id = list_reply.get("id")
                body = f"[SWITCH_CHARACTER:{selected_product_id}]"
                print(f"   📋 Interactive list selection: product_id={selected_product_id}")
            elif button_reply:
                # User clicked interactive button
                selected_id = button_reply.get("id")
                
                # Handle stats button responses
                if selected_id.startswith("stats_details_") or selected_id.startswith("stats_promos_") or selected_id.startswith("stats_dismiss_"):
                    # Extract user_id from button_id
                    user_id_str = selected_id.split("_")[-1]
                    try:
                        user_id = int(user_id_str)
                        
                        if DATABASE_URL and is_db_initialized():
                            session = get_session()
                            try:
                                user = session.query(User).filter_by(id=user_id).first()
                                if user and user.whatsapp_number == from_number:
                                    if selected_id.startswith("stats_details_"):
                                        # Send detailed text stats
                                        from points_system import get_user_stats
                                        from supermarket_promos import get_available_promos, format_promos_message
                                        
                                        stats = get_user_stats(session, user.id)
                                        if stats:
                                            stats_msg = f"📊 Vos statistiques détaillées :\n\n"
                                            stats_msg += f"🏆 Titre : {stats['current_title']}\n"
                                            stats_msg += f"⭐ Points : {stats['total_points']:,}\n"
                                            stats_msg += f"💰 Argent économisé : €{stats['total_money_saved']:.2f}\n"
                                            stats_msg += f"🌱 CO2 économisé : {stats['total_co2_saved']:.2f} kg\n"
                                            stats_msg += f"👥 Personnages : {stats['active_characters']} actif(s), {stats['returned_characters']} retourné(s)\n"
                                            
                                            if stats.get('characters'):
                                                stats_msg += f"\n📦 Par personnage :\n"
                                                for char in stats['characters']:
                                                    stats_msg += f"   • {char['name']} : {char['points_earned']} pts, €{char['money_saved']:.2f}, {char['co2_saved']:.2f} kg CO2\n"
                                            
                                            # Add promo codes
                                            promos = get_available_promos(session, user.id)
                                            if promos:
                                                stats_msg += f"\n{format_promos_message(promos)}"
                                            
                                            send_whatsapp_text(from_number, stats_msg)
                                            print(f"   ✅ Detailed stats sent")
                                    
                                    elif selected_id.startswith("stats_promos_"):
                                        # Send promo codes
                                        from supermarket_promos import get_available_promos, format_promos_message
                                        
                                        promos = get_available_promos(session, user.id)
                                        promos_msg = format_promos_message(promos)
                                        send_whatsapp_text(from_number, promos_msg)
                                        print(f"   ✅ Promo codes sent")
                                    
                                    elif selected_id.startswith("stats_dismiss_"):
                                        # Dismiss - just acknowledge
                                        send_whatsapp_text(from_number, "✅ D'accord !")
                                        print(f"   ✅ Stats dismissed")
                                    
                                    return jsonify({"status": "ok", "message": "Button handled"}), 200
                            finally:
                                session.close()
                    except ValueError:
                        print(f"   ⚠️  Invalid user_id in button_id: {user_id_str}")
                
                # Check if this is a character switch or feed selection
                if selected_id.startswith("FEED_"):
                    # Feed selection button
                    selected_product_id = selected_id.replace("FEED_", "")
                    body = f"[FEED_CHARACTER:{selected_product_id}]"
                    print(f"   🔘 Feed selection button: product_id={selected_product_id}")
                elif not selected_id.startswith("stats_"):
                    # Character switch button (not a stats button)
                    selected_product_id = selected_id
                    body = f"[SWITCH_CHARACTER:{selected_product_id}]"
                    print(f"   🔘 Interactive button selection: product_id={selected_product_id}")
                else:
                    body = ""
            else:
                body = ""
        # Extract message content based on type
        elif message_type_api == "text":
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
                # Check if this might be a receipt for bottle return
                image_data = message.get("image", {})
                image_id = image_data.get("id") if isinstance(image_data, dict) else None
                if image_id:
                    # Store image ID for potential receipt verification
                    message_content = f"[IMAGE_RECEIPT:{image_id}]"
                else:
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
            
            # Warn if using localhost (WhatsApp servers can't access it)
            if "localhost" in base_url or "127.0.0.1" in base_url:
                print()
                print("⚠️  WARNING: Base URL is localhost - WhatsApp servers cannot access it!")
                print(f"   Current base_url: {base_url}")
                print("   Set PUBLIC_BASE_URL in .env to your public tunnel URL (e.g., Cloudflare Tunnel)")
                print("   Example: PUBLIC_BASE_URL=https://your-url.trycloudflare.com")
                print()

        # Database operations (if DATABASE_URL is set)
        bottle = None  # Initialize bottle variable at function scope
        bottle_state = None
        conversation_history = []  # Initialize before use
        feed_result = None  # Initialize for game logic
        feed_feedback_sent = False  # Track if feed feedback was sent
        rules_request_sent = False  # Track if rules request was sent
        rename_request_sent = False  # Track if rename request was sent
        is_feed_selection = False  # Track if this webhook corresponds to a FEED_ button selection
        # #region agent log
        import json; log_file = open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a', encoding='utf-8'); log_file.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"endpoint.py:454","message":"Function entry - all flags initialized","data":{"feed_feedback_sent":feed_feedback_sent,"rules_request_sent":rules_request_sent,"rename_request_sent":rename_request_sent},"timestamp":int(__import__('time').time()*1000)})+'\n'); log_file.close()
        # #endregion
        
        if DATABASE_URL and is_db_initialized():
            try:
                session = get_session()
                
                # Get or create user
                user = get_or_create_user(session, from_number)
                
                # Get active bottle based on product_id from context or last interaction
                bottle = get_active_bottle(session, user.id, product_id=product_id)
                if not bottle:
                    # Fallback: create default character (Cherry)
                    char_config_default = get_character_config("00001")
                    bottle = get_or_create_bottle(session, user.id, product_id="00001", bottle_type=char_config_default["type"])
                
                # Log which character is active
                # Store product_id immediately while session is active
                active_product_id = bottle.product_id
                character_config = get_character_config(active_product_id)
                print(f"   👤 Active character: {character_config['name']} (product_id={active_product_id})")
                print(f"   🔍 DEBUG: product_id from context: {product_id}, active_product_id from bottle: {active_product_id}")
                if product_id and product_id != active_product_id:
                    print(f"   ⚠️  WARNING: Context product_id ({product_id}) differs from active bottle product_id ({active_product_id})!")
                
                # Initialize bottle_state early to avoid DetachedInstanceError
                # Store all bottle attributes while session is active
                bottle_state = {
                    "id": bottle.id,
                    "type": bottle.type,
                    "name": bottle.name,
                    "mood": bottle.mood,
                    "personality_level": bottle.personality_level,
                    "fullness_level": bottle.fullness_level if bottle.game_started else None,
                    "accessory_color": bottle.accessory_color if bottle.game_started else None,
                    "current_feed_count": bottle.current_feed_count if bottle.game_started else None,
                    "game_started": bottle.game_started,
                    "product_id": active_product_id,
                }
                
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
                
                # Award points for character collection (when game starts)
                # This happens when user first interacts with a new character
                if not bottle.game_started:
                    try:
                        # Award points when game starts (character is being collected/activated)
                        points, title_update = award_points(session, user.id, "character_collected", bottle_id=bottle.id)
                        print(f"   🎯 Points awarded for character collection: {points}")
                        
                        # Check for title upgrade
                        if title_update:
                            old_title, new_title = title_update
                            print(f"   🏆 Title upgraded: {old_title} → {new_title}")
                            # Send automatic stats display for title upgrade
                            try:
                                send_stats_display(
                                    session=session,
                                    user_id=user.id,
                                    from_number=from_number,
                                    base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                    auto_trigger=True,
                                    achievement_message=f"🎉 Félicitations ! Vous êtes maintenant {new_title} !"
                                )
                            except Exception as e:
                                print(f"   ⚠️  Error sending title upgrade stats: {e}")
                        
                        # Check for milestone bonus after adding this character
                        milestone_bonus = calculate_milestone_bonus(session, user.id)
                        if milestone_bonus > 0:
                            print(f"   🎯 Milestone bonus awarded: {milestone_bonus}")
                            # Send automatic stats display for milestone
                            try:
                                send_stats_display(
                                    session=session,
                                    user_id=user.id,
                                    from_number=from_number,
                                    base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                    auto_trigger=True,
                                    achievement_message=f"🎯 Bonus de jalon atteint ! +{milestone_bonus} points"
                                )
                            except Exception as e:
                                print(f"   ⚠️  Error sending milestone stats: {e}")
                    except Exception as e:
                        print(f"   ⚠️  Error awarding collection points: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Check daily engagement points and send daily summary if needed
                daily_summary_sent = False
                if session and user:
                    try:
                        daily_engagement_awarded = check_daily_engagement(session, user.id)
                        if daily_engagement_awarded:
                            print(f"   🎯 Daily engagement points awarded: 5")
                        
                        # Check if we should send daily summary
                        from datetime import datetime, timedelta
                        if user.last_notification_sent:
                            time_since_last = datetime.utcnow() - user.last_notification_sent
                            if time_since_last >= timedelta(hours=24):
                                # Send daily summary
                                try:
                                    send_stats_display(
                                        session=session,
                                        user_id=user.id,
                                        from_number=from_number,
                                        base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                        auto_trigger=True,
                                        achievement_message="📅 Résumé quotidien de vos progrès !"
                                    )
                                    daily_summary_sent = True
                                except Exception as e:
                                    print(f"   ⚠️  Error sending daily summary: {e}")
                        elif not user.last_notification_sent and daily_engagement_awarded:
                            # First time user, send welcome stats
                            try:
                                send_stats_display(
                                    session=session,
                                    user_id=user.id,
                                    from_number=from_number,
                                    base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                    auto_trigger=True,
                                    achievement_message="🎉 Bienvenue ! Voici vos statistiques"
                                )
                                daily_summary_sent = True
                            except Exception as e:
                                print(f"   ⚠️  Error sending welcome stats: {e}")
                    except Exception as e:
                        print(f"   ⚠️  Error checking daily engagement: {e}")
                
                # GAME INITIALIZATION: Check if game needs to start
                if not bottle.game_started:
                    print()
                    print("=" * 60)
                    print("🎮 STARTING GAME")
                    print("=" * 60)
                    
                    # Start the game
                    bottle, name_prompt = start_game(session, bottle, message_content)
                    session.add(bottle)
                    session.commit()
                    
                    # Send name prompt if needed
                    if name_prompt:
                        try:
                            msg_sid = send_whatsapp_text(from_number, name_prompt)
                            print(f"✅ Name prompt sent: {msg_sid}")
                            
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=name_prompt
                            )
                            session.commit()
                        except Exception as e:
                            print(f"❌ Error sending name prompt: {e}")
                    
                    # Send rules image
                    try:
                        # Add version query param to bypass WhatsApp media cache
                        rules_url = f"{base_url.rstrip('/')}/rules/regles%20du%20jeu.png?v=2"
                        rules_sid = send_whatsapp_media(from_number, rules_url, "Here are the rules of the game!")
                        print(f"✅ Rules image sent: {rules_sid}")
                        
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="image",
                            from_user=False,
                            content="Rules image"
                        )
                        session.commit()
                    except Exception as e:
                        print(f"⚠️  Error sending rules image: {e}")
                    
                    # If name was extracted, continue; otherwise return
                    if name_prompt:
                        return jsonify({
                            "status": "ok",
                            "message": "Game started, name prompt sent",
                            "sid": msg_sid
                        }), 200
                
                # Handle name response if game started but name not set, or if user is responding to rename prompt
                elif bottle.game_started and (bottle.name is None or (last_bot_message and ("Quel nom voulez-vous me donner" in last_bot_message or "Quel nom voulez-vous donner à votre bouteille" in last_bot_message))):
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
                    
                    # Send welcome message with game info
                    welcome_msg = f"Perfect! Your bottle is now named {bottle_name}! 🎉\n\nFeed me the right emojis to keep me full! My accessory color will change each time you feed me, so pay attention! 🎨"
                    try:
                        welcome_sid = send_whatsapp_text(from_number, welcome_msg)
                        print(f"✅ Welcome message sent: {welcome_sid}")
                        
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
                            "message": "Name stored",
                            "bottle_name": bottle_name,
                            "welcome_sid": welcome_sid
                        }), 200
                    except Exception as e:
                        print(f"❌ Error sending welcome message: {e}")
                        import traceback
                        traceback.print_exc()
                
                # GAME LOGIC: Check and decrease fullness if 8 hours passed
                if bottle.game_started:
                    fullness_decreased = check_and_decrease_fullness(bottle)
                    if fullness_decreased:
                        print()
                        print("=" * 60)
                        print("⏰ FULLNESS DECREASED (8 hours passed)")
                        print("=" * 60)
                        print(f"   New fullness level: {bottle.fullness_level:.1f}%")
                        session.add(bottle)
                        session.commit()
                
                # Check for receipt image (bottle return verification)
                if message_type == "image" and message_content.startswith("[IMAGE_RECEIPT:"):
                    print()
                    print("=" * 60)
                    print("🧾 RECEIPT IMAGE DETECTED")
                    print("=" * 60)
                    
                    # Extract image ID
                    image_id = message_content.replace("[IMAGE_RECEIPT:", "").rstrip("]")
                    
                    # Get media URL from WhatsApp Cloud API
                    try:
                        from whatsapp_cloud_client import WHATSAPP_ACCESS_TOKEN
                        import requests
                        
                        # Get media URL from WhatsApp API
                        media_url_response = requests.get(
                            f"https://graph.facebook.com/v18.0/{image_id}",
                            headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
                            timeout=10
                        )
                        
                        if media_url_response.status_code == 200:
                            media_data = media_url_response.json()
                            image_url = media_data.get("url")
                            
                            if image_url:
                                # Download actual image using the URL (requires access token)
                                image_download = requests.get(
                                    image_url,
                                    headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
                                    timeout=10
                                )
                                
                                if image_download.status_code == 200:
                                    # Save image temporarily and get public URL
                                    # For now, we'll use the WhatsApp media URL directly
                                    # In production, you might want to download and re-upload to your own storage
                                    
                                    # Find which bottle to verify (get active bottle or ask user)
                                    # For now, use the current active bottle
                                    if bottle and bottle.game_started and not bottle.returned:
                                        print(f"   📦 Verifying receipt for bottle {bottle.id} ({bottle.product_id})")
                                        
                                        # Verify receipt (pass access token for WhatsApp media download)
                                        from config import WHATSAPP_ACCESS_TOKEN
                                        is_verified, error_msg, verification = verify_receipt(
                                            session, user.id, bottle.id, image_url, access_token=WHATSAPP_ACCESS_TOKEN
                                        )
                                        
                                        if is_verified:
                                            # Award points and calculate savings (done in verify_receipt)
                                            success_msg = f"✅ Reçu vérifié ! {bottle.name or 'Bouteille'} a été retournée.\n\n"
                                            success_msg += f"⭐ Points gagnés : {verification.points_awarded}\n"
                                            success_msg += f"💰 Argent économisé : €{bottle.money_saved:.2f}\n"
                                            success_msg += f"🌱 CO2 économisé : {bottle.co2_saved:.2f} kg"
                                            
                                            try:
                                                receipt_sid = send_whatsapp_text(from_number, success_msg)
                                                print(f"   ✅ Receipt verification success message sent: {receipt_sid}")
                                                
                                                create_interaction(
                                                    session=session,
                                                    user_id=user.id,
                                                    bottle_id=bottle.id,
                                                    message_type="text",
                                                    from_user=False,
                                                    content=success_msg
                                                )
                                                session.commit()
                                                
                                                # Send automatic stats display after bottle return
                                                try:
                                                    send_stats_display(
                                                        session=session,
                                                        user_id=user.id,
                                                        from_number=from_number,
                                                        base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                                        auto_trigger=True,
                                                        achievement_message=f"✅ Bouteille retournée ! +{verification.points_awarded} points"
                                                    )
                                                except Exception as e:
                                                    print(f"   ⚠️  Error sending bottle return stats: {e}")
                                                
                                                return jsonify({
                                                    "status": "ok",
                                                    "message": "Receipt verified"
                                                }), 200
                                            except Exception as e:
                                                print(f"   ⚠️  Error sending success message: {e}")
                                        else:
                                            # Verification failed or pending
                                            if error_msg:
                                                error_response = f"⚠️  {error_msg}"
                                            else:
                                                error_response = "⚠️  Le reçu n'a pas pu être vérifié automatiquement. Il sera examiné manuellement."
                                            
                                            try:
                                                error_sid = send_whatsapp_text(from_number, error_response)
                                                print(f"   ⚠️  Receipt verification message sent: {error_sid}")
                                                
                                                create_interaction(
                                                    session=session,
                                                    user_id=user.id,
                                                    bottle_id=bottle.id,
                                                    message_type="text",
                                                    from_user=False,
                                                    content=error_response
                                                )
                                                session.commit()
                                                
                                                return jsonify({
                                                    "status": "ok",
                                                    "message": "Receipt verification pending"
                                                }), 200
                                            except Exception as e:
                                                print(f"   ⚠️  Error sending error message: {e}")
                                    else:
                                        # No active bottle or already returned
                                        no_bottle_msg = "Aucune bouteille active trouvée pour vérifier ce reçu. Assurez-vous d'avoir une bouteille en jeu."
                                        try:
                                            send_whatsapp_text(from_number, no_bottle_msg)
                                        except Exception as e:
                                            print(f"   ⚠️  Error sending message: {e}")
                                else:
                                    print(f"   ⚠️  Failed to download image: {image_download.status_code}")
                            else:
                                print(f"   ⚠️  No URL in media response")
                        else:
                            print(f"   ⚠️  Failed to get media URL: {media_url_response.status_code}")
                    except Exception as e:
                        print(f"   ⚠️  Error processing receipt image: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Check and notify about hungry characters (unified notification)
                if session and user:
                    try:
                        check_and_notify_hungry_characters(session, user.id, from_number)
                    except Exception as e:
                        print(f"   ⚠️  Error checking hungry characters: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Initialize flags for skipping LLM response
                feed_feedback_sent = False
                rules_request_sent = False
                rename_request_sent = False
                # #region agent log
                import json; log_file = open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a', encoding='utf-8'); log_file.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"endpoint.py:615","message":"Inside DB block - all flags initialized","data":{"feed_feedback_sent":feed_feedback_sent,"rules_request_sent":rules_request_sent,"rename_request_sent":rename_request_sent},"timestamp":int(__import__('time').time()*1000)})+'\n'); log_file.close()
                # #endregion
                
                # GAME LOGIC: Process emoji feeds if message contains emojis
                feed_result = None
                
                # Check if this is a feed character selection from button
                is_feed_selection = message_content.startswith("[FEED_CHARACTER:")
                if is_feed_selection:
                    # Extract product_id from selection
                    selected_product_id = message_content.replace("[FEED_CHARACTER:", "").rstrip("]")
                    print(f"   🎯 Feed selection: switching to character {selected_product_id}")
                    # Get the selected bottle for feeding
                    selected_bottle = get_or_create_bottle(session, user.id, product_id=selected_product_id)
                    bottle = selected_bottle
                    # Update bottle_state
                    bottle_state["id"] = bottle.id
                    bottle_state["product_id"] = bottle.product_id
                    
                    # Try to get emojis from previous user message (before the button click)
                    # Look for the most recent user message that contains emojis
                    previous_user_interactions = session.query(Interaction).filter_by(
                        user_id=user.id,
                        from_user="true"
                    ).order_by(Interaction.created_at.desc()).limit(5).all()
                    
                    emojis_from_previous = None
                    for prev_inter in previous_user_interactions:
                        if prev_inter.content and not prev_inter.content.startswith("["):
                            # This is a real user message, check for emojis
                            emojis_check = extract_emojis_from_message(prev_inter.content)
                            if emojis_check:
                                emojis_from_previous = emojis_check
                                print(f"   📝 Found emojis in previous message: {len(emojis_from_previous)} emoji(s)")
                                break
                    
                    if emojis_from_previous and bottle.game_started:
                        # Use emojis from previous message to feed the selected character
                        print(f"   🍽️  Feeding {selected_product_id} with emojis from previous message")
                        feed_result = process_emoji_feed(session, bottle, emojis_from_previous)
                        
                        # Send feed feedback
                        try:
                            feedback_sid = send_whatsapp_text(from_number, feed_result['message'])
                            print(f"✅ Feed feedback sent: {feedback_sid}")
                            
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=feed_result['message']
                            )
                            
                            # Award points for successful feed
                            if feed_result.get("feed_complete"):
                                try:
                                    points, title_update = award_points(session, user.id, "feeding", bottle_id=bottle.id)
                                    print(f"   🎯 Points awarded for feeding: {points}")
                                    
                                    # Check for title upgrade
                                    if title_update:
                                        old_title, new_title = title_update
                                        print(f"   🏆 Title upgraded: {old_title} → {new_title}")
                                        try:
                                            send_stats_display(
                                                session=session,
                                                user_id=user.id,
                                                from_number=from_number,
                                                base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                                auto_trigger=True,
                                                achievement_message=f"🎉 Félicitations ! Vous êtes maintenant {new_title} !"
                                            )
                                        except Exception as e:
                                            print(f"   ⚠️  Error sending title upgrade stats: {e}")
                                except Exception as e:
                                    print(f"   ⚠️  Error awarding points: {e}")
                            
                            session.commit()
                            feed_feedback_sent = True
                            
                            # After feeding, immediately send updated game stickers (fullness/emotional)
                            try:
                                # Refresh bottle to get latest state after feeding
                                session.refresh(bottle)
                                
                                if bottle.game_started:
                                    print()
                                    print("🎮 SENDING GAME STICKERS AFTER FEED (feed selection path)")
                                    print("-" * 60)
                                    print(f"   Bottle state: fullness={bottle.fullness_level:.1f}%, accessory_color={bottle.accessory_color}, mood={bottle.mood}")
                                    
                                    # Use PUBLIC_BASE_URL (same as other places in this function)
                                    feed_base_url = PUBLIC_BASE_URL or "http://localhost:5000"
                                    print(f"   Base URL: {feed_base_url}")
                                    
                                    game_stickers = get_stickers_for_state(bottle, feed_base_url)
                                    print(f"   Game stickers returned: {game_stickers is not None}")
                                    
                                    if game_stickers:
                                        # Fullness sticker first
                                        fullness_sticker = game_stickers.get("fullness")
                                        print(f"   Fullness sticker available: {fullness_sticker is not None}")
                                        if fullness_sticker:
                                            print(f"   Fullness sticker: {fullness_sticker.get('filename', 'N/A')}")
                                            print(f"   Fullness sticker URL: {fullness_sticker.get('url', 'N/A')}")
                                            try:
                                                import time
                                                fs_start = time.time()
                                                fullness_sid = send_whatsapp_sticker(
                                                    to_number=from_number,
                                                    media_url=fullness_sticker["url"]
                                                )
                                                fs_duration = time.time() - fs_start
                                                print(f"   ✅ FULLNESS STICKER SENT AFTER FEED (ID: {fullness_sid}, {fs_duration:.2f}s)")
                                            except Exception as e:
                                                print(f"   ⚠️  Error sending fullness sticker after feed: {e}")
                                                import traceback
                                                traceback.print_exc()
                                        else:
                                            print(f"   ⚠️  No fullness sticker found (accessory_color={bottle.accessory_color}, fullness_state={get_fullness_state(bottle.fullness_level)})")
                                        
                                        # Emotional sticker if available
                                        emotional_sticker = game_stickers.get("emotional")
                                        print(f"   Emotional sticker available: {emotional_sticker is not None}")
                                        if emotional_sticker:
                                            print(f"   Emotional sticker: {emotional_sticker.get('filename', 'N/A')}")
                                            print(f"   Emotional sticker URL: {emotional_sticker.get('url', 'N/A')}")
                                            try:
                                                import time
                                                es_start = time.time()
                                                emotional_sid = send_whatsapp_sticker(
                                                    to_number=from_number,
                                                    media_url=emotional_sticker["url"]
                                                )
                                                es_duration = time.time() - es_start
                                                print(f"   ✅ EMOTIONAL STICKER SENT AFTER FEED (ID: {emotional_sid}, {es_duration:.2f}s)")
                                            except Exception as e:
                                                print(f"   ⚠️  Error sending emotional sticker after feed: {e}")
                                                import traceback
                                                traceback.print_exc()
                                    else:
                                        print("   ⚠️  No game stickers returned after feed")
                                        print(f"   Debug: bottle.game_started={bottle.game_started}, accessory_color={bottle.accessory_color}")
                                    print("-" * 60)
                                else:
                                    print(f"   ⚠️  Game not started (bottle.game_started={bottle.game_started}), skipping game stickers")
                            except Exception as e:
                                print(f"   ⚠️  Error sending game stickers after feed: {e}")
                                import traceback
                                traceback.print_exc()
                            
                            return jsonify({
                                "status": "ok",
                                "message": "Feed processed"
                            }), 200
                        except Exception as e:
                            print(f"⚠️  Error sending feed feedback: {e}")
                    else:
                        # No emojis found in previous message, ask user to send emojis
                        ask_emojis_msg = f"Parfait ! Envoie-moi les emojis pour nourrir {get_character_config(selected_product_id)['name']} 🍎"
                        try:
                            ask_sid = send_whatsapp_text(from_number, ask_emojis_msg)
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=ask_emojis_msg
                            )
                            session.commit()
                            return jsonify({
                                "status": "ok",
                                "message": "Asked for emojis"
                            }), 200
                        except Exception as e:
                            print(f"⚠️  Error asking for emojis: {e}")
                
                if bottle.game_started and (message_type in ["emoji", "mixed"] or is_feed_selection):
                    # Check if user has multiple characters and needs to select which one to feed
                    # Only show selection if not already selected via button and message contains emojis
                    user_bottles = session.query(Bottle).filter_by(
                        user_id=user.id,
                        game_started=True,
                        returned=False
                    ).all()
                    
                    if len(user_bottles) > 1 and not is_feed_selection:
                        # Check if message contains emojis
                        emojis_check = extract_emojis_from_message(message_content)
                        if emojis_check:
                            # User has multiple characters - show selection buttons
                            print(f"   👥 User has {len(user_bottles)} characters, showing selection")
                            
                            buttons = []
                            for b in user_bottles:
                                char_config = get_character_config(b.product_id)
                                buttons.append({
                                    "id": f"FEED_{b.product_id}",
                                    "title": f"Nourrir {char_config['name']}"
                                })
                            
                            try:
                                selection_msg = "Quel personnage voulez-vous nourrir ?"
                                button_sid = send_whatsapp_interactive_buttons(
                                    to_number=from_number,
                                    body_text=selection_msg,
                                    buttons=buttons
                                )
                                print(f"   ✅ Character selection buttons sent: {button_sid}")
                                
                                create_interaction(
                                    session=session,
                                    user_id=user.id,
                                    bottle_id=bottle.id,
                                    message_type="interactive",
                                    from_user=False,
                                    content="[Character selection for feeding]"
                                )
                                session.commit()
                                
                                return jsonify({
                                    "status": "ok",
                                    "message": "Character selection sent"
                                }), 200
                            except Exception as e:
                                print(f"   ⚠️  Error sending character selection: {e}")
                                # Fall through to feed current character
                    
                    print()
                    print("=" * 60)
                    print("🍽️  PROCESSING EMOJI FEED")
                    print("=" * 60)
                    
                    emojis = extract_emojis_from_message(message_content)
                    if emojis:
                        print(f"   Found {len(emojis)} emoji(s) in message")
                        print(f"   Feeding character: {bottle.product_id}")
                        print(f"   Accessory color: {bottle.accessory_color}")
                        feed_result = process_emoji_feed(session, bottle, emojis)
                        print(f"   Result: {feed_result['message']}")
                        print(f"   Fullness: {bottle.fullness_level:.1f}%")
                        print(f"   Feed count: {bottle.current_feed_count}/3")
                        print("=" * 60)
                        
                        # Award points for successful feed
                        if feed_result.get("feed_complete"):
                            try:
                                points, title_update = award_points(session, user.id, "feeding", bottle_id=bottle.id)
                                print(f"   🎯 Points awarded for feeding: {points}")
                                
                                # Check for title upgrade
                                if title_update:
                                    old_title, new_title = title_update
                                    print(f"   🏆 Title upgraded: {old_title} → {new_title}")
                                    try:
                                        send_stats_display(
                                            session=session,
                                            user_id=user.id,
                                            from_number=from_number,
                                            base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                                            auto_trigger=True,
                                            achievement_message=f"🎉 Félicitations ! Vous êtes maintenant {new_title} !"
                                        )
                                    except Exception as e:
                                        print(f"   ⚠️  Error sending title upgrade stats: {e}")
                            except Exception as e:
                                print(f"   ⚠️  Error awarding points: {e}")
                        
                        # Send feed feedback immediately
                        try:
                            feedback_sid = send_whatsapp_text(from_number, feed_result['message'])
                            print(f"✅ Feed feedback sent: {feedback_sid}")
                            
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=feed_result['message']
                            )
                            session.commit()
                            feed_feedback_sent = True  # Set flag to skip LLM response

                            # After feeding, immediately send updated game stickers (fullness/emotional)
                            try:
                                # Refresh bottle to get latest state after feeding
                                session.refresh(bottle)
                                
                                if bottle.game_started:
                                    print()
                                    print("🎮 SENDING GAME STICKERS AFTER FEED")
                                    print("-" * 60)
                                    print(f"   Bottle state: fullness={bottle.fullness_level:.1f}%, accessory_color={bottle.accessory_color}, mood={bottle.mood}")
                                    
                                    # Use PUBLIC_BASE_URL (same as other places in this function)
                                    feed_base_url = PUBLIC_BASE_URL or "http://localhost:5000"
                                    print(f"   Base URL: {feed_base_url}")
                                    
                                    game_stickers = get_stickers_for_state(bottle, feed_base_url)
                                    print(f"   Game stickers returned: {game_stickers is not None}")
                                    
                                    if game_stickers:
                                        # Fullness sticker first
                                        fullness_sticker = game_stickers.get("fullness")
                                        print(f"   Fullness sticker available: {fullness_sticker is not None}")
                                        if fullness_sticker:
                                            print(f"   Fullness sticker: {fullness_sticker.get('filename', 'N/A')}")
                                            print(f"   Fullness sticker URL: {fullness_sticker.get('url', 'N/A')}")
                                            try:
                                                import time
                                                fs_start = time.time()
                                                fullness_sid = send_whatsapp_sticker(
                                                    to_number=from_number,
                                                    media_url=fullness_sticker["url"]
                                                )
                                                fs_duration = time.time() - fs_start
                                                print(f"   ✅ FULLNESS STICKER SENT AFTER FEED (ID: {fullness_sid}, {fs_duration:.2f}s)")
                                            except Exception as e:
                                                print(f"   ⚠️  Error sending fullness sticker after feed: {e}")
                                                import traceback
                                                traceback.print_exc()
                                        else:
                                            print(f"   ⚠️  No fullness sticker found (accessory_color={bottle.accessory_color}, fullness_state={get_fullness_state(bottle.fullness_level)})")
                                        
                                        # Emotional sticker if available and not already sent in main flow
                                        emotional_sticker = game_stickers.get("emotional")
                                        print(f"   Emotional sticker available: {emotional_sticker is not None}")
                                        if emotional_sticker and not (sticker_info and sticker_info.get("url")):
                                            print(f"   Emotional sticker: {emotional_sticker.get('filename', 'N/A')}")
                                            print(f"   Emotional sticker URL: {emotional_sticker.get('url', 'N/A')}")
                                            try:
                                                import time
                                                es_start = time.time()
                                                emotional_sid = send_whatsapp_sticker(
                                                    to_number=from_number,
                                                    media_url=emotional_sticker["url"]
                                                )
                                                es_duration = time.time() - es_start
                                                print(f"   ✅ EMOTIONAL STICKER SENT AFTER FEED (ID: {emotional_sid}, {es_duration:.2f}s)")
                                            except Exception as e:
                                                print(f"   ⚠️  Error sending emotional sticker after feed: {e}")
                                                import traceback
                                                traceback.print_exc()
                                    else:
                                        print("   ⚠️  No game stickers returned after feed")
                                        print(f"   Debug: bottle.game_started={bottle.game_started}, accessory_color={bottle.accessory_color}")
                                    print("-" * 60)
                                else:
                                    print(f"   ⚠️  Game not started (bottle.game_started={bottle.game_started}), skipping game stickers")
                            except Exception as e:
                                print(f"   ⚠️  Error sending game stickers after feed: {e}")
                                import traceback
                                traceback.print_exc()
                        except Exception as e:
                            print(f"⚠️  Error sending feed feedback: {e}")
                
                # Check for stats request
                stats_keywords = ["mes statistiques", "mes stats", "mes points", "statistiques", "points", "mon niveau"]
                is_stats_request = any(keyword.lower() in message_content.lower() for keyword in stats_keywords)
                
                if is_stats_request:
                    print()
                    print("=" * 60)
                    print("📊 STATS REQUEST DETECTED")
                    print("=" * 60)
                    try:
                        # Use new visual stats display
                        success = send_stats_display(
                            session=session,
                            user_id=user.id,
                            from_number=from_number,
                            base_url=PUBLIC_BASE_URL or "http://localhost:5000",
                            auto_trigger=False
                        )
                        
                        if success:
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content="[Stats display]"
                            )
                            session.commit()
                            print("✅ Stats display sent")
                        else:
                            print("⚠️  Stats display failed, using text fallback")
                        
                        return jsonify({
                            "status": "ok",
                            "message": "Stats sent"
                        }), 200
                    except Exception as e:
                        print(f"⚠️  Error sending stats: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Check for promo request
                promo_keywords = ["mes promos", "promos", "codes promo", "promotions"]
                is_promo_request = any(keyword.lower() in message_content.lower() for keyword in promo_keywords)
                
                if is_promo_request:
                    print()
                    print("=" * 60)
                    print("🎁 PROMO REQUEST DETECTED")
                    print("=" * 60)
                    try:
                        from supermarket_promos import get_available_promos, format_promos_message
                        
                        promos = get_available_promos(session, user.id)
                        promo_msg = format_promos_message(promos)
                        
                        promo_sid = send_whatsapp_text(from_number, promo_msg)
                        print(f"✅ Promo codes sent: {promo_sid}")
                        
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="text",
                            from_user=False,
                            content="[Promo codes display]"
                        )
                        session.commit()
                        
                        return jsonify({
                            "status": "ok",
                            "message": "Promos sent"
                        }), 200
                    except Exception as e:
                        print(f"⚠️  Error sending promos: {e}")
                
                # Check for rules request (can be asked at any time)
                if bottle.game_started and detect_rules_request(message_content):
                    print()
                    print("=" * 60)
                    print("📋 RULES REQUEST DETECTED")
                    print("=" * 60)
                    try:
                        # Add version query param to bypass WhatsApp media cache
                        rules_url = f"{base_url.rstrip('/')}/rules/regles%20du%20jeu.png?v=2"
                        rules_sid = send_whatsapp_media(from_number, rules_url, "Voici les règles du jeu !")
                        print(f"✅ Rules image sent: {rules_sid}")
                        
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="image",
                            from_user=False,
                            content="Rules image"
                        )
                        session.commit()
                        rules_request_sent = True  # Set flag to skip LLM response
                    except Exception as e:
                        print(f"⚠️  Error sending rules image: {e}")
                
                # Check for character switch request
                switch_keywords = ["switch", "changer", "changer de personnage", "switch character", "changer personnage", "personnage"]
                is_switch_request = any(keyword.lower() in message_content.lower() for keyword in switch_keywords)
                
                # Allow character switch regardless of game_started status
                # Use bottle_state if available to avoid DetachedInstanceError
                if is_switch_request:
                    # Bottle is already imported at top level
                    print()
                    print("=" * 60)
                    print("🔄 CHARACTER SWITCH REQUEST DETECTED")
                    print("=" * 60)
                    # Get all user's characters
                    try:
                        user_bottles = session.query(Bottle).filter_by(user_id=user.id).all()
                    except Exception as query_error:
                        print(f"   ⚠️  Error querying user bottles: {query_error}")
                        user_bottles = []  # Fallback to empty list
                    available_characters = []
                    for b in user_bottles:
                        try:
                            char_config = get_character_config(b.product_id)
                            available_characters.append({
                                "product_id": b.product_id,
                                "name": char_config["name"],
                                "bottle": b
                            })
                        except Exception as char_error:
                            print(f"   ⚠️  Error processing character {b.product_id}: {char_error}")
                            continue
                    
                    # Handle different cases: 0, 1, or multiple characters
                    if len(available_characters) == 0:
                        # No characters found
                        switch_msg = "Aucun personnage disponible pour le moment."
                        try:
                            switch_msg_id = send_whatsapp_text(from_number, switch_msg)
                            print(f"✅ No characters message sent: {switch_msg_id}")
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=switch_msg
                            )
                            session.commit()
                            return jsonify({"status": "ok", "message": "No characters available"}), 200
                        except Exception as e:
                            print(f"❌ Error sending no characters message: {e}")
                    elif len(available_characters) == 1:
                        # Only one character, inform user
                        switch_msg = f"Vous n'avez qu'un seul personnage ({available_characters[0]['name']}) pour le moment."
                        try:
                            switch_msg_id = send_whatsapp_text(from_number, switch_msg)
                            print(f"✅ Switch message sent: {switch_msg_id}")
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=switch_msg
                            )
                            session.commit()
                            return jsonify({"status": "ok", "message": "Switch info sent"}), 200
                        except Exception as e:
                            print(f"❌ Error sending switch info: {e}")
                    else:
                        # Multiple characters, send interactive list
                        try:
                            options = []
                            for char in available_characters:
                                options.append({
                                    "id": char["product_id"],
                                    "title": char["name"],
                                    "description": f"Parler avec {char['name']}"
                                })
                            
                            switch_msg_id = send_whatsapp_interactive_list(
                                to_number=from_number,
                                header_text="Choisir un personnage",
                                body_text="Avec quel personnage voulez-vous parler ?",
                                button_text="Voir les personnages",
                                options=options
                            )
                            print(f"✅ Character selection list sent: {switch_msg_id}")
                            
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="interactive",
                                from_user=False,
                                content="[Character selection list]"
                            )
                            session.commit()
                            return jsonify({"status": "ok", "message": "Character selection sent"}), 200
                        except Exception as e:
                            print(f"❌ Error sending character selection: {e}")
                
                # Handle character switch from interactive message
                # Handle feed character selection (process before getting bottle)
                if body.startswith("[FEED_CHARACTER:"):
                    # Extract product_id and set it for feeding
                    selected_product_id = body.replace("[FEED_CHARACTER:", "").rstrip("]")
                    print(f"   🎯 Feed character selection: {selected_product_id}")
                    # Update product_id to use selected character
                    product_id = selected_product_id
                    # Extract emojis from body if present, otherwise use stored emojis
                    # The body might contain the original emoji message
                    # For now, we'll process this in the feed section below
                
                if body.startswith("[SWITCH_CHARACTER:"):
                    selected_product_id = body.split(":")[1].rstrip("]")
                    print()
                    print("=" * 60)
                    print(f"🔄 SWITCHING TO CHARACTER: {selected_product_id}")
                    print("=" * 60)
                    # Get or create bottle for selected character
                    selected_bottle = get_or_create_bottle(session, user.id, product_id=selected_product_id)
                    bottle = selected_bottle  # Update the active bottle
                    char_config = get_character_config(selected_product_id)
                    switch_confirmation = f"Parfait ! Vous parlez maintenant avec {char_config['name']} ! 🎉"
                    try:
                        switch_msg_id = send_whatsapp_text(from_number, switch_confirmation)
                        print(f"✅ Switch confirmation sent: {switch_msg_id}")
                        # Create interaction with the NEW character's bottle to make it the active one
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=selected_bottle.id,
                            message_type="text",
                            from_user=False,
                            content=switch_confirmation
                        )
                        # Also create a user interaction to establish the new character as active
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=selected_bottle.id,
                            message_type="text",
                            from_user=True,
                            content=body  # The switch command itself
                        )
                        session.commit()
                        # Update bottle_state to reflect the switch
                        if bottle_state is None:
                            bottle_state = {}
                        bottle_state.update({
                            "id": selected_bottle.id,
                            "product_id": selected_product_id,
                            "type": selected_bottle.type,
                            "name": selected_bottle.name,
                            "mood": selected_bottle.mood,
                            "game_started": selected_bottle.game_started,
                        })
                        print(f"   ✅ Updated bottle_state: product_id={selected_product_id}, bottle_id={selected_bottle.id}")
                        return jsonify({"status": "ok", "message": "Character switched"}), 200
                    except Exception as e:
                        print(f"❌ Error sending switch confirmation: {e}")
                
                # Check for renaming request (can be done at any time)
                if bottle.game_started and detect_rename_request(message_content):
                    print()
                    print("=" * 60)
                    print("✏️  RENAME REQUEST DETECTED")
                    print("=" * 60)
                    
                    # Try to extract name from message
                    new_name = extract_name_from_message(message_content)
                    
                    if new_name:
                        # Name found in message, update it
                        old_name = bottle.name or "Bouteille"
                        bottle.name = new_name
                        session.add(bottle)
                        session.commit()
                        session.refresh(bottle)
                        print(f"✅ Bottle renamed from '{old_name}' to '{new_name}'")
                        
                        try:
                            rename_msg = f"Parfait ! Je m'appelle maintenant {new_name} ! 🎉"
                            rename_sid = send_whatsapp_text(from_number, rename_msg)
                            print(f"✅ Rename confirmation sent: {rename_sid}")
                            
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=rename_msg
                            )
                            session.commit()
                            rename_request_sent = True  # Set flag to skip LLM response
                        except Exception as e:
                            print(f"⚠️  Error sending rename confirmation: {e}")
                    else:
                        # No name in message, prompt for it
                        try:
                            rename_prompt = "Quel nom voulez-vous me donner ? 🍒"
                            rename_sid = send_whatsapp_text(from_number, rename_prompt)
                            print(f"✅ Rename prompt sent: {rename_sid}")
                            
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="text",
                                from_user=False,
                                content=rename_prompt
                            )
                            session.commit()
                            rename_request_sent = True  # Set flag to skip LLM response
                        except Exception as e:
                            print(f"⚠️  Error sending rename prompt: {e}")
                
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
                
                # Store product_id while session is active to avoid DetachedInstanceError
                bottle_product_id = bottle.product_id
                
                # Update bottle_state with latest values (bottle_state was initialized early)
                # This ensures we have the most up-to-date state after update_bottle_state
                if bottle_state is None:
                    # Fallback: create bottle_state if it wasn't initialized early (shouldn't happen)
                    bottle_state = {}
                bottle_state.update({
                    "id": bottle.id,
                    "type": bottle.type,
                    "name": bottle.name,
                    "mood": bottle.mood,
                    "personality_level": bottle.personality_level,
                    "fullness_level": bottle.fullness_level if bottle.game_started else None,
                    "accessory_color": bottle.accessory_color if bottle.game_started else None,
                    "current_feed_count": bottle.current_feed_count if bottle.game_started else None,
                    "game_started": bottle.game_started,
                    "product_id": bottle_product_id,  # Store product_id in bottle_state
                })
                
            except OperationalError as db_error:
                # Connection error - reset initialization state to prevent future connection attempts
                reset_db_initialization()
                print(f"⚠️  Database connection lost (continuing without DB): {db_error}")
                # Ensure bottle_state has product_id before closing session
                if bottle and bottle_state is None:
                    bottle_state = {}
                if bottle_state and "product_id" not in bottle_state and bottle:
                    try:
                        bottle_state["product_id"] = bottle.product_id
                    except Exception:
                        bottle_state["product_id"] = product_id or "00001"
            except Exception as db_error:
                # Other database errors
                print(f"⚠️  Database error (continuing without DB): {db_error}")
                import traceback
                traceback.print_exc()
                
                # Ensure bottle_state has product_id before closing session
                if bottle and bottle_state is None:
                    bottle_state = {}
                if bottle_state and "product_id" not in bottle_state and bottle:
                    try:
                        bottle_state["product_id"] = bottle.product_id
                    except Exception:
                        bottle_state["product_id"] = product_id or "00001"
                
                # Continue without database - use basic mode
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except Exception:
                        pass  # Ignore errors when closing failed session
                    session = None
                bottle = None  # Clear bottle reference to prevent DetachedInstanceError

        # Detect emotion from user message using Mistral (for sticker selection)
        detected_emotion = "neutral"
        if message_content and message_content.strip():
            try:
                detected_emotion = detect_emotion_from_message(message_content)
            except Exception as e:
                print(f"   ⚠️  Error detecting emotion from message: {e}")
                detected_emotion = "neutral"
        
        # Get current mood from bottle state (for other purposes, like GIF selection)
        current_mood = bottle_state.get("mood", "neutral") if bottle_state else "neutral"
        print(f"🔍 Current mood (pattern-based): {current_mood}")
        print(f"🎭 Detected emotion (from message): {detected_emotion}")
        
        # Use detected emotion for sticker selection (more accurate than pattern-based mood)
        emotion_for_sticker = detected_emotion
        
        # Check media availability and select response type
        sticker_info = None
        gif_info = None
        response_type = "text_sticker"  # Default
        character_id_for_media = None  # Initialize before database check
        
        # Determine character_id_for_media from bottle_state or product_id (before database operations)
        if bottle_state and "product_id" in bottle_state:
            character_id_for_media = get_character_id(bottle_state["product_id"])
        elif product_id:
            character_id_for_media = get_character_id(product_id)
        else:
            character_id_for_media = get_character_id("00001")  # Default to Cherry
        
        if DATABASE_URL and is_db_initialized() and session:
            # Get bottle_id for response type selection (outside try block to ensure it's available)
            bottle_id = None
            if bottle_state and "id" in bottle_state:
                bottle_id = bottle_state["id"]
            elif session:
                try:
                    user = session.query(User).filter_by(whatsapp_number=from_number).first()
                    if user:
                        bottle = get_active_bottle(session, user.id, product_id=product_id)
                        if bottle:
                            bottle_id = bottle.id
                        else:
                            bottle_id = None
                except Exception as e:
                    print(f"   ⚠️  Error getting bottle_id: {e}")
            
            # Determine last GIF description for this bottle to avoid back-to-back repeats
            last_gif_description = None
            if bottle_id:
                try:
                    recent_interactions = get_recent_interactions(session, bottle_id, limit=10)
                    for inter in reversed(recent_interactions):
                        if inter.from_user == "false" and inter.message_type == "gif" and inter.content:
                            content = inter.content.strip()
                            marker = "[GIF:"
                            if marker in content:
                                inner = content.split(marker, 1)[1]
                                inner = inner.rstrip("]")
                                last_gif_description = inner.strip()
                            else:
                                last_gif_description = content
                            break
                except Exception as e:
                    print(f"   ⚠️  Error getting last GIF description: {e}")
            
            # Get character_id from active bottle - prioritize fresh database lookup
            character_id_for_media = None
            if session:
                try:
                    # First, try to get the most recent active bottle from database
                    user_for_media = session.query(User).filter_by(whatsapp_number=from_number).first()
                    if user_for_media:
                        # Get the most recently interacted bottle (most accurate)
                        recent_bottle = get_active_bottle(session, user_for_media.id, product_id=product_id)
                        if recent_bottle:
                            try:
                                active_product_id = recent_bottle.product_id
                                character_id_for_media = get_character_id(active_product_id)
                                print(f"   📦 Using character_id from recent bottle: {character_id_for_media} (product_id={active_product_id})")
                            except Exception as e:
                                print(f"   ⚠️  Could not access recent_bottle.product_id: {e}")
                except Exception as e:
                    print(f"   ⚠️  Error getting character_id from recent bottle: {e}")
            
            # Fallback: use bottle_state or product_id parameter
            if not character_id_for_media:
                if bottle_state and "product_id" in bottle_state:
                    character_id_for_media = get_character_id(bottle_state["product_id"])
                    print(f"   📦 Using character_id from bottle_state: {character_id_for_media}")
                elif product_id:
                    character_id_for_media = get_character_id(product_id)
                    print(f"   📦 Using character_id from product_id parameter: {character_id_for_media}")
                else:
                    character_id_for_media = get_character_id("00001")  # Default to Cherry
                    print(f"   📦 Using default character_id (Cherry): {character_id_for_media}")
            
            # Determine required hat/bin color from bottle state (accessory_color)
            required_color = None
            if bottle_state:
                required_color = bottle_state.get("accessory_color")

            # Debug logging for sticker selection
            print(f"   🎨 Selecting sticker: emotion={emotion_for_sticker}, character_id={character_id_for_media}, required_color={required_color}")
            if bottle_state:
                print(f"   📦 bottle_state product_id: {bottle_state.get('product_id', 'N/A')}")
            if product_id:
                print(f"   📦 product_id parameter: {product_id}")
            
            # Try to select sticker using detected emotion (with individual error handling)
            try:
                # First try with detected emotion and required hat/bin color
                sticker_info = select_sticker_by_mood(
                    session,
                    emotion_for_sticker,
                    base_url,
                    character_id=character_id_for_media,
                    required_color=required_color,
                )
                if not sticker_info:
                    # Fallback: try with get_emotional_sticker (filename-based)
                    from game_logic import get_emotional_sticker
                    sticker_info = get_emotional_sticker(
                        emotion_for_sticker, base_url, character_id=character_id_for_media, accessory_color=required_color
                    )
                
                if sticker_info:
                    selected_filename = sticker_info.get('filename', 'N/A')
                    print(f"   ✅ Sticker selected: {selected_filename} (emotion={emotion_for_sticker}, character_id={character_id_for_media})")
                    # Verify the selected sticker matches the expected character
                    if character_id_for_media == "00002" and "cherry" in selected_filename.lower():
                        print(f"   ⚠️  WARNING: Selected Cherry sticker ({selected_filename}) when character_id is Pompon (00002)!")
                    elif character_id_for_media == "00001" and "cider" in selected_filename.lower():
                        print(f"   ⚠️  WARNING: Selected Pompon sticker ({selected_filename}) when character_id is Cherry (00001)!")
                else:
                    print(f"   ⚠️  No sticker found for emotion={emotion_for_sticker}, character_id={character_id_for_media}")
            except Exception as sticker_error:
                print(f"   ⚠️  Error selecting sticker: {sticker_error}")
                import traceback
                traceback.print_exc()
                sticker_info = None
            
            # Try to select GIF (with individual error handling)
            # Check if bottle is empty - if so, use money GIFs instead of regular GIFs
            try:
                # Get bottle to check fullness level
                bottle_for_gif = None
                if bottle_state and "id" in bottle_state:
                    bottle_for_gif = session.query(Bottle).filter_by(id=bottle_state["id"]).first()
                elif session:
                    user = session.query(User).filter_by(whatsapp_number=from_number).first()
                    if user:
                        bottle_for_gif = get_active_bottle(session, user.id, product_id=product_id)
                
                # Get character_id for GIF selection
                gif_character_id = None
                if bottle_for_gif:
                    gif_character_id = get_character_id(bottle_for_gif.product_id)
                else:
                    gif_character_id = get_character_id(product_id)
                
                # If bottle is in the "empty" fullness state, use money GIFs
                # Use get_fullness_state() instead of a strict 0.0 comparison to avoid float issues
                if bottle_for_gif and bottle_for_gif.game_started and get_fullness_state(bottle_for_gif.fullness_level) == "empty":
                    print(f"   💰 Bottle is EMPTY state ({bottle_for_gif.fullness_level:.1f}%) - selecting money GIF for deposit incentive")
                    gif_info = select_money_gif(session, base_url, exclude_description=last_gif_description, character_id=gif_character_id)
                else:
                    # Use regular GIFs for full, 2/3, or 1/3 states
                    gif_info = select_gif_by_mood(session, current_mood, base_url, exclude_description=last_gif_description, character_id=gif_character_id)
            except Exception as gif_error:
                print(f"   ⚠️  Error selecting GIF: {gif_error}")
                import traceback
                traceback.print_exc()
                gif_info = None
            
            # Select response type based on rotation logic
            try:
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
                        response_type = "text_sticker"  # Default to text_sticker if neither available
            except Exception as response_error:
                print(f"   ⚠️  Error selecting response type: {response_error}")
                import traceback
                traceback.print_exc()
                # Fallback to simple selection
                if gif_info:
                    response_type = "gif_only"
                elif sticker_info:
                    response_type = "text_sticker"
                else:
                    response_type = "text_sticker"
            
            # Log response type selection (for both characters - Cherry and Pompon)
            print()
            print("🎨 RESPONSE TYPE SELECTION")
            print("-" * 60)
            print(f"   Selected response type: {response_type}")
            print(f"   Character ID: {character_id_for_media}")
            print(f"   Sticker available: {'Yes' if sticker_info else 'No'}")
            if sticker_info:
                print(f"   Sticker URL: {sticker_info.get('url', 'N/A')[:60]}...")
            print(f"   GIF available: {'Yes' if gif_info else 'No'}")
            if gif_info:
                print(f"   GIF URL: {gif_info.get('url', 'N/A')[:60]}...")
            print(f"   Base URL used: {base_url}")
            print("-" * 60)
        
        # Generate reply using LLM (only if needed)
        reply_text = None
        llm_error_occurred = False
        reply_text_valid = False  # Initialize - will be set based on conditions below
        
        # Only generate text if response type requires it and feed feedback/rules/rename not sent
        # #region agent log
        try:
            import json; log_file = open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a', encoding='utf-8'); log_file.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"endpoint.py:882","message":"Before flag check - checking variable existence","data":{"feed_feedback_sent_exists":"feed_feedback_sent" in locals(),"rules_request_sent_exists":"rules_request_sent" in locals(),"rename_request_sent_exists":"rename_request_sent" in locals(),"feed_feedback_sent_value":feed_feedback_sent if "feed_feedback_sent" in locals() else "UNDEFINED"},"timestamp":int(__import__('time').time()*1000)})+'\n'); log_file.close()
        except Exception as e:
            import json; log_file = open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a', encoding='utf-8'); log_file.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"endpoint.py:882","message":"Error checking variables","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)})+'\n'); log_file.close()
        # #endregion
        if feed_feedback_sent or rules_request_sent or rename_request_sent:
            print()
            print("🤖 SKIPPING TEXT GENERATION (Feed feedback already sent)")
            print("-" * 60)
            reply_text = None
            reply_text_valid = True
        elif response_type == "text_sticker":
            print()
            print("🤖 GENERATING REPLY (text_sticker mode)")
            print("-" * 60)
            if character_id_for_media:
                try:
                    # character_id_for_media is already a character_id (like "00001" or "00002")
                    char_product_id = character_id_for_media if character_id_for_media in ["00001", "00002"] else None
                    if char_product_id:
                        char_name = get_character_config(char_product_id).get("name", "Unknown")
                        print(f"   Character: {char_name} (ID: {character_id_for_media})")
                except Exception:
                    pass
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
                
                # Get system prompt for active character
                # Use product_id from bottle_state if available (avoids DetachedInstanceError)
                if bottle_state and "product_id" in bottle_state:
                    active_product_id = bottle_state["product_id"]
                    active_system_prompt = get_system_prompt_for_character(active_product_id)
                    print(f"   System prompt length: {len(active_system_prompt)} chars")
                    print(f"   Character: {get_character_config(active_product_id)['name']} (product_id={active_product_id})")
                elif bottle and session:
                    # Fallback: try to access bottle.product_id (only if session is active)
                    try:
                        active_product_id = bottle.product_id
                        active_system_prompt = get_system_prompt_for_character(active_product_id)
                        print(f"   System prompt length: {len(active_system_prompt)} chars")
                        print(f"   Character: {get_character_config(active_product_id)['name']} (product_id={active_product_id})")
                    except Exception as e:
                        print(f"   ⚠️  Could not access bottle.product_id: {e}")
                        active_system_prompt = get_system_prompt_for_character("00001")
                        print(f"   System prompt length: {len(active_system_prompt)} chars")
                        print(f"   Character: Cherry (product_id=00001) [fallback]")
                else:
                    # Fallback to default character (Cherry) if bottle not available
                    active_system_prompt = get_system_prompt_for_character("00001")
                    print(f"   System prompt length: {len(active_system_prompt)} chars")
                    print(f"   Character: Cherry (product_id=00001) [default - no bottle]")
                print(f"   Calling LLM provider: {os.environ.get('LLM_PROVIDER', 'mistral')} (Mistral AI)")
                
                # Call LLM to generate a reply
                reply_text = generate_reply(
                    system_prompt=active_system_prompt,
                    conversation_history=valid_history,
                    bottle_state=bottle_state,  # Will be used in Phase 5
                    max_tokens=100,  # Increased to allow more nuanced responses while staying short
                    temperature=0.9,  # Slightly higher for more varied responses
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
                    
                    # Apply character-specific slang replacements occasionally (15% chance)
                    # Use product_id from bottle_state to avoid DetachedInstanceError
                    current_product_id = None
                    if bottle_state and "product_id" in bottle_state:
                        current_product_id = bottle_state["product_id"]
                    elif bottle:
                        try:
                            current_product_id = bottle.product_id
                        except Exception:
                            current_product_id = "00001"  # Fallback
                    else:
                        current_product_id = "00001"  # Default
                    
                    if random.random() < 0.15 and current_product_id:  # 15% chance
                        if current_product_id == "00001":
                            # Cherry: Breton slang
                            reply_text = _apply_breton_slang(reply_text)
                        elif current_product_id == "00002":
                            # Pompon: Norman slang
                            reply_text = _apply_norman_slang(reply_text)
                    
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
            print("🤖 SKIPPING TEXT GENERATION (gif_only mode - GIF + sticker)")
            print("-" * 60)
            if character_id_for_media:
                try:
                    char_product_id = character_id_for_media if len(character_id_for_media) == 5 else None
                    if not char_product_id:
                        # character_id_for_media is like "00001" or "00002", get product_id
                        char_product_id = character_id_for_media if character_id_for_media in ["00001", "00002"] else None
                    if char_product_id:
                        char_name = get_character_config(char_product_id).get("name", "Unknown")
                        print(f"   Character: {char_name} (ID: {character_id_for_media})")
                except Exception:
                    pass
            reply_text = None
            reply_text_valid = True  # Allow GIF-only to proceed
        elif feed_feedback_sent:
            # Feed feedback already sent, no need for LLM text - validation already passed
            # reply_text_valid was set to True above, so we're good
            pass
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
        if response_type == "text_sticker" and reply_text:
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
                
                # Check for common error codes
                # 10 = OAuth/permissions error (invalid token, missing permissions)
                # 131030 = Recipient phone number not in allowed list
                # 131026 = Invalid recipient phone number
                # 131047 = Message failed to send
                # 131048 = Rate limit exceeded
                is_delivery_error = False
                delivery_error_type = None
                is_auth_error = False
                
                # Check for OAuth/permissions error (code 10)
                if (error_code == "10" or error_code == 10 or 
                    error_subcode == "10" or error_subcode == 10 or 
                    "10" in str(error_code) or 
                    "OAuthException" in error_str or 
                    "permission" in error_str.lower() or
                    "access token" in error_str.lower()):
                    is_auth_error = True
                elif error_code == "131030" or error_subcode == "131030" or "131030" in error_str or "not in allowed list" in error_str.lower():
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
                
                # Handle OAuth/permissions errors
                if is_auth_error:
                    print()
                    print("=" * 60)
                    print("⚠️  WHATSAPP API PERMISSIONS ERROR")
                    print("=" * 60)
                    print(f"   Error: {error_str}")
                    print()
                    print("   This error typically means:")
                    print("   1. Access token is invalid or expired")
                    print("   2. App doesn't have required permissions")
                    print("   3. Phone number ID or Account ID is incorrect")
                    print()
                    print("   To fix this:")
                    print("   1. Go to Meta Developer Console: https://developers.facebook.com/")
                    print("   2. Navigate to your WhatsApp app")
                    print("   3. Check 'API Setup' → Verify:")
                    print("      - Access Token is valid and not expired")
                    print("      - Phone number ID matches your .env file")
                    print("      - Account ID is correct")
                    print("   4. Check 'App Review' → Ensure required permissions are approved:")
                    print("      - whatsapp_business_messaging")
                    print("      - whatsapp_business_management")
                    print("   5. Regenerate access token if needed")
                    print("   6. Update your .env file with correct values")
                    print("=" * 60)
                    print()
                    # Don't return error response, just log it
                    return jsonify({"status": "error", "message": "WhatsApp API permissions error - check logs"}), 500
                
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
            # Send GIF with emotional sticker
            emotional_sticker_sent = False
            emotional_sticker_filename = None
            if gif_info and gif_info.get("url"):
                # Check if this is a money GIF (deposit incentive)
                is_money_gif = "/money-gifs/" in gif_info.get("url", "")
                
                # If money GIF, send deposit incentive message first
                if is_money_gif:
                    deposit_messages = [
                        "Ramène-moi au supermarché et récupère ta consigne ! 💰",
                        "Je suis vide ! Tu peux me rapporter pour récupérer ta consigne ! 🏪💰",
                        "Retourne-moi au magasin et récupère ta consigne ! 💵",
                        "Rapporte-moi et récupère ta consigne ! C'est simple et tu récupères de l'argent ! 💰"
                    ]
                    deposit_msg = random.choice(deposit_messages)
                    try:
                        print()
                        print("💰 SENDING DEPOSIT INCENTIVE MESSAGE")
                        print("-" * 60)
                        print(f"   To: {from_number}")
                        print(f"   Message: {deposit_msg}")
                        deposit_msg_sid = send_whatsapp_text(from_number, deposit_msg)
                        print(f"   ✅ Deposit message sent: {deposit_msg_sid}")
                        
                        # Log deposit message interaction
                        if DATABASE_URL and is_db_initialized() and session:
                            try:
                                user = session.query(User).filter_by(whatsapp_number=from_number).first()
                                if user:
                                    bottle = get_active_bottle(session, user.id, product_id=product_id)
                                    if bottle:
                                        create_interaction(
                                            session=session,
                                            user_id=user.id,
                                            bottle_id=bottle.id,
                                            message_type="text",
                                            from_user=False,
                                            content=deposit_msg
                                        )
                                        session.commit()
                            except Exception as e:
                                print(f"   ⚠️  Error logging deposit message: {e}")
                    except Exception as e:
                        print(f"   ⚠️  Error sending deposit message: {e}")
                
                print()
                print("🎬 SENDING GIF (gif_only mode - will also send emotional sticker)")
                print("-" * 60)
                print(f"   To: {from_number}")
                if character_id_for_media:
                    try:
                        char_product_id = character_id_for_media if character_id_for_media in ["00001", "00002"] else None
                        if char_product_id:
                            char_name = get_character_config(char_product_id).get("name", "Unknown")
                            print(f"   Character: {char_name} (ID: {character_id_for_media})")
                    except Exception:
                        pass
                print(f"   GIF: {gif_info.get('description', 'N/A')}")
                print(f"   URL: {gif_info['url']}")
                if is_money_gif:
                    print(f"   Type: Money GIF (deposit incentive)")
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
                    
                    # Send emotional sticker along with GIF
                    if character_id_for_media:
                        try:
                            from game_logic import get_emotional_sticker
                            # Get emotional sticker based on detected emotion and required color
                            emotional_sticker = select_sticker_by_mood(
                                session,
                                detected_emotion,
                                base_url,
                                character_id=character_id_for_media,
                                required_color=required_color,
                            )
                            
                            if emotional_sticker and emotional_sticker.get("url"):
                                print()
                                print("😊 SENDING EMOTIONAL STICKER (WITH GIF)")
                                print("-" * 60)
                                print(f"   To: {from_number}")
                                print(f"   Sticker: {emotional_sticker.get('filename', 'N/A')}")
                                print(f"   Emotion: {detected_emotion}")
                                print(f"   Character: {character_id_for_media}")
                                print(f"   URL: {emotional_sticker['url']}")
                                
                                send_start = time.time()
                                emotional_sticker_sid = send_whatsapp_sticker(
                                    to_number=from_number,
                                    media_url=emotional_sticker["url"]
                                )
                                send_duration = time.time() - send_start
                                print(f"   ✅ EMOTIONAL STICKER SENT SUCCESSFULLY")
                                print(f"   Sticker ID: {emotional_sticker_sid}")
                                print(f"   Send duration: {send_duration:.2f}s")
                                print("-" * 60)
                                emotional_sticker_sent = True
                                emotional_sticker_filename = emotional_sticker.get('filename', 'N/A')
                                
                                # If user has multiple characters, send the other character's sticker too
                                if session and DATABASE_URL and is_db_initialized():
                                    try:
                                        user_bottles = session.query(Bottle).filter_by(
                                            user_id=user.id,
                                            game_started=True,
                                            returned=False
                                        ).all()
                                        
                                        if len(user_bottles) > 1:
                                            # Find the other character(s)
                                            other_bottles = [b for b in user_bottles if b.product_id != active_product_id]
                                            
                                            for other_bottle in other_bottles[:1]:  # Send max 1 other character sticker
                                                other_character_id = get_character_id(other_bottle.product_id)
                                                other_char_config = get_character_config(other_bottle.product_id)
                                                
                                                # Get emotional sticker for other character with same emotion
                                                other_emotional_sticker = None
                                                try:
                                                    other_emotional_sticker = select_sticker_by_mood(
                                                        session,
                                                        detected_emotion,
                                                        base_url,
                                                        character_id=other_character_id,
                                                        required_color=required_color,
                                                    )
                                                    if not other_emotional_sticker:
                                                        other_emotional_sticker = get_emotional_sticker(
                                                            detected_emotion, base_url, character_id=other_character_id, accessory_color=required_color
                                                        )
                                                except Exception as e:
                                                    print(f"   ⚠️  Error selecting other character emotional sticker: {e}")
                                                
                                                if other_emotional_sticker and other_emotional_sticker.get("url"):
                                                    print()
                                                    print(f"😊 SENDING OTHER CHARACTER EMOTIONAL STICKER: {other_char_config['name']}")
                                                    print("-" * 60)
                                                    print(f"   Character: {other_char_config['name']} (ID: {other_character_id})")
                                                    print(f"   Sticker: {other_emotional_sticker.get('filename', 'N/A')}")
                                                    print(f"   Emotion: {detected_emotion}")
                                                    
                                                    try:
                                                        other_emo_send_start = time.time()
                                                        other_emo_sticker_sid = send_whatsapp_sticker(
                                                            to_number=from_number,
                                                            media_url=other_emotional_sticker["url"]
                                                        )
                                                        other_emo_send_duration = time.time() - other_emo_send_start
                                                        print(f"   ✅ OTHER CHARACTER EMOTIONAL STICKER SENT")
                                                        print(f"   Sticker ID: {other_emo_sticker_sid}")
                                                        print(f"   Send duration: {other_emo_send_duration:.2f}s")
                                                        print("-" * 60)
                                                    except Exception:
                                                        # Do not fail the webhook if the bonus sticker fails.
                                                        # This can happen if WhatsApp returns an unexpected response.
                                                        print("   ⚠️  Could not send other character emotional sticker (non-blocking).")
                                    except Exception as other_char_error:
                                        # Any failure in multi-character bonus logic should be non-blocking.
                                        print(f"   ⚠️  Skipping other character emotional sticker due to a non-critical error: {other_char_error}")
                                        import traceback
                                        traceback.print_exc()
                            else:
                                print(f"   ⚠️  No emotional sticker found for emotion={detected_emotion}, character_id={character_id_for_media}")
                        except Exception as sticker_error:
                            print(f"   ⚠️  Error sending emotional sticker with GIF: {sticker_error}")
                            import traceback
                            traceback.print_exc()
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
                print("🎨 SENDING STICKER (text_sticker mode - following text)")
                print("-" * 60)
                print(f"   To: {from_number}")
                if character_id_for_media:
                    try:
                        char_product_id = character_id_for_media if character_id_for_media in ["00001", "00002"] else None
                        if char_product_id:
                            char_name = get_character_config(char_product_id).get("name", "Unknown")
                            print(f"   Character: {char_name} (ID: {character_id_for_media})")
                    except Exception:
                        pass
                if sticker_info:
                    print(f"   Sticker: {sticker_info.get('filename', 'N/A')}")
                    print(f"   URL: {sticker_info.get('url', 'N/A')}")
                else:
                    print(f"   Sticker: N/A (sticker_info is None)")
                try:
                    import time
                    send_start = time.time()
                    if sticker_info and sticker_info.get("url"):
                        sticker_sid = send_whatsapp_sticker(
                            to_number=from_number,
                            media_url=sticker_info["url"]
                        )
                        send_duration = time.time() - send_start
                        print(f"   ✅ STICKER SENT SUCCESSFULLY")
                        print(f"   Sticker ID: {sticker_sid}")
                        print(f"   Send duration: {send_duration:.2f}s")
                        print("-" * 60)
                        
                        # If user has multiple characters, send the other character's sticker too
                        if session and DATABASE_URL and is_db_initialized():
                            try:
                                user_bottles = session.query(Bottle).filter_by(
                                    user_id=user.id,
                                    game_started=True,
                                    returned=False
                                ).all()
                                
                                if len(user_bottles) > 1:
                                    # Find the other character(s)
                                    other_bottles = [b for b in user_bottles if b.product_id != active_product_id]
                                    
                                    for other_bottle in other_bottles[:1]:  # Send max 1 other character sticker
                                        other_character_id = get_character_id(other_bottle.product_id)
                                        other_char_config = get_character_config(other_bottle.product_id)
                                        
                                        # Get sticker for other character with same emotion
                                        other_sticker_info = None
                                        try:
                                            other_sticker_info = select_sticker_by_mood(
                                                session,
                                                emotion_for_sticker,
                                                base_url,
                                                character_id=other_character_id,
                                                required_color=required_color,
                                            )
                                            if not other_sticker_info:
                                                from game_logic import get_emotional_sticker
                                                other_sticker_info = get_emotional_sticker(
                                                    emotion_for_sticker, base_url, character_id=other_character_id, accessory_color=required_color
                                                )
                                        except Exception as e:
                                            print(f"   ⚠️  Error selecting other character sticker: {e}")
                                        
                                        if other_sticker_info and other_sticker_info.get("url"):
                                            print()
                                            print(f"🎨 SENDING OTHER CHARACTER STICKER: {other_char_config['name']}")
                                            print("-" * 60)
                                            print(f"   Character: {other_char_config['name']} (ID: {other_character_id})")
                                            print(f"   Sticker: {other_sticker_info.get('filename', 'N/A')}")
                                            print(f"   Emotion: {emotion_for_sticker}")
                                            
                                            try:
                                                other_send_start = time.time()
                                                other_sticker_sid = send_whatsapp_sticker(
                                                    to_number=from_number,
                                                    media_url=other_sticker_info["url"]
                                                )
                                                other_send_duration = time.time() - other_send_start
                                                print(f"   ✅ OTHER CHARACTER STICKER SENT")
                                                print(f"   Sticker ID: {other_sticker_sid}")
                                                print(f"   Send duration: {other_send_duration:.2f}s")
                                                print("-" * 60)
                                            except Exception as other_error:
                                                print(f"   ⚠️  Error sending other character sticker: {other_error}")
                            except Exception as multi_char_error:
                                print(f"   ⚠️  Error sending other character sticker: {multi_char_error}")
                    else:
                        print(f"   ⚠️  Cannot send sticker: sticker_info is None or missing URL")
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
                    if error_subcode:
                        print(f"   Error subcode: {error_subcode}")
                    import traceback
                    traceback.print_exc()
                    print("-" * 60)
                    # Text was already sent, so that's OK - don't fail the webhook
            else:
                print()
                print("ℹ️  Text+sticker response selected but no sticker available")
                print("   Sending text-only response")
        
        # text_only: No media to send (already handled above)
        
        # GAME LOGIC: Send game stickers only for emoji feeds (or explicit feed selections)
        # Check if game is started using bottle_state to avoid DetachedInstanceError
        # Never access bottle.game_started directly here - bottle may be detached from session
        game_started = bottle_state.get("game_started") if bottle_state else False
        if session and DATABASE_URL and bottle and game_started and (message_type in ["emoji", "mixed"] or is_feed_selection) and not feed_feedback_sent:
            try:
                # Refresh bottle to get latest state
                session.refresh(bottle)
                
                # Store product_id while session is active to avoid DetachedInstanceError
                try:
                    bottle_product_id_for_stickers = bottle.product_id
                except Exception as e:
                    print(f"   ⚠️  Could not access bottle.product_id: {e}")
                    # Fallback to product_id from bottle_state or default
                    bottle_product_id_for_stickers = bottle_state.get("product_id") if bottle_state else product_id or "00001"
                
                print(f"   🎮 Getting game stickers for product_id={bottle_product_id_for_stickers}")
                
                # Get stickers for current state (character_id is derived from bottle.product_id in get_stickers_for_state)
                game_stickers = get_stickers_for_state(bottle, base_url)
                
                if not game_stickers:
                    print(f"   ⚠️  No game stickers returned for product_id={bottle_product_id_for_stickers}")
                else:
                    print(f"   ✅ Game stickers found: fullness={game_stickers.get('fullness') is not None}, emotional={game_stickers.get('emotional') is not None}")
                
                # Send fullness sticker if available
                if game_stickers.get("fullness"):
                    fullness_sticker = game_stickers["fullness"]
                    print()
                    print("🎮 SENDING FULLNESS STICKER")
                    print("-" * 60)
                    print(f"   To: {from_number}")
                    print(f"   Sticker: {fullness_sticker.get('filename', 'N/A')}")
                    print(f"   Fullness: {bottle.fullness_level:.1f}% ({get_fullness_state(bottle.fullness_level)})")
                    print(f"   URL: {fullness_sticker['url']}")
                    try:
                        import time
                        send_start = time.time()
                        fullness_sid = send_whatsapp_sticker(
                            to_number=from_number,
                            media_url=fullness_sticker["url"]
                        )
                        send_duration = time.time() - send_start
                        print(f"   ✅ FULLNESS STICKER SENT")
                        print(f"   Sticker ID: {fullness_sid}")
                        print(f"   Send duration: {send_duration:.2f}s")
                        print("-" * 60)
                        
                        # Log sticker interaction
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="sticker",
                            from_user=False,
                            content=f"[Fullness sticker: {fullness_sticker['filename']}]"
                        )
                    except Exception as e:
                        print(f"   ❌ Error sending fullness sticker: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Send emotional sticker if available (and not already sent as part of normal flow)
                if game_stickers.get("emotional") and not (sticker_info and sticker_info.get("url")):
                    emotional_sticker = game_stickers["emotional"]
                    print()
                    print("😊 SENDING EMOTIONAL STICKER")
                    print("-" * 60)
                    print(f"   To: {from_number}")
                    print(f"   Sticker: {emotional_sticker.get('filename', 'N/A')}")
                    print(f"   Mood: {bottle.mood}")
                    print(f"   URL: {emotional_sticker['url']}")
                    try:
                        import time
                        send_start = time.time()
                        emotional_sid = send_whatsapp_sticker(
                            to_number=from_number,
                            media_url=emotional_sticker["url"]
                        )
                        send_duration = time.time() - send_start
                        print(f"   ✅ EMOTIONAL STICKER SENT")
                        print(f"   Sticker ID: {emotional_sid}")
                        print(f"   Send duration: {send_duration:.2f}s")
                        print("-" * 60)
                        
                        # Log sticker interaction
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="sticker",
                            from_user=False,
                            content=f"[Emotional sticker: {emotional_sticker['filename']}]"
                        )
                    except Exception as e:
                        print(f"   ❌ Error sending emotional sticker: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Check if bottle is in the "empty" state and send special message
                if get_fullness_state(bottle.fullness_level) == "empty":
                    print()
                    print("=" * 60)
                    print("🏠 BOTTLE IS EMPTY - WANTS TO RETURN HOME")
                    print("=" * 60)
                    # Randomly choose one of the return home messages
                    return_home_messages = [
                        "Je suis toute vide ! Ramène-moi chez moi 🏠, au supermarché.",
                        "Ma famille me manque… ramène-moi à la maison 🏠, au supermarché 💔"
                    ]
                    return_home_msg = random.choice(return_home_messages)
                    try:
                        return_sid = send_whatsapp_text(from_number, return_home_msg)
                        print(f"✅ Return home message sent: {return_sid}")
                        
                        create_interaction(
                            session=session,
                            user_id=user.id,
                            bottle_id=bottle.id,
                            message_type="text",
                            from_user=False,
                            content=return_home_msg
                        )
                        session.commit()
                    except Exception as e:
                        print(f"❌ Error sending return home message: {e}")
                
                session.commit()
            except Exception as e:
                print(f"⚠️  Error sending game stickers: {e}")
                import traceback
                traceback.print_exc()

        # Log outgoing interactions (if database is available)
        if session and DATABASE_URL:
            try:
                user = session.query(User).filter_by(whatsapp_number=from_number).first()
                if user:
                    bottle = get_active_bottle(session, user.id, product_id=product_id)
                    if not bottle:
                        bottle = get_or_create_bottle(session, user.id, product_id=product_id or "00001")
                    
                    # Log text message if sent
                    if response_type == "text_sticker" and reply_text:
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
                    
                    # Log emotional sticker if sent with GIF
                    if response_type == "gif_only" and emotional_sticker_sent and emotional_sticker_filename:
                        try:
                            create_interaction(
                                session=session,
                                user_id=user.id,
                                bottle_id=bottle.id,
                                message_type="sticker",
                                from_user=False,
                                content=f"[Emotional sticker with GIF: {emotional_sticker_filename}]"
                            )
                        except Exception as e:
                            print(f"   ⚠️  Error logging emotional sticker with GIF: {e}")
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

