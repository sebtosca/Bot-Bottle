"""Unit tests for sticker selection functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.game.feeding_game import (
    get_fullness_sticker,
    get_emotional_sticker,
    get_stickers_for_state,
)


@pytest.mark.unit
class TestGetFullnessSticker:
    """Tests for get_fullness_sticker function."""
    
    def test_get_fullness_sticker_success(self, mock_db_session, sample_sticker):
        """Test getting fullness sticker successfully."""
        sample_sticker.mood_tags = "green,full"
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_sticker]
        mock_db_session.query.return_value = mock_query
        
        result = get_fullness_sticker(
            "GREEN",
            "full",
            "http://localhost:5000",
            character_id="00001"
        )
        
        assert result is not None
        assert "url" in result
        assert "filename" in result
        assert result["type"] == "fullness"
    
    def test_get_fullness_sticker_no_match(self, mock_db_session):
        """Test getting fullness sticker when no match found."""
        # Mock Path.exists() to return False (file doesn't exist)
        with patch('core.game.feeding_game.Path') as mock_path_class:
            # Mock the path chain: Path(__file__).parent.parent.parent / char_config["feeding_sticker_dir"] / filename
            mock_path_instance = MagicMock()
            mock_path_instance.parent.parent.parent = MagicMock()
            mock_path_instance.parent.parent.parent.__truediv__ = MagicMock(return_value=MagicMock())
            mock_path_class.return_value = mock_path_instance
            
            # Mock the final path check
            final_path = MagicMock()
            final_path.exists.return_value = False
            mock_path_instance.parent.parent.parent.__truediv__.return_value.__truediv__ = MagicMock(return_value=final_path)
            
            result = get_fullness_sticker(
                "GREEN",
                "full",
                "http://localhost:5000",
                character_id="00001"
            )
            
            assert result is None
    
    def test_get_fullness_sticker_all_states(self, mock_db_session, sample_sticker):
        """Test getting fullness sticker for all states."""
        states = ["full", "2/3", "1/3", "empty"]
        colors = ["GREEN", "YELLOW", "BLACK", "BLUE"]
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_sticker]
        mock_db_session.query.return_value = mock_query
        
        for state in states:
            for color in colors:
                result = get_fullness_sticker(
                    color,
                    state,
                    "http://localhost:5000",
                    character_id="00001"
                )
                # Should return sticker or None (depending on availability)
                assert result is None or "url" in result


@pytest.mark.unit
class TestGetEmotionalSticker:
    """Tests for get_emotional_sticker function."""
    
    def test_get_emotional_sticker_success(self, mock_db_session, sample_sticker):
        """Test getting emotional sticker successfully."""
        sample_sticker.mood_tags = "happy"
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_sticker]
        mock_db_session.query.return_value = mock_query
        
        result = get_emotional_sticker(
            "happy",
            "http://localhost:5000",
            character_id="00001"
        )
        
        assert result is not None
        assert "url" in result
        assert "filename" in result
        assert result["type"] == "emotional"
    
    def test_get_emotional_sticker_with_color(self, mock_db_session, sample_sticker):
        """Test getting emotional sticker with color requirement."""
        sample_sticker.mood_tags = "happy,green"
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_sticker]
        mock_db_session.query.return_value = mock_query
        
        result = get_emotional_sticker(
            "happy",
            "http://localhost:5000",
            character_id="00001",
            accessory_color="GREEN"
        )
        
        assert result is not None
    
    def test_get_emotional_sticker_no_match(self, mock_db_session):
        """Test getting emotional sticker when no match found."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        result = get_emotional_sticker(
            "nonexistent",
            "http://localhost:5000",
            character_id="00001"
        )
        
        assert result is None


@pytest.mark.unit
class TestGetStickersForState:
    """Tests for get_stickers_for_state function."""
    
    def test_get_stickers_for_state_success(self, sample_bottle):
        """Test getting both stickers for state."""
        sample_bottle.fullness_level = 100.0
        sample_bottle.mood = "happy"
        sample_bottle.accessory_color = "GREEN"
        sample_bottle.product_id = "00001"
        
        with patch('core.game.feeding_game.get_fullness_sticker', return_value={"url": "test", "filename": "test.webp"}):
            with patch('core.game.feeding_game.get_emotional_sticker', return_value={"url": "test2", "filename": "test2.webp"}):
                result = get_stickers_for_state(sample_bottle, "http://localhost:5000")
                
                assert "fullness" in result
                assert "emotional" in result
                assert result["fullness"] is not None
                assert result["emotional"] is not None
    
    def test_get_stickers_for_state_no_color(self, sample_bottle):
        """Test getting stickers when no accessory color set."""
        sample_bottle.fullness_level = 100.0
        sample_bottle.mood = "happy"
        sample_bottle.accessory_color = None
        sample_bottle.product_id = "00001"
        
        with patch('core.game.feeding_game.get_emotional_sticker', return_value={"url": "test", "filename": "test.webp"}):
            result = get_stickers_for_state(sample_bottle, "http://localhost:5000")
            
            assert "fullness" in result
            assert "emotional" in result
            assert result["fullness"] is None  # No color, no fullness sticker
            assert result["emotional"] is not None
    
    def test_get_stickers_for_state_all_fullness_levels(self, sample_bottle):
        """Test getting stickers for all fullness levels."""
        levels = [0.0, 33.33, 66.66, 100.0]
        sample_bottle.mood = "happy"
        sample_bottle.accessory_color = "GREEN"
        sample_bottle.product_id = "00001"
        
        for level in levels:
            sample_bottle.fullness_level = level
            with patch('core.game.feeding_game.get_fullness_sticker', return_value={"url": "test", "filename": "test.webp"}):
                with patch('core.game.feeding_game.get_emotional_sticker', return_value={"url": "test2", "filename": "test2.webp"}):
                    result = get_stickers_for_state(sample_bottle, "http://localhost:5000")
                    
                    assert "fullness" in result
                    assert "emotional" in result
