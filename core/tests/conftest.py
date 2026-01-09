"""Shared pytest fixtures for core module tests."""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.db import User, Bottle, Interaction, Sticker


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.fixture
def sample_user():
    """Sample User object for testing."""
    user = Mock(spec=User)
    user.id = 1
    user.phone_number = "+33684950535"
    user.total_points = 100
    user.current_title = "Novice"
    user.total_money_saved = 0.0
    user.total_co2_saved = 0.0
    user.last_seen_at = datetime.utcnow()
    return user


@pytest.fixture
def sample_bottle():
    """Sample Bottle object for testing."""
    bottle = Mock(spec=Bottle)
    bottle.id = 1
    bottle.user_id = 1
    bottle.product_id = "00001"
    bottle.name = "TestBottle"
    bottle.fullness_level = 50.0
    bottle.current_feed_count = 0
    bottle.incorrect_feed_count = 0
    bottle.mood = "happy"
    bottle.personality_level = 1
    bottle.accessory_color = "GREEN"
    bottle.points_earned = 0
    bottle.money_saved = 0.0
    bottle.co2_saved = 0.0
    bottle.returned = False
    bottle.last_feed_time = None
    bottle.last_fullness_decrease = None
    bottle.created_at = datetime.utcnow()
    return bottle


@pytest.fixture
def sample_interaction():
    """Sample Interaction object for testing."""
    interaction = Mock(spec=Interaction)
    interaction.id = 1
    interaction.bottle_id = 1
    interaction.message_type = "text"
    interaction.created_at = datetime.utcnow()
    return interaction


@pytest.fixture
def sample_emoji_segmentation():
    """Sample emoji segmentation data."""
    return {
        "🍎": "GREEN",
        "🍌": "YELLOW",
        "📱": "BLACK",
        "📄": "BLUE",
        "🥤": "YELLOW",
        "🍷": "GREEN",
        "📦": "BLUE",
        "🔋": "BLACK",
    }


@pytest.fixture
def sample_sticker():
    """Sample Sticker object for testing."""
    sticker = Mock(spec=Sticker)
    sticker.id = 1
    sticker.filename = "happy_cherry.webp"
    sticker.character_id = "00001"
    sticker.mood_tags = "happy,excited"
    sticker.description = "Happy cherry sticker"
    sticker.media_type = "sticker"
    sticker.url = None
    return sticker


@pytest.fixture
def sample_gif():
    """Sample GIF Sticker object for testing."""
    gif = Mock(spec=Sticker)
    gif.id = 1
    gif.filename = "celebration.gif"
    gif.character_id = "00001"
    gif.mood_tags = "happy"
    gif.description = "Celebration GIF"
    gif.media_type = "gif"
    gif.url = None
    return gif


@pytest.fixture
def sample_fullness_levels():
    """Sample fullness level values for testing."""
    return {
        "empty": 0.0,
        "one_third": 33.33,
        "two_thirds": 66.66,
        "full": 100.0,
        "boundary_1": 33.32,  # Just below 1/3
        "boundary_2": 33.33,  # Exactly 1/3
        "boundary_3": 66.65,  # Just below 2/3
        "boundary_4": 66.66,  # Exactly 2/3
    }


@pytest.fixture
def sample_accessory_colors():
    """Sample accessory colors for testing."""
    return ["GREEN", "YELLOW", "BLACK", "BLUE"]


@pytest.fixture
def sample_moods():
    """Sample mood values for testing."""
    return ["happy", "sad", "excited", "neutral", "angry", "curious", "surprised"]


@pytest.fixture
def sample_message_types():
    """Sample message types for testing."""
    return ["text", "emoji", "sticker", "image", "video", "audio", "gif", "mixed"]


@pytest.fixture
def fixed_random_seed():
    """Fixture to set fixed random seed for deterministic tests."""
    import random
    seed = 42
    random.seed(seed)
    yield seed
    random.seed()  # Reset to system random


@pytest.fixture
def mock_datetime_now():
    """Fixture to mock datetime.utcnow() for time-dependent tests."""
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    with patch('core.game.feeding_game.datetime') as mock_dt:
        mock_dt.utcnow.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield fixed_time


@pytest.fixture
def mock_emoji_segmentation_file(sample_emoji_segmentation, tmp_path):
    """Fixture to create a mock emoji_segmentation_corrected.json file."""
    emoji_file = tmp_path / "emoji_segmentation_corrected.json"
    import json
    emoji_file.write_text(
        json.dumps({"segmentation": sample_emoji_segmentation}),
        encoding="utf-8"
    )
    return emoji_file


@pytest.fixture
def mock_path_exists():
    """Fixture to mock Path.exists() for file system operations."""
    with patch('pathlib.Path.exists') as mock_exists:
        mock_exists.return_value = True
        yield mock_exists


@pytest.fixture
def mock_open_file(sample_emoji_segmentation):
    """Fixture to mock open() for reading emoji segmentation file."""
    import json
    from unittest.mock import mock_open
    file_content = json.dumps({"segmentation": sample_emoji_segmentation})
    with patch('builtins.open', mock_open(read_data=file_content)):
        yield
