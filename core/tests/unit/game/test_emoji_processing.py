"""Unit tests for emoji processing functions."""

import pytest
from unittest.mock import patch, MagicMock
from core.game.feeding_game import (
    load_emoji_segmentation,
    get_emoji_category,
    extract_emojis_from_message,
    validate_emoji_for_color,
)


@pytest.mark.unit
class TestLoadEmojiSegmentation:
    """Tests for load_emoji_segmentation function."""
    
    def test_load_emoji_segmentation_success(self, sample_emoji_segmentation, mock_open_file, mock_path_exists):
        """Test loading emoji segmentation from file."""
        with patch('core.game.feeding_game.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            result = load_emoji_segmentation()
            assert isinstance(result, dict)
    
    def test_load_emoji_segmentation_file_not_found(self, mock_path_exists):
        """Test loading when file doesn't exist."""
        # Reset global cache first
        import core.game.feeding_game as feeding_game
        feeding_game._emoji_segmentation = None
        
        with patch('core.game.feeding_game.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            result = load_emoji_segmentation()
            assert result == {}
    
    def test_load_emoji_segmentation_cached(self, sample_emoji_segmentation, mock_open_file, mock_path_exists):
        """Test that segmentation is cached after first load."""
        with patch('core.game.feeding_game.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            # Load twice
            result1 = load_emoji_segmentation()
            result2 = load_emoji_segmentation()
            # Should return same object (cached)
            assert result1 is result2
    
    def test_load_emoji_segmentation_invalid_json(self, tmp_path):
        """Test loading with invalid JSON file."""
        # Reset global cache first
        import core.game.feeding_game as feeding_game
        feeding_game._emoji_segmentation = None
        
        emoji_file = tmp_path / "emoji_segmentation_corrected.json"
        emoji_file.write_text("invalid json", encoding="utf-8")
        
        with patch('core.game.feeding_game.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__ = lambda self, other: emoji_file
            result = load_emoji_segmentation()
            # Should return empty dict on error
            assert result == {}


@pytest.mark.unit
class TestGetEmojiCategory:
    """Tests for get_emoji_category function."""
    
    def test_get_emoji_category_found(self, sample_emoji_segmentation):
        """Test getting category for known emoji."""
        with patch('core.game.feeding_game.load_emoji_segmentation', return_value=sample_emoji_segmentation):
            assert get_emoji_category("🍎") == "GREEN"
            assert get_emoji_category("🍌") == "YELLOW"
            assert get_emoji_category("📱") == "BLACK"
            assert get_emoji_category("📄") == "BLUE"
    
    def test_get_emoji_category_not_found(self, sample_emoji_segmentation):
        """Test getting category for unknown emoji (defaults to BLACK)."""
        with patch('core.game.feeding_game.load_emoji_segmentation', return_value=sample_emoji_segmentation):
            assert get_emoji_category("🤔") == "BLACK"
            assert get_emoji_category("") == "BLACK"
    
    def test_get_emoji_category_empty_segmentation(self):
        """Test getting category when segmentation is empty."""
        with patch('core.game.feeding_game.load_emoji_segmentation', return_value={}):
            assert get_emoji_category("🍎") == "BLACK"


@pytest.mark.unit
class TestExtractEmojisFromMessage:
    """Tests for extract_emojis_from_message function."""
    
    def test_extract_emojis_single(self):
        """Test extracting single emoji."""
        result = extract_emojis_from_message("Hello 🍎 world")
        assert "🍎" in result
        assert len(result) == 1
    
    def test_extract_emojis_multiple(self):
        """Test extracting multiple emojis."""
        result = extract_emojis_from_message("🍎🍌📱")
        assert "🍎" in result
        assert "🍌" in result
        assert "📱" in result
        assert len(result) == 3
    
    def test_extract_emojis_none(self):
        """Test extracting from message with no emojis."""
        result = extract_emojis_from_message("Hello world")
        assert result == []
    
    def test_extract_emojis_empty_message(self):
        """Test extracting from empty message."""
        result = extract_emojis_from_message("")
        assert result == []
    
    def test_extract_emojis_none_input(self):
        """Test extracting from None input."""
        result = extract_emojis_from_message(None)
        assert result == []
    
    def test_extract_emojis_mixed(self):
        """Test extracting from mixed text and emojis."""
        result = extract_emojis_from_message("Hello 🍎 and 🍌 goodbye")
        assert "🍎" in result
        assert "🍌" in result
        assert len(result) == 2


@pytest.mark.unit
class TestValidateEmojiForColor:
    """Tests for validate_emoji_for_color function."""
    
    def test_validate_emoji_correct_color(self, sample_emoji_segmentation):
        """Test validating emoji with correct color."""
        with patch('core.game.feeding_game.get_emoji_category', return_value="GREEN"):
            assert validate_emoji_for_color("🍎", "GREEN") is True
    
    def test_validate_emoji_incorrect_color(self, sample_emoji_segmentation):
        """Test validating emoji with incorrect color."""
        with patch('core.game.feeding_game.get_emoji_category', return_value="GREEN"):
            assert validate_emoji_for_color("🍎", "YELLOW") is False
    
    def test_validate_emoji_no_accessory_color(self):
        """Test validating with no accessory color."""
        assert validate_emoji_for_color("🍎", "") is False
        assert validate_emoji_for_color("🍎", None) is False
    
    def test_validate_emoji_all_colors(self, sample_emoji_segmentation):
        """Test validating emoji for all color types."""
        colors = ["GREEN", "YELLOW", "BLACK", "BLUE"]
        for color in colors:
            with patch('core.game.feeding_game.get_emoji_category', return_value=color):
                assert validate_emoji_for_color("🍎", color) is True
                # Test wrong color
                wrong_colors = [c for c in colors if c != color]
                for wrong_color in wrong_colors:
                    assert validate_emoji_for_color("🍎", wrong_color) is False
