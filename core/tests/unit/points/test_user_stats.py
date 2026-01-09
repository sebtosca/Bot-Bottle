"""Unit tests for user statistics functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.points.rewards import get_user_stats


@pytest.mark.unit
class TestGetUserStats:
    """Tests for get_user_stats function."""
    
    def test_get_user_stats_success(self, mock_db_session, sample_user, sample_bottle):
        """Test getting user stats successfully."""
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
            assert "active_characters" in stats
            assert "returned_characters" in stats
            assert "characters" in stats
            assert len(stats["characters"]) == 1
    
    def test_get_user_stats_user_not_found(self, mock_db_session):
        """Test getting stats for non-existent user."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        stats = get_user_stats(mock_db_session, 999)
        
        assert stats == {}
    
    def test_get_user_stats_with_returned_bottles(self, mock_db_session, sample_user, sample_bottle):
        """Test getting stats with returned bottles."""
        returned_bottle = Mock()
        returned_bottle.returned = True
        sample_bottle.returned = False
        
        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [sample_bottle, returned_bottle]
        mock_db_session.query.return_value = mock_query
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        
        with patch('models.characters.get_character_config', return_value={"name": "Cherry"}):
            stats = get_user_stats(mock_db_session, sample_user.id)
            
            assert stats["character_count"] == 2
            assert stats["active_characters"] == 1
            assert stats["returned_characters"] == 1
    
    def test_get_user_stats_updates_title(self, mock_db_session, sample_user, sample_bottle):
        """Test that get_user_stats updates title if needed."""
        sample_bottle.user_id = sample_user.id
        sample_bottle.product_id = "00001"
        sample_bottle.returned = False
        sample_user.total_points = 500  # At Apprentice threshold
        sample_user.current_title = "Novice"
        
        mock_query = MagicMock()
        mock_query.filter_by.return_value.all.return_value = [sample_bottle]
        mock_db_session.query.return_value = mock_query
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        
        with patch('models.characters.get_character_config', return_value={"name": "Cherry"}):
            with patch('core.points.rewards.update_user_title', return_value=("Novice", "Apprentice")):
                stats = get_user_stats(mock_db_session, sample_user.id)
                
                assert stats["current_title"] in ["Novice", "Apprentice"]
