"""Stats display orchestration module.

Handles sending stats images and interactive buttons to users.
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from points_system import get_user_stats, TITLE_THRESHOLDS
from stats_visualizer import generate_stats_image
from whatsapp_cloud_client import send_whatsapp_media, send_whatsapp_interactive_buttons
from db.db import User


def get_next_title_threshold(current_title: str) -> int:
    """Get the points threshold for the next title level."""
    if current_title == "Novice":
        return TITLE_THRESHOLDS["Apprentice"]
    elif current_title == "Apprentice":
        return TITLE_THRESHOLDS["Master"]
    else:
        return TITLE_THRESHOLDS["Master"] * 2


def format_stats_caption(stats: Dict, achievement_message: Optional[str] = None) -> str:
    """Create a concise caption for the stats image.
    
    Args:
        stats: Dictionary from get_user_stats().
        achievement_message: Optional achievement message to include.
    
    Returns:
        Formatted caption text.
    """
    current_title = stats.get('current_title', 'Novice')
    total_points = stats.get('total_points', 0)
    
    # Calculate progress
    next_threshold = get_next_title_threshold(current_title)
    current_threshold = TITLE_THRESHOLDS.get(current_title, 0)
    progress_points = total_points - current_threshold
    progress_max = next_threshold - current_threshold
    
    if progress_max > 0:
        progress_percent = int((progress_points / progress_max) * 100)
        if current_title == "Novice":
            next_title = "Apprentice"
        elif current_title == "Apprentice":
            next_title = "Master"
        else:
            next_title = None
    else:
        progress_percent = 100
        next_title = None
    
    caption = f"🏆 {current_title} • ⭐ {total_points:,} points"
    
    if next_title:
        caption += f"\n\n📊 Progression vers {next_title}: {progress_percent}%"
    else:
        caption += "\n\n✨ Niveau maximum atteint !"
    
    if achievement_message:
        caption = f"{achievement_message}\n\n{caption}"
    
    return caption


def send_stats_display(
    session: Session,
    user_id: int,
    from_number: str,
    base_url: str,
    auto_trigger: bool = False,
    achievement_message: Optional[str] = None
) -> bool:
    """Send stats image with interactive buttons to user.
    
    Args:
        session: Database session.
        user_id: User ID.
        from_number: WhatsApp number to send to.
        base_url: Base URL for serving images.
        auto_trigger: Whether this was triggered automatically (affects button options).
        achievement_message: Optional achievement message to include in caption.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Get user stats
        stats = get_user_stats(session, user_id)
        if not stats:
            return False
        
        # Format caption
        caption = format_stats_caption(stats, achievement_message)
        
        # Generate image URL (route will generate on-demand)
        image_url = f"{base_url.rstrip('/')}/stats-image/{user_id}"
        
        # Send interactive buttons
        buttons = [
            {
                "id": f"stats_details_{user_id}",
                "title": "Voir détails"
            },
            {
                "id": f"stats_promos_{user_id}",
                "title": "Mes promos"
            }
        ]
        
        if not auto_trigger:
            # Add dismiss button for manual requests
            buttons.append({
                "id": f"stats_dismiss_{user_id}",
                "title": "Fermer"
            })
        
        # Send image first
        try:
            send_whatsapp_media(from_number, image_url, caption)
        except Exception as e:
            print(f"⚠️  Error sending stats image: {e}")
            # Fallback: send text stats
            send_text_stats_fallback(session, user_id, from_number, stats, achievement_message)
            return False
        
        # Send interactive buttons
        try:
            send_whatsapp_interactive_buttons(
                from_number,
                "Que souhaitez-vous faire ?",
                buttons
            )
        except Exception as e:
            print(f"⚠️  Error sending interactive buttons: {e}")
        
        # Update last stats shown timestamp
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.last_notification_sent = datetime.utcnow()
            session.commit()
        
        return True
        
    except Exception as e:
        print(f"⚠️  Error in send_stats_display: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_text_stats_fallback(
    session: Session,
    user_id: int,
    from_number: str,
    stats: Dict,
    achievement_message: Optional[str] = None
) -> None:
    """Fallback: send stats as formatted text message.
    
    Args:
        session: Database session.
        user_id: User ID.
        from_number: WhatsApp number to send to.
        stats: User stats dictionary.
        achievement_message: Optional achievement message.
    """
    from whatsapp_cloud_client import send_whatsapp_text
    
    stats_msg = "📊 Vos statistiques :\n\n"
    
    if achievement_message:
        stats_msg += f"{achievement_message}\n\n"
    
    stats_msg += f"🏆 Titre : {stats['current_title']}\n"
    stats_msg += f"⭐ Points : {stats['total_points']:,}\n"
    stats_msg += f"💰 Argent économisé : €{stats['total_money_saved']:.2f}\n"
    stats_msg += f"🌱 CO2 économisé : {stats['total_co2_saved']:.2f} kg\n"
    stats_msg += f"👥 Personnages : {stats['active_characters']} actif(s), {stats['returned_characters']} retourné(s)\n"
    
    if stats.get('characters'):
        stats_msg += f"\n📦 Par personnage :\n"
        for char in stats['characters']:
            stats_msg += f"   • {char['name']} : {char['points_earned']} pts, €{char['money_saved']:.2f}, {char['co2_saved']:.2f} kg CO2\n"
    
    send_whatsapp_text(from_number, stats_msg)
