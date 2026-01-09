"""Unit tests for daily engagement tracking."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from core.points.rewards import (
    check_daily_engagement,
    POINTS_DAILY_ENGAGEMENT,
)


@pytest.mark.unit
class TestCheckDailyEngagement:
    """Tests for check_daily_engagement function."""
    
    def test_check_daily_engagement_new_day(self, mock_db_session, sample_user):
        """Test awarding points for new day engagement."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        # Set last_seen_at to yesterday
        sample_user.last_seen_at = datetime.utcnow() - timedelta(days=1)
        
        with patch('core.points.rewards.award_points', return_value=(POINTS_DAILY_ENGAGEMENT, None)) as mock_award:
            result = check_daily_engagement(mock_db_session, sample_user.id)
            
            assert result is True
            mock_award.assert_called_once_with(
                mock_db_session,
                sample_user.id,
                "daily_engagement"
            )
    
    def test_check_daily_engagement_same_day(self, mock_db_session, sample_user):
        """Test not awarding points if already engaged today."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        # Set last_seen_at to today
        sample_user.last_seen_at = datetime.utcnow()
        
        result = check_daily_engagement(mock_db_session, sample_user.id)
        
        assert result is False
    
    def test_check_daily_engagement_user_not_found(self, mock_db_session):
        """Test checking engagement for non-existent user."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = check_daily_engagement(mock_db_session, 999)
        
        assert result is False
    
    def test_check_daily_engagement_no_last_seen(self, mock_db_session, sample_user):
        """Test awarding points when user has no last_seen_at."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.last_seen_at = None
        
        with patch('core.points.rewards.award_points', return_value=(POINTS_DAILY_ENGAGEMENT, None)):
            result = check_daily_engagement(mock_db_session, sample_user.id)
            
            assert result is True  # Should award for first time
    
    def test_check_daily_engagement_multiple_days(self, mock_db_session, sample_user):
        """Test awarding points after multiple days."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.last_seen_at = datetime.utcnow() - timedelta(days=3)
        
        with patch('core.points.rewards.award_points', return_value=(POINTS_DAILY_ENGAGEMENT, None)):
            result = check_daily_engagement(mock_db_session, sample_user.id)
            
            assert result is True
    
    def test_check_daily_engagement_same_day_different_time(self, mock_db_session, sample_user):
        """Test not awarding if same day but different time."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        # Same day, but earlier in the day
        today = datetime.utcnow().date()
        sample_user.last_seen_at = datetime.combine(today, datetime.min.time())
        
        result = check_daily_engagement(mock_db_session, sample_user.id)
        
        assert result is False  # Same day, no award
