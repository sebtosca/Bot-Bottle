"""Unit tests for title management functions."""

import pytest
from unittest.mock import Mock, MagicMock
from core.points.rewards import (
    update_user_title,
    TITLE_THRESHOLDS,
)


@pytest.mark.unit
class TestUpdateUserTitle:
    """Tests for update_user_title function."""
    
    def test_update_title_novice(self, mock_db_session, sample_user):
        """Test user stays at Novice with low points."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.total_points = 100
        sample_user.current_title = "Novice"
        
        result = update_user_title(mock_db_session, sample_user.id)
        
        assert result is None  # No change
        assert sample_user.current_title == "Novice"
    
    def test_update_title_to_apprentice(self, mock_db_session, sample_user):
        """Test user upgrades to Apprentice."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.total_points = TITLE_THRESHOLDS["Apprentice"]
        sample_user.current_title = "Novice"
        
        result = update_user_title(mock_db_session, sample_user.id)
        
        assert result == ("Novice", "Apprentice")
        assert sample_user.current_title == "Apprentice"
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_update_title_to_master(self, mock_db_session, sample_user):
        """Test user upgrades to Master."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.total_points = TITLE_THRESHOLDS["Master"]
        sample_user.current_title = "Apprentice"
        
        result = update_user_title(mock_db_session, sample_user.id)
        
        assert result == ("Apprentice", "Master")
        assert sample_user.current_title == "Master"
    
    def test_update_title_from_novice_to_master(self, mock_db_session, sample_user):
        """Test user jumps from Novice directly to Master."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.total_points = TITLE_THRESHOLDS["Master"]
        sample_user.current_title = "Novice"
        
        result = update_user_title(mock_db_session, sample_user.id)
        
        assert result == ("Novice", "Master")
        assert sample_user.current_title == "Master"
    
    def test_update_title_no_change(self, mock_db_session, sample_user):
        """Test title doesn't change if already correct."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        sample_user.total_points = TITLE_THRESHOLDS["Apprentice"]
        sample_user.current_title = "Apprentice"
        
        result = update_user_title(mock_db_session, sample_user.id)
        
        assert result is None
        assert sample_user.current_title == "Apprentice"
    
    def test_update_title_user_not_found(self, mock_db_session):
        """Test updating title for non-existent user."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = update_user_title(mock_db_session, 999)
        
        assert result is None
    
    def test_update_title_boundary_values(self, mock_db_session, sample_user):
        """Test title updates at boundary point values."""
        # Just below Apprentice threshold
        sample_user.total_points = TITLE_THRESHOLDS["Apprentice"] - 1
        sample_user.current_title = "Novice"
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = sample_user
        
        result = update_user_title(mock_db_session, sample_user.id)
        assert result is None
        assert sample_user.current_title == "Novice"
        
        # Exactly at Apprentice threshold
        sample_user.total_points = TITLE_THRESHOLDS["Apprentice"]
        result = update_user_title(mock_db_session, sample_user.id)
        assert result == ("Novice", "Apprentice")
        
        # Just below Master threshold
        sample_user.total_points = TITLE_THRESHOLDS["Master"] - 1
        sample_user.current_title = "Apprentice"
        result = update_user_title(mock_db_session, sample_user.id)
        assert result is None
        assert sample_user.current_title == "Apprentice"
        
        # Exactly at Master threshold
        sample_user.total_points = TITLE_THRESHOLDS["Master"]
        result = update_user_title(mock_db_session, sample_user.id)
        assert result == ("Apprentice", "Master")
