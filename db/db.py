from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Text
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
    type = Column(String, default="maraschino_cherry", nullable=False)  # e.g., "maraschino_cherry", "tabasco", "water"
    mood = Column(String, default="neutral", nullable=False)  # e.g., "happy", "sad", "angry", "lonely", "thirsty", "neutral"
    personality_level = Column(Integer, default=0, nullable=False)  # 0-10 scale, evolves with engagement
    
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


def get_or_create_bottle(session: Session, user_id: int, bottle_type: str = "maraschino_cherry") -> Bottle:
    """Get existing bottle for user or create a new one.
    
    Args:
        session: Database session.
        user_id: User ID.
        bottle_type: Type of bottle (default: "maraschino_cherry").
    
    Returns:
        Bottle object.
    """
    bottle = session.query(Bottle).filter_by(user_id=user_id).first()
    
    if bottle is None:
        now = datetime.utcnow()
        bottle = Bottle(
            user_id=user_id,
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

