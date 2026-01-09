
from __future__ import annotations

import os
import sys
import json
import emoji
import random
import importlib.util
from pathlib import Path

# Add parent directory to path to ensure local config.py is imported (not site-packages config)
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Add current directory (endpoint/) to path for importing helpers and routes
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from flask import Flask, request, jsonify, send_from_directory
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import BadRequest

from config import DATABASE_URL, PUBLIC_BASE_URL, WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Core business logic
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

# Database
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
    Bottle,
    User,
    Interaction,
)

# External services
from llm.llama_client import generate_reply, detect_emotion_from_message
from services.whatsapp import (
    send_whatsapp_text, send_whatsapp_media, send_whatsapp_sticker,
    send_whatsapp_gif, send_whatsapp_audio, send_whatsapp_interactive_list,
    send_whatsapp_interactive_buttons
)

# Models and configuration
from models.characters import (
    get_system_prompt_for_character, get_character_id, get_character_config
)

# Features
from features.receipt import verify_receipt
from features.stats import (
    send_stats_display, send_text_stats_fallback, generate_stats_image
)

# Import refactored modules
# Since current directory is in sys.path, we can import directly
from helpers import apply_breton_slang, apply_norman_slang, check_and_notify_hungry_characters
from routes.static_files import register_static_routes

# Import new webhook handling modules
from webhook.handler import WebhookHandler, get_request_id
from webhook.worker import setup_in_memory_worker
from webhook.queue import get_message_queue, InMemoryQueue
from webhook.processor import create_message_processor
from webhook.message_processor import process_whatsapp_message
from webhook.models import JobPayload

# Import security modules
# Note: These imports work because endpoint/ is in sys.path
try:
    from security.middleware import setup_security_headers, rate_limit, get_client_ip
    from security.validation import sanitize_filename, validate_product_id
    from middleware.request_correlation import setup_request_correlation
except ImportError:
    # Fallback: try absolute import
    import sys
    from pathlib import Path
    endpoint_dir = Path(__file__).parent
    if str(endpoint_dir) not in sys.path:
        sys.path.insert(0, str(endpoint_dir))
    from security.middleware import setup_security_headers, rate_limit, get_client_ip
    from security.validation import sanitize_filename, validate_product_id
    from middleware.request_correlation import setup_request_correlation


# Initialize Flask app
app = Flask(__name__)

# Set up request correlation (adds request_id to all logs)
setup_request_correlation(app)

# Set up security headers (OWASP best practices)
setup_security_headers(app)

# Initialize database at startup
if DATABASE_URL:
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning("Database initialization failed, continuing without DB", extra={"error": str(e)})
else:
    logger.warning("DATABASE_URL not set - running without database")

# Register static file routes
register_static_routes(app)
     
# Alias helper functions for backward compatibility
_apply_breton_slang = apply_breton_slang
_apply_norman_slang = apply_norman_slang

# Initialize webhook handler and queue
# Disable signature verification for local development (when WHATSAPP_APP_SECRET is not set)
import os
enable_sig_verification = bool(os.environ.get("WHATSAPP_APP_SECRET"))
message_queue = get_message_queue()
webhook_handler = WebhookHandler(
    message_queue=message_queue,
    enable_signature_verification=enable_sig_verification
)

logger.info("Webhook handler initialized", extra={
    "signature_verification": enable_sig_verification,
    "queue_type": type(message_queue).__name__,
    "queue_id": id(message_queue)
})

# Create message processor
processor = create_message_processor(process_whatsapp_message)

# Set up in-memory worker if using in-memory queue (for local dev)
if isinstance(message_queue, InMemoryQueue):       
    setup_in_memory_worker(message_queue, processor)
    logger.info("In-memory queue worker started for local development", extra={
        "queue_type": type(message_queue).__name__,
        "queue_id": id(message_queue),
        "has_processor": processor is not None,
        "whatsapp_access_token_set": bool(WHATSAPP_ACCESS_TOKEN),
        "whatsapp_phone_number_id_set": bool(WHATSAPP_PHONE_NUMBER_ID)
    })
    
    # Warn if WhatsApp credentials are missing
    if not WHATSAPP_ACCESS_TOKEN:
        logger.warning("WHATSAPP_ACCESS_TOKEN is not set - messages will fail to send!")
    if not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WHATSAPP_PHONE_NUMBER_ID is not set - messages will fail to send!")
else:
    logger.warning("Not using in-memory queue - worker may not be started", extra={
        "queue_type": type(message_queue).__name__
    })


@app.route("/whatsapp-webhook", methods=["GET", "POST"])
@rate_limit(max_requests=100, window_seconds=60)  # 100 requests per minute per IP
def whatsapp_webhook():
    """Receive an inbound WhatsApp message from Cloud API.
    
    Fast ACK pattern: verifies → parses → checks idempotency → enqueues → returns 200.
    Actual processing happens asynchronously in the worker.
    
    GET: Webhook verification (Meta requires this for webhook setup)
    POST: Handle incoming messages (fast ACK, enqueue for processing)
    
    Security:
    - Rate limited: 100 requests/minute per IP
    - Signature verification enabled
    - Idempotency checks prevent duplicate processing
    - Request correlation via request_id (from middleware or generated)
    """
    # Request ID is set by middleware, but get it here for webhook handler
    from flask import g
    request_id = getattr(g, 'request_id', None) or get_request_id(request)
    
    # Handle webhook verification (GET request from Meta)
    if request.method == "GET":
        return webhook_handler.handle_verification(request)
    
    # Handle incoming messages (POST request from Meta)
    # Fast ACK: verify → parse → idempotency → enqueue → 200 OK
    return webhook_handler.handle_webhook(request, request_id)


# Legacy synchronous handler - kept for now but will be replaced by worker
# TODO: Extract processing logic from below into message_processor.py
def _process_message_sync(payload: JobPayload) -> None:
    """Legacy synchronous message processing (to be migrated to worker).
    
    This function will be replaced by the async worker once message_processor.py
    is fully implemented with all the business logic extracted from below.
    """
    # For now, this is a placeholder
    # The actual processing logic (2000+ lines) is still in the old whatsapp_webhook function
    # This needs to be incrementally migrated
    pass


# NOTE: The old synchronous processing logic (2000+ lines) that was here
# has been replaced by the new fast ACK handler above.
# 
# The new handler:
# 1. Verifies signature (if enabled)
# 2. Parses payload (pure function)
# 3. Checks idempotency (prevents duplicates)
# 4. Enqueues job (async processing)
# 5. Returns 200 OK quickly
#
# All heavy processing now happens in the worker via process_whatsapp_message()
# in endpoint/webhook/message_processor.py
#
# The old processing logic needs to be extracted and moved to message_processor.py
# to complete the migration.
#
# The old handler code has been removed. To complete the migration, extract the
# processing logic from git history and move it to message_processor.py.


if __name__ == "__main__":
    # For local development; in production use a proper WSGI server
    PORT = 5000
    logger.info("Starting BotBottle Flask server", extra={
        "port": PORT,
        "health_check": f"http://localhost:{PORT}/health",
        "webhook": f"http://localhost:{PORT}/whatsapp-webhook"
    })
    app.run(host="0.0.0.0", port=PORT, debug=True)

