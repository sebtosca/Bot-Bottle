"""Points and rewards system for Bot-Bottle.

Handles points calculation, title management, and user statistics.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.db import User, Bottle


# Points values for different activities
POINTS_CHARACTER_COLLECTED = 100  # Points per character collected
POINTS_FEEDING = 10  # Points per successful feed (3 correct emojis)
POINTS_DAILY_ENGAGEMENT = 5  # Points per day user interacts
POINTS_BOTTLE_RETURN = 500  # Points for verified bottle return

# Character milestone bonuses
MILESTONE_BONUSES = {
    1: 0,      # 1 character: 0 bonus
    2: 50,     # 2 characters: +50 bonus
    3: 100,    # 3 characters: +100 bonus
    4: 200,    # 4+ characters: +200 bonus
}

# Title thresholds
TITLE_THRESHOLDS = {
    "Novice": 0,
    "Apprentice": 500,
    "Master": 2000,
}


def award_points(
    session: Session,
    user_id: int,
    activity_type: str,
    amount: Optional[int] = None,
    bottle_id: Optional[int] = None
) -> int:
    """Award points to a user for an activity.
    
    Args:
        session: Database session.
        user_id: User ID.
        activity_type: Type of activity ("character_collected", "feeding", 
                     "daily_engagement", "bottle_return", "milestone").
        amount: Optional custom amount (if None, uses default for activity_type).
        bottle_id: Optional bottle ID for character-specific tracking.
    
    Returns:
        Points awarded.
    """
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return 0
    
    # Determine points amount
    if amount is not None:
        points = amount
    elif activity_type == "character_collected":
        points = POINTS_CHARACTER_COLLECTED
    elif activity_type == "feeding":
        points = POINTS_FEEDING
    elif activity_type == "daily_engagement":
        points = POINTS_DAILY_ENGAGEMENT
    elif activity_type == "bottle_return":
        points = POINTS_BOTTLE_RETURN
    elif activity_type == "milestone":
        # Calculate milestone bonus based on character count
        character_count = session.query(Bottle).filter_by(user_id=user_id).count()
        points = MILESTONE_BONUSES.get(character_count, MILESTONE_BONUSES[4])
    else:
        points = 0
    
    if points > 0:
        # Update user total points
        user.total_points += points
        session.add(user)
        
        # Update bottle points if bottle_id provided
        if bottle_id:
            bottle = session.query(Bottle).filter_by(id=bottle_id).first()
            if bottle:
                bottle.points_earned += points
                session.add(bottle)
        
        session.commit()
        
        # Check if title should be updated
        title_update = update_user_title(session, user_id)
        # Return points and title update info
        return points, title_update
    
    return points, None


def update_user_title(session: Session, user_id: int) -> Optional[tuple]:
    """Update user's title based on total points.
    
    Args:
        session: Database session.
        user_id: User ID.
    
    Returns:
        Tuple of (old_title, new_title) if changed, None otherwise.
    """
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return None
    
    # Determine title based on points
    new_title = None
    if user.total_points >= TITLE_THRESHOLDS["Master"]:
        new_title = "Master"
    elif user.total_points >= TITLE_THRESHOLDS["Apprentice"]:
        new_title = "Apprentice"
    else:
        new_title = "Novice"
    
    # Update if changed
    if user.current_title != new_title:
        old_title = user.current_title
        user.current_title = new_title
        session.add(user)
        session.commit()
        return (old_title, new_title)
    
    return None


def get_user_stats(session: Session, user_id: int) -> Dict:
    """Get comprehensive user statistics.
    
    Args:
        session: Database session.
        user_id: User ID.
    
    Returns:
        Dictionary with user stats: points, title, savings, characters.
    """
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return {}
    
    # Get all user's bottles
    bottles = session.query(Bottle).filter_by(user_id=user_id).all()
    character_count = len(bottles)
    active_characters = [b for b in bottles if not b.returned]
    returned_characters = [b for b in bottles if b.returned]
    
    # Calculate per-character stats
    character_stats = []
    for bottle in active_characters:
        from characters import get_character_config
        char_config = get_character_config(bottle.product_id)
        character_stats.append({
            "name": char_config["name"],
            "product_id": bottle.product_id,
            "points_earned": bottle.points_earned,
            "money_saved": bottle.money_saved,
            "co2_saved": bottle.co2_saved,
            "fullness": bottle.fullness_level,
        })
    
    # Ensure title is up to date
    update_user_title(session, user_id)
    session.refresh(user)
    
    return {
        "total_points": user.total_points,
        "current_title": user.current_title or "Novice",
        "total_money_saved": user.total_money_saved,
        "total_co2_saved": user.total_co2_saved,
        "character_count": character_count,
        "active_characters": len(active_characters),
        "returned_characters": len(returned_characters),
        "characters": character_stats,
    }


def check_daily_engagement(session: Session, user_id: int) -> bool:
    """Check if user should receive daily engagement points.
    
    Awards points if user hasn't received them today.
    
    Args:
        session: Database session.
        user_id: User ID.
    
    Returns:
        True if points were awarded, False otherwise.
    """
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        return False
    
    # Check if user has interacted today (via last_seen_at)
    today = datetime.utcnow().date()
    last_seen_date = user.last_seen_at.date() if user.last_seen_at else None
    
    # Award points if this is a new day
    if last_seen_date != today:
        points, title_update = award_points(session, user_id, "daily_engagement")
        return True
    
    return False


def calculate_milestone_bonus(session: Session, user_id: int) -> int:
    """Calculate and award milestone bonus if user reached a new character count.
    
    This should be called AFTER a new character is added to check if a milestone was reached.
    
    Args:
        session: Database session.
        user_id: User ID.
    
    Returns:
        Bonus points awarded (0 if no new milestone).
    """
    character_count = session.query(Bottle).filter_by(user_id=user_id).count()
    
    # Check if this count qualifies for a milestone bonus
    # Only award if we've reached a milestone threshold
    if character_count in MILESTONE_BONUSES:
        bonus = MILESTONE_BONUSES[character_count]
        if bonus > 0:
            # Check if user already received this milestone bonus
            # (by checking if they have enough points from milestones)
            # For simplicity, we'll award it - in production you might want to track milestone awards
            award_points(session, user_id, "milestone", amount=bonus)
            return bonus
    
    return 0
