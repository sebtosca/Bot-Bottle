"""Integration tests for game module."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from core.game.feeding_game import (
    process_emoji_feed,
    update_fullness_after_feed,
    check_and_decrease_fullness,
)


@pytest.mark.integration
@pytest.mark.requires_db
class TestGameIntegration:
    """Integration tests for game flow."""
    
    def test_process_emoji_feed_integration(self, mock_db_session, sample_bottle, sample_user):
        """Test complete emoji feed processing flow."""
        # Setup
        sample_bottle.current_feed_count = 0
        sample_bottle.fullness_level = 0.0
        sample_bottle.accessory_color = "GREEN"
        
        # Mock database queries
        mock_db_session.query.return_value.filter_by.return_value.first.side_effect = [
            sample_bottle,  # Bottle query
            sample_user,   # User query for points
        ]
        
        result = process_emoji_feed(
            mock_db_session,
            sample_bottle,
            ["🍎"]  # GREEN emoji
        )
        
        assert "success" in result
        assert "correct_count" in result
        assert "fullness_increased" in result
    
    def test_fullness_decrease_after_time(self, sample_bottle):
        """Test fullness decreases after 8 hours."""
        # Set initial state
        sample_bottle.fullness_level = 100.0
        sample_bottle.last_fullness_decrease = datetime.utcnow() - timedelta(hours=8, minutes=1)
        
        # Check and decrease
        result = check_and_decrease_fullness(sample_bottle)
        
        assert result is True
        assert sample_bottle.fullness_level == 67.0  # 100 - 33
    
    def test_feed_cycle_completion(self, sample_bottle):
        """Test completing a full feed cycle (3 correct feeds)."""
        sample_bottle.current_feed_count = 0
        sample_bottle.fullness_level = 0.0
        
        # First feed
        increased1, complete1 = update_fullness_after_feed(sample_bottle, True)
        assert increased1 is False
        assert complete1 is False
        assert sample_bottle.current_feed_count == 1
        
        # Second feed
        increased2, complete2 = update_fullness_after_feed(sample_bottle, True)
        assert increased2 is False
        assert complete2 is False
        assert sample_bottle.current_feed_count == 2
        
        # Third feed (completes cycle)
        increased3, complete3 = update_fullness_after_feed(sample_bottle, True)
        assert increased3 is True
        assert complete3 is True
        assert sample_bottle.current_feed_count == 0  # Reset
        assert sample_bottle.fullness_level == pytest.approx(33.333, abs=0.001)
