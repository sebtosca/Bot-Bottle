"""Integration tests for points system."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from core.points.rewards import (
    award_points,
    update_user_title,
    check_daily_engagement,
    get_user_stats,
)


@pytest.mark.integration
@pytest.mark.requires_db
class TestPointsIntegration:
    """Integration tests for points flow."""
    
    def test_points_and_title_progression(self, mock_db_session, sample_user):
        """Test points accumulation leading to title upgrade."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.total_points = 0
        sample_user.current_title = "Novice"
        
        # Award points to reach Apprentice threshold
        result = award_points(
            mock_db_session,
            sample_user.id,
            "character_collected",
            amount=500  # Exactly at Apprentice threshold
        )
        
        if isinstance(result, tuple):
            points, title_update = result
        else:
            points = result
            title_update = None
        
        assert points == 500
        assert sample_user.total_points == 500
        # Title should be updated
        assert title_update is not None or sample_user.current_title == "Apprentice"
    
    def test_daily_engagement_and_points(self, mock_db_session, sample_user):
        """Test daily engagement awards points."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.last_seen_at = datetime.utcnow() - timedelta(days=1)
        sample_user.total_points = 0
        
        with patch('core.points.rewards.award_points', return_value=(5, None)) as mock_award:
            result = check_daily_engagement(mock_db_session, sample_user.id)
            
            assert result is True
            mock_award.assert_called_once()
    
    def test_user_stats_integration(self, mock_db_session, sample_user, sample_bottle):
        """Test getting comprehensive user stats."""
        sample_bottle.user_id = sample_user.id
        sample_bottle.product_id = "00001"
        sample_bottle.returned = False
        
        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [sample_bottle]
        mock_db_session.query.return_value = mock_query
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        
        with patch('models.characters.get_character_config', return_value={"name": "Cherry"}):
            stats = get_user_stats(mock_db_session, sample_user.id)
            
            assert "total_points" in stats
            assert "current_title" in stats
            assert "character_count" in stats
            assert "characters" in stats
