"""Static file serving routes for stickers, GIFs, audio, etc."""

import logging
import mimetypes
from pathlib import Path
from urllib.parse import unquote

from flask import Flask, Response, jsonify, request, send_from_directory, g, has_request_context

from config import DATABASE_URL, PUBLIC_BASE_URL
from core.points import get_user_stats
from db.db import User, get_session, is_db_initialized
from features.stats.visualizer import generate_stats_image
from models.characters import get_character_config

from endpoint.security.middleware import rate_limit, get_client_ip
from endpoint.security.validation import sanitize_filename, validate_product_id, ValidationError

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # adjust if needed
RULES_DIR = PROJECT_ROOT / "Rule"
MONEY_GIF_DIR = PROJECT_ROOT / "money_GIF"

IMG_EXTS = {".webp", ".png", ".jpg", ".jpeg"}
VID_EXTS = {".mp4", ".gif"}
AUD_EXTS = {".mp3", ".ogg", ".wav", ".m4a"}


def _rid() -> str | None:
    return getattr(g, "request_id", None) if has_request_context() else None


def _mask_ip() -> str:
    ip = get_client_ip(request) or ""
    return (ip[:4] + "****") if len(ip) >= 4 else "****"


def _bad_filename(msg: str, filename: str, request_id: str | None):
    logger.warning(msg, extra={"request_id": request_id, "file_name": filename})
    return jsonify({"error": "Invalid filename"}), 400


def _serve_file(
    directory: Path,
    filename: str,
    allowed_exts: set[str],
    log_label: str,
    *,
    request_id: str | None,
):
    try:
        filename = sanitize_filename(filename)
    except ValidationError as e:
        logger.warning(f"{log_label}: invalid filename", extra={"request_id": request_id, "error": str(e)})
        return jsonify({"error": "Invalid filename"}), 400

    ext = Path(filename).suffix.lower()
    if ext not in allowed_exts:
        return _bad_filename(f"{log_label}: invalid extension", filename, request_id)

    path = directory / filename
    if not path.exists():
        logger.warning(f"{log_label}: not found", extra={"request_id": request_id, "file_name": filename})
        return jsonify({"error": "Not found"}), 404

    mimetype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    logger.debug(
        f"{log_label}: serving",
        extra={"request_id": request_id, "file_name": filename, "remote_addr": _mask_ip(), "mimetype": mimetype},
    )
    return send_from_directory(str(directory), filename, mimetype=mimetype)


def register_static_routes(app: Flask) -> None:
    @app.route("/health", methods=["GET"])
    @rate_limit(max_requests=60, window_seconds=60)
    def health():
        logger.debug("Health check", extra={"request_id": _rid()})
        return {"status": "ok"}, 200

    @app.route("/money-gifs/<filename>", methods=["GET"])
    @rate_limit(max_requests=200, window_seconds=60)
    def serve_money_gif(filename: str):
        return _serve_file(MONEY_GIF_DIR, filename, VID_EXTS, "money-gif", request_id=_rid())


    @app.route("/rules/<filename>", methods=["GET"])
    @rate_limit(max_requests=100, window_seconds=60)
    def serve_rules(filename: str):
        return _serve_file(RULES_DIR, filename, IMG_EXTS, "rules", request_id=_rid())

    @app.route("/gifs/<filename>", methods=["GET"])
    @rate_limit(max_requests=200, window_seconds=60)
    def serve_gif(filename: str):
        rid = _rid()
        character_id = request.args.get("character_id", "00001")
        if not validate_product_id(character_id):
            logger.warning("gif: invalid character_id", extra={"request_id": rid, "character_id": character_id})
            character_id = "00001"

        gifs_dir = PROJECT_ROOT / get_character_config(character_id)["gif_dir"]
        resp = _serve_file(gifs_dir, filename, VID_EXTS, "gif", request_id=rid)
        # _serve_file returns tuple (response, status) for errors, Response object for success
        if isinstance(resp, tuple):
            if resp[1] != 404:  # found or bad request
                return resp
        else:
            # Success - return the Response object
            return resp

        # fallback
        fallback_dir = PROJECT_ROOT / ("Cherry_GIF" if character_id == "00002" else "pompon_GIF")
        return _serve_file(fallback_dir, filename, VID_EXTS, "gif-fallback", request_id=rid)

    @app.route("/feeding-stickers/<filename>", methods=["GET"])
    @rate_limit(max_requests=200, window_seconds=60)
    def serve_feeding_sticker(filename: str):
        rid = _rid()
        character_id = request.args.get("character_id", "00001")
        if not validate_product_id(character_id):
            logger.warning("feeding: invalid character_id", extra={"request_id": rid, "character_id": character_id})
            character_id = "00001"

        stickers_dir = PROJECT_ROOT / get_character_config(character_id)["feeding_sticker_dir"]
        resp = _serve_file(stickers_dir, filename, {".webp"}, "feeding-sticker", request_id=rid)
        # _serve_file returns tuple (response, status) for errors, Response object for success
        if isinstance(resp, tuple):
            if resp[1] != 404:
                return resp
        else:
            # Success - return the Response object
            return resp
        #fallback
        fallback_dir = PROJECT_ROOT / ("feeding_game_logic_stickers" if character_id == "00002" else "Pompon_normand_feeding_game_logic_stickers")
        return _serve_file(fallback_dir, filename, {".webp"}, "feeding-sticker-fallback", request_id=rid)

    @app.route("/stickers/<filename>", methods=["GET"])
    @rate_limit(max_requests=200, window_seconds=60)
    def serve_sticker(filename: str):
        rid = _rid()
        try:
            sanitized = sanitize_filename(filename)
        except ValidationError:
            return jsonify({"error": "Invalid filename"}), 400

        ext = Path(sanitized).suffix.lower()
        if ext not in IMG_EXTS:
            return jsonify({"error": "Invalid filename"}), 400

        name_lower = sanitized.lower()
        candidates: list[Path] = []

        if "bouteille_affamee" in name_lower:
            candidates += [
                PROJECT_ROOT / "feeding_game_logic_stickers",
                PROJECT_ROOT / "Pompon_normand_feeding_game_logic_stickers",
            ]

        if "cider" in name_lower:
            candidates += [PROJECT_ROOT / "Pompom_normand_emotional_sticker", PROJECT_ROOT / "stickers"]
        else:
            candidates += [PROJECT_ROOT / "stickers", PROJECT_ROOT / "Pompom_normand_emotional_sticker"]

        for d in candidates:
            if (d / sanitized).exists():
                return send_from_directory(str(d), sanitized, mimetype=mimetypes.guess_type(sanitized)[0])

        logger.warning("sticker: not found", extra={"request_id": rid, "file_name": sanitized})
        return jsonify({"error": "Sticker not found"}), 404

    @app.route("/stats-image/<int:user_id>", methods=["GET"])
    @rate_limit(max_requests=30, window_seconds=60)  # ✅ protect it
    def serve_stats_image(user_id: int):
        if not DATABASE_URL or not is_db_initialized():
            return jsonify({"error": "Database not available"}), 503

        session = None
        try:
            session = get_session()
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            stats = get_user_stats(session, user_id)
            if not stats:
                return jsonify({"error": "Could not generate stats"}), 500

            image_bytes = generate_stats_image(stats, PUBLIC_BASE_URL)
            return Response(image_bytes, mimetype="image/png", headers={"Cache-Control": "no-cache, no-store"})
        except Exception:
            logger.exception("Error generating stats image", extra={"user_id": user_id, "request_id": _rid()})
            return jsonify({"error": "Error generating image"}), 500
        finally:
            if session:
                session.close()
