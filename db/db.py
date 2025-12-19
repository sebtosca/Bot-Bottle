from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Text, Boolean
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from config import DATABASE_URL

Base = declarative_base()


class User(Base):
    """User model representing a WhatsApp user."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp_number = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    bottles = relationship("Bottle", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")


class Bottle(Base):
    """Bottle model representing a user's bottle with state."""
    __tablename__ = "bottles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String, default="00001", nullable=False, index=True)  # Character product_id: "00001" (Cherry), "00002" (Pompon)
    type = Column(String, default="maraschino_cherry", nullable=False)  # e.g., "maraschino_cherry", "pompon_normand"
    name = Column(String, nullable=True)  # User-given name for the bottle (optional)
    mood = Column(String, default="neutral", nullable=False)  # e.g., "happy", "sad", "angry", "lonely", "thirsty", "neutral"
    personality_level = Column(Integer, default=0, nullable=False)  # 0-10 scale, evolves with engagement
    
    # Feeding game fields
    fullness_level = Column(Float, default=100.0, nullable=False)  # 0.0 to 100.0
    accessory_color = Column(String, nullable=True)  # "GREEN", "YELLOW", "BLACK", "BLUE"
    last_fullness_decrease = Column(DateTime, nullable=True)  # Track last 8hr decrease
    game_started = Column(Boolean, default=False, nullable=False)  # Has game started?
    current_feed_count = Column(Integer, default=0, nullable=False)  # Correct emojis in current session (0-3)
    incorrect_feed_count = Column(Integer, default=0, nullable=False)  # Incorrect emojis in current session
    last_feed_time = Column(DateTime, nullable=True)  # When last fed
    recovery_required = Column(Boolean, default=False, nullable=False)  # True if recovery needs 3 correct feeds
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bottles")
    interactions = relationship("Interaction", back_populates="bottle", cascade="all, delete-orphan")


class Interaction(Base):
    """Interaction model representing a message exchange."""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bottle_id = Column(Integer, ForeignKey("bottles.id"), nullable=False, index=True)
    message_type = Column(String, nullable=False)  # e.g., "text", "sticker", "image", "emoji", "gif"
    from_user = Column(String, nullable=False)  # "true" or "false" (user message vs bot response)
    content = Column(Text, nullable=False)  # Message content
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="interactions")
    bottle = relationship("Bottle", back_populates="interactions")


class Sticker(Base):
    """Sticker model representing mood-based stickers and GIFs.
    
    Notes:
        - For media_type == "sticker":
            * filename is the local image file name (e.g. "happy_cherry.webp")
            * url is typically NULL.
        - For media_type == "gif":
            * filename is the local MP4 (or GIF) filename served by Flask,
              e.g. "diva_reaction.mp4" in the GIF directory.
            * url is not used any more (legacy field for old URL-based GIFs).
    """
    __tablename__ = "stickers"

    id = Column(Integer, primary_key=True, index=True)
    # For stickers: local sticker image file name.
    # For GIFs: local MP4/GIF file name in the GIF directory.
    filename = Column(String, unique=True, nullable=True, index=True)
    character_id = Column(String, nullable=True, index=True)  # Character ID: "00001" (Cherry), "00002" (Pompon), or None (universal)
    mood_tags = Column(String, nullable=True)  # Comma-separated moods: "happy,excited,playful"
    description = Column(String, nullable=True)  # Optional description
    media_type = Column(String, default="sticker", nullable=False)  # "sticker" or "gif"
    # Legacy field (previously used for remote GIF URLs). New code should
    # prefer `filename` and local serving instead of URL-based GIFs.
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Database engine and session
engine = None
SessionLocal = None


def init_db() -> None:
    """Initialize database connection and create tables.
    
    Raises:
        RuntimeError: If DATABASE_URL is not set.
    """
    global engine, SessionLocal
    
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be set in environment variables or .env file")
    
    # Create engine
    engine = create_engine(DATABASE_URL, echo=False)
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database initialized successfully")


def is_db_initialized() -> bool:
    """Check if database is initialized and reachable.
    
    This function verifies both that the session factory exists AND that
    the database is actually reachable by performing a lightweight connection test.
    
    Returns:
        True if database is initialized and reachable, False otherwise.
    """
    if SessionLocal is None or engine is None:
        return False
    
    # Test actual connectivity with a lightweight connection test
    try:
        # Try to get a connection from the pool
        # This will fail if database is unreachable
        conn = engine.connect()
        conn.close()
        return True
    except OperationalError:
        # Connection failed - database is not reachable
        return False
    except Exception:
        # Other exceptions (shouldn't happen, but be safe)
        return False


def reset_db_initialization() -> None:
    """Reset database initialization state.
    
    This function should be called when connection errors occur to prevent
    repeated connection attempts. It resets the global engine and SessionLocal
    to None, allowing the app to gracefully continue without database functionality.
    """
    global engine, SessionLocal
    engine = None
    SessionLocal = None


def get_session() -> Session:
    """Get a database session.
    
    Returns:
        Database session.
    
    Raises:
        RuntimeError: If database is not initialized.
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return SessionLocal()


# Helper functions for common operations

def get_or_create_user(session: Session, whatsapp_number: str) -> User:
    """Get existing user or create a new one.
    
    Args:
        session: Database session.
        whatsapp_number: WhatsApp number (without whatsapp: prefix).
    
    Returns:
        User object.
    """
    user = session.query(User).filter_by(whatsapp_number=whatsapp_number).first()
    
    if user is None:
        now = datetime.utcnow()
        user = User(
            whatsapp_number=whatsapp_number,
            created_at=now,
            last_seen_at=now
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        # Update last_seen_at
        user.last_seen_at = datetime.utcnow()
        session.add(user)
        session.commit()
    
    return user


def get_or_create_bottle(session: Session, user_id: int, product_id: str = "00001", bottle_type: str = "maraschino_cherry") -> Bottle:
    """Get existing bottle for user and product_id or create a new one.
    
    Args:
        session: Database session.
        user_id: User ID.
        product_id: Character product_id (default: "00001" for Cherry).
        bottle_type: Type of bottle (default: "maraschino_cherry").
    
    Returns:
        Bottle object for the specified character.
    """
    # Query by both user_id and product_id to support multiple characters per user
    bottle = session.query(Bottle).filter_by(user_id=user_id, product_id=product_id).first()
    
    if bottle is None:
        now = datetime.utcnow()
        bottle = Bottle(
            user_id=user_id,
            product_id=product_id,
            type=bottle_type,
            mood="neutral",
            personality_level=0,
            created_at=now,
            updated_at=now
        )
        session.add(bottle)
        session.commit()
        session.refresh(bottle)
    
    return bottle


def get_active_bottle(session: Session, user_id: int, product_id: Optional[str] = None) -> Optional[Bottle]:
    """Get the active bottle for a user.
    
    If product_id is provided (from message context), use that character.
    Otherwise, determine active character from the most recent user interaction.
    
    Args:
        session: Database session.
        user_id: User ID.
        product_id: Optional product_id from message context.
    
    Returns:
        Bottle object for the active character, or None if no interactions exist.
    """
    # If product_id provided, use it directly
    if product_id:
        return get_or_create_bottle(session, user_id, product_id=product_id)
    
    # Otherwise, find the most recently interacted bottle
    last_interaction = (
        session.query(Interaction)
        .filter_by(user_id=user_id, from_user="true")
        .order_by(Interaction.created_at.desc())
        .first()
    )
    
    if last_interaction:
        active_bottle = session.query(Bottle).filter_by(id=last_interaction.bottle_id).first()
        if active_bottle:
            return active_bottle
    
    # Fallback: get or create default character (Cherry)
    return get_or_create_bottle(session, user_id, product_id="00001")


def create_interaction(
    session: Session,
    user_id: int,
    bottle_id: int,
    message_type: str,
    from_user: bool,
    content: str
) -> Interaction:
    """Create a new interaction record.
    
    Args:
        session: Database session.
        user_id: User ID.
        bottle_id: Bottle ID.
        message_type: Type of message ("text", "sticker", "image", etc.).
        from_user: True if from user, False if from bot.
        content: Message content.
    
    Returns:
        Interaction object.
    """
    interaction = Interaction(
        user_id=user_id,
        bottle_id=bottle_id,
        message_type=message_type,
        from_user="true" if from_user else "false",
        content=content,
        created_at=datetime.utcnow()
    )
    session.add(interaction)
    session.commit()
    session.refresh(interaction)
    return interaction


def get_recent_interactions(session: Session, bottle_id: int, limit: int = 10) -> list[Interaction]:
    """Get recent interactions for a bottle.
    
    Args:
        session: Database session.
        bottle_id: Bottle ID.
        limit: Maximum number of interactions to return.
    
    Returns:
        List of Interaction objects, ordered by created_at (oldest first).
    """
    return (
        session.query(Interaction)
        .filter_by(bottle_id=bottle_id)
        .order_by(Interaction.created_at.asc())
        .limit(limit)
        .all()
    )

