"""Supermarket promotion code management based on user level.

Manages promo codes and discounts available to users based on their title/points.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from db.db import User
from core.points import get_user_stats


# Promo codes by title level
PROMO_CODES = {
    "Novice": [
        {
            "supermarket": "Carrefour",
            "discount": "5%",
            "code": "BOTBOTTLE5",
            "description": "5% de réduction sur vos achats",
            "min_points": 0,
        }
    ],
    "Apprentice": [
        {
            "supermarket": "Carrefour",
            "discount": "10%",
            "code": "BOTBOTTLE10",
            "description": "10% de réduction sur vos achats",
            "min_points": 500,
        },
        {
            "supermarket": "Leclerc",
            "discount": "8%",
            "code": "BOTBOTTLE8",
            "description": "8% de réduction sur vos achats",
            "min_points": 500,
        }
    ],
    "Master": [
        {
            "supermarket": "Carrefour",
            "discount": "15%",
            "code": "BOTBOTTLE15",
            "description": "15% de réduction sur vos achats",
            "min_points": 2000,
        },
        {
            "supermarket": "Leclerc",
            "discount": "12%",
            "code": "BOTBOTTLE12",
            "description": "12% de réduction sur vos achats",
            "min_points": 2000,
        },
        {
            "supermarket": "Intermarché",
            "discount": "10%",
            "code": "BOTBOTTLE10IM",
            "description": "10% de réduction sur vos achats",
            "min_points": 2000,
        }
    ]
}


def get_available_promos(session: Session, user_id: int) -> List[Dict]:
    """Get available promo codes for a user based on their title level.
    
    Args:
        session: Database session.
        user_id: User ID.
    
    Returns:
        List of promo code dictionaries available to the user.
    """
    stats = get_user_stats(session, user_id)
    if not stats:
        return []
    
    title = stats.get("current_title", "Novice")
    total_points = stats.get("total_points", 0)
    
    # Get promos for current title and all lower titles
    available_promos = []
    
    title_order = ["Novice", "Apprentice", "Master"]
    current_index = title_order.index(title) if title in title_order else 0
    
    # Include promos from current level and below
    for i in range(current_index + 1):
        level = title_order[i]
        if level in PROMO_CODES:
            for promo in PROMO_CODES[level]:
                # Only include if user has enough points
                if total_points >= promo.get("min_points", 0):
                    available_promos.append(promo)
    
    return available_promos


def format_promos_message(promos: List[Dict]) -> str:
    """Format promo codes into a user-friendly message.
    
    Args:
        promos: List of promo code dictionaries.
    
    Returns:
        Formatted message string.
    """
    if not promos:
        return "Aucun code promo disponible pour le moment. Continuez à collecter des points !"
    
    message = "🎁 Vos codes promo disponibles :\n\n"
    
    for promo in promos:
        message += f"🏪 {promo['supermarket']}\n"
        message += f"   {promo['description']}\n"
        message += f"   Code: {promo['code']}\n\n"
    
    return message


def get_promo_by_code(code: str) -> Optional[Dict]:
    """Get promo code details by code string.
    
    Args:
        code: Promo code string.
    
    Returns:
        Promo dictionary if found, None otherwise.
    """
    for level_promos in PROMO_CODES.values():
        for promo in level_promos:
            if promo["code"].upper() == code.upper():
                return promo
    return None
