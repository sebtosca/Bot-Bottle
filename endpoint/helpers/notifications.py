import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List

from sqlalchemy import or_

from db.db import User, Bottle  # optionally: Outbox
from core.game import check_and_decrease_fullness, get_fullness_state
from models.characters import get_character_config
from services.whatsapp import send_whatsapp_text

logger = logging.getLogger(__name__)

COOLDOWN = timedelta(hours=1)
HUNGRY_THRESHOLD = 33.0


@dataclass(frozen=True)
class Hungry:
    name: str
    state: str  # e.g. "empty", ...
    fullness: float


def _mask(phone_number: str) -> str:
    return (phone_number[:4] + "****") if phone_number and len(phone_number) >= 4 else "****"


# 1) Separate: state update (pure-ish, idempotent-ish)
def update_fullness(bottles: Iterable[Bottle]) -> None:
    for b in bottles:
        check_and_decrease_fullness(b)  # ideally moved to a scheduled job later


# 1) Separate: read-only selection
def find_hungry_bottles(bottles: Iterable[Bottle]) -> List[Hungry]:
    cache = {}
    hungry: List[Hungry] = []

    for b in bottles:
        state = get_fullness_state(b.fullness_level)
        if state != "empty" and b.fullness_level >= HUNGRY_THRESHOLD:
            continue

        cfg = cache.setdefault(b.product_id, get_character_config(b.product_id))
        hungry.append(Hungry(cfg["name"], state, b.fullness_level))

    return hungry


def _build_message(hungry: List[Hungry]) -> str:
    names = [h.name for h in hungry]
    any_empty = any(h.state == "empty" for h in hungry)

    if len(names) == 1:
        return f"{names[0]} est vide ! Ramène-moi au supermarché 🏠" if any_empty else f"{names[0]} a faim ! Nourris-moi 🍎"

    joined = " et ".join(names) if len(names) == 2 else ", ".join(names[:-1]) + " et " + names[-1]
    return f"{joined} sont vides ! Ramenez-nous au supermarché 🏠🏠" if any_empty else f"{joined} ont faim ! Nourris-les 🍎🥤"


# 2) Anti-duplicate: atomic cooldown guard
def acquire_notification_slot(session, user_id: int, now: datetime) -> bool:
    cutoff = now - COOLDOWN
    updated = (
        session.query(User)
        .filter(
            User.id == user_id,
            or_(User.last_notification_sent.is_(None), User.last_notification_sent < cutoff),
        )
        .update({User.last_notification_sent: now}, synchronize_session=False)
    )
    return updated == 1


# 3) Separate: side effect (enqueue preferred)
def send_notification(session, user_id: int, recipient_phone_number: str, message: str) -> None:
    """
    Preferred: write to an Outbox table here.
    Fallback: direct send (not ideal for scale).
    """
    # If you add Outbox:
    # session.add(Outbox(user_id=user_id, to_number=recipient_phone_number, message=message, status="pending"))
    # return

    send_whatsapp_text(recipient_phone_number, message)


def check_and_notify_hungry_characters(session, user_id: int, recipient_phone_number: str) -> None:
    user = session.query(User).filter(User.id == user_id).one_or_none()
    if not user:
        return

    q = session.query(Bottle).filter(Bottle.user_id == user_id, Bottle.game_started.is_(True))
    if hasattr(Bottle, "returned"):
        q = q.filter(Bottle.returned.is_(False))

    bottles = q.all()
    if not bottles:
        return

    update_fullness(bottles)               # 1) state update
    hungry = find_hungry_bottles(bottles)  # 1) read-only

    now = datetime.utcnow()
    session.flush()  # persist bottle mutations before deciding

    if not hungry:
        session.commit()
        return

    # 2) atomic anti-duplicate guard
    if not acquire_notification_slot(session, user_id, now):
        session.commit()
        return

    message = _build_message(hungry)

    try:
        logger.info(
            "Hunger notification queued/sent",
            extra={"user_id": user_id, "recipient_phone_number": _mask(recipient_phone_number), "hungry_count": len(hungry)},
        )
        send_notification(session, user_id, recipient_phone_number, message)  # 3) side effect
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Hunger notification failed", extra={"user_id": user_id, "recipient_phone_number": _mask(recipient_phone_number)})
