"""Unit tests for game flow functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from core.game.feeding_game import (
    start_game,
    process_emoji_feed,
    calculate_and_record_savings,
)


@pytest.mark.unit
class TestStartGame:
    """Tests for start_game function."""
    
    def test_start_game_with_name(self, mock_db_session, sample_bottle):
        """Test starting game with name in message."""
        sample_bottle.name = None
        sample_bottle.fullness_level = 0.0
        
        with patch('core.game.feeding_game.datetime') as mock_dt:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt.utcnow.return_value = fixed_time
            
            bottle, message = start_game(
                mock_db_session,
                sample_bottle,
                "Alice"
            )
            
            assert bottle.name == "Alice"
            assert bottle.fullness_level == 100.0
            assert bottle.game_started is True
            assert message == ""
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()
    
    def test_start_game_without_name(self, mock_db_session, sample_bottle):
        """Test starting game without name (prompts for name)."""
        sample_bottle.name = None
        
        with patch('core.game.feeding_game.datetime') as mock_dt:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt.utcnow.return_value = fixed_time
            
            bottle, message = start_game(
                mock_db_session,
                sample_bottle,
                "What is your name?"
            )
            
            assert bottle.name is None or bottle.name != "What is your name?"
            assert message != ""
            assert "name" in message.lower()
    
    def test_start_game_name_too_long(self, mock_db_session, sample_bottle):
        """Test starting game with name that's too long."""
        sample_bottle.name = None
        long_name = "A" * 51
        
        bottle, message = start_game(
            mock_db_session,
            sample_bottle,
            long_name
        )
        
        assert bottle.name != long_name
        assert message != ""
    
    def test_start_game_initializes_fullness(self, mock_db_session, sample_bottle):
        """Test that game start initializes fullness to 100%."""
        sample_bottle.fullness_level = 0.0
        sample_bottle.current_feed_count = 5
        
        with patch('core.game.feeding_game.datetime') as mock_dt:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt.utcnow.return_value = fixed_time
            
            bottle, message = start_game(
                mock_db_session,
                sample_bottle,
                "Test"
            )
            
            assert bottle.fullness_level == 100.0
            assert bottle.current_feed_count == 0


@pytest.mark.unit
class TestProcessEmojiFeed:
    """Tests for process_emoji_feed function."""
    
    def test_process_emoji_feed_correct_emoji(self, mock_db_session, sample_bottle):
        """Test processing feed with correct emoji."""
        sample_bottle.accessory_color = "GREEN"
        sample_bottle.current_feed_count = 0
        
        with patch('core.game.feeding_game.validate_emoji_for_color', return_value=True):
            with patch('core.game.feeding_game.assign_accessory_color', return_value="YELLOW"):
                result = process_emoji_feed(
                    mock_db_session,
                    sample_bottle,
                    ["🍎"]  # GREEN emoji
                )
                
                assert result["success"] is True
                assert result["correct_count"] > 0
    
    def test_process_emoji_feed_incorrect_emoji(self, mock_db_session, sample_bottle):
        """Test processing feed with incorrect emoji."""
        sample_bottle.accessory_color = "GREEN"
        sample_bottle.current_feed_count = 0
        
        with patch('core.game.feeding_game.validate_emoji_for_color', return_value=False):
            result = process_emoji_feed(
                mock_db_session,
                sample_bottle,
                ["🍌"]  # YELLOW emoji (wrong color)
            )
            
            assert result["success"] is False
            assert result["correct_count"] == 0
    
    def test_process_emoji_feed_assigns_color_first_time(self, mock_db_session, sample_bottle):
        """Test that color is assigned on first feed."""
        sample_bottle.accessory_color = None
        
        with patch('core.game.feeding_game.assign_accessory_color', return_value="GREEN") as mock_assign:
            with patch('core.game.feeding_game.validate_emoji_for_color', return_value=True):
                process_emoji_feed(
                    mock_db_session,
                    sample_bottle,
                    ["🍎"]
                )
                
                mock_assign.assert_called()
                assert sample_bottle.accessory_color == "GREEN"
    
    def test_process_emoji_feed_multiple_emojis(self, mock_db_session, sample_bottle):
        """Test processing feed with multiple emojis."""
        sample_bottle.accessory_color = "GREEN"
        sample_bottle.current_feed_count = 0
        
        with patch('core.game.feeding_game.validate_emoji_for_color', side_effect=[True, True, False]):
            result = process_emoji_feed(
                mock_db_session,
                sample_bottle,
                ["🍎", "🍎", "🍌"]  # 2 correct, 1 incorrect
            )
            
            # Net feed count = 2 correct - 1 incorrect = 1
            assert result["correct_count"] == 1
            assert result["success"] is True
    
    def test_process_emoji_feed_completes_cycle(self, mock_db_session, sample_bottle):
        """Test that feed completes cycle after 3 correct feeds."""
        sample_bottle.accessory_color = "GREEN"
        sample_bottle.current_feed_count = 2  # Already at 2
        
        with patch('core.game.feeding_game.validate_emoji_for_color', return_value=True):
            result = process_emoji_feed(
                mock_db_session,
                sample_bottle,
                ["🍎"]  # Third correct feed
            )
            
            assert result["feed_complete"] is True
            assert result["fullness_increased"] is True


@pytest.mark.unit
class TestCalculateAndRecordSavings:
    """Tests for calculate_and_record_savings function."""
    
    def test_calculate_savings_success(self, mock_db_session, sample_bottle, sample_user):
        """Test calculating savings successfully."""
        sample_bottle.user_id = sample_user.id
        sample_bottle.product_id = "00001"
        sample_bottle.money_saved = 0.0
        sample_bottle.co2_saved = 0.0
        
        mock_db_session.query.return_value.filter_by.return_value.first.side_effect = [
            sample_bottle,
            sample_user,
        ]
        
        with patch('models.characters.get_character_config', return_value={
            "money_per_bottle": 0.10,
            "co2_per_bottle": 0.5
        }):
            result = calculate_and_record_savings(mock_db_session, sample_bottle.id)
            
            assert "money_saved" in result
            assert "co2_saved" in result
            assert result["money_saved"] == 0.10
            assert result["co2_saved"] == 0.5
    
    def test_calculate_savings_bottle_not_found(self, mock_db_session):
        """Test calculating savings when bottle not found."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = calculate_and_record_savings(mock_db_session, 999)
        
        assert result == {"money_saved": 0.0, "co2_saved": 0.0}
