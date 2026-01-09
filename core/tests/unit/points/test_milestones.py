"""Unit tests for milestone bonus functions."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.points.rewards import (
    calculate_milestone_bonus,
    MILESTONE_BONUSES,
)


@pytest.mark.unit
class TestCalculateMilestoneBonus:
    """Tests for calculate_milestone_bonus function."""
    
    def test_calculate_milestone_bonus_1_character(self, mock_db_session, sample_user):
        """Test milestone bonus for 1 character (no bonus)."""
        mock_bottle_query = MagicMock()
        mock_bottle_query.count.return_value = 1
        mock_db_session.query.return_value.filter_by.return_value = mock_bottle_query
        
        bonus = calculate_milestone_bonus(mock_db_session, sample_user.id)
        
        assert bonus == 0  # No bonus for 1 character
    
    def test_calculate_milestone_bonus_2_characters(self, mock_db_session, sample_user):
        """Test milestone bonus for 2 characters."""
        mock_bottle_query = MagicMock()
        mock_bottle_query.count.return_value = 2
        mock_db_session.query.return_value.filter_by.return_value = mock_bottle_query
        
        with patch('core.points.rewards.award_points', return_value=(50, None)) as mock_award:
            bonus = calculate_milestone_bonus(mock_db_session, sample_user.id)
            
            assert bonus == MILESTONE_BONUSES[2]
            mock_award.assert_called_once()
    
    def test_calculate_milestone_bonus_3_characters(self, mock_db_session, sample_user):
        """Test milestone bonus for 3 characters."""
        mock_bottle_query = MagicMock()
        mock_bottle_query.count.return_value = 3
        mock_db_session.query.return_value.filter_by.return_value = mock_bottle_query
        
        with patch('core.points.rewards.award_points', return_value=(100, None)) as mock_award:
            bonus = calculate_milestone_bonus(mock_db_session, sample_user.id)
            
            assert bonus == MILESTONE_BONUSES[3]
            mock_award.assert_called_once()
    
    def test_calculate_milestone_bonus_4_plus_characters(self, mock_db_session, sample_user):
        """Test milestone bonus for 4+ characters."""
        mock_bottle_query = MagicMock()
        mock_bottle_query.count.return_value = 4
        mock_db_session.query.return_value.filter_by.return_value = mock_bottle_query
        
        with patch('core.points.rewards.award_points', return_value=(200, None)) as mock_award:
            bonus = calculate_milestone_bonus(mock_db_session, sample_user.id)
            
            assert bonus == MILESTONE_BONUSES[4]
            mock_award.assert_called_once()
    
    def test_calculate_milestone_bonus_many_characters(self, mock_db_session, sample_user):
        """Test milestone bonus for many characters."""
        mock_bottle_query = MagicMock()
        mock_bottle_query.count.return_value = 10
        mock_db_session.query.return_value.filter_by.return_value = mock_bottle_query
        
        # calculate_milestone_bonus only awards if character_count is in MILESTONE_BONUSES dict
        # Since 10 is not in {1, 2, 3, 4}, it returns 0
        bonus = calculate_milestone_bonus(mock_db_session, sample_user.id)
        
        assert bonus == 0  # No bonus for count not in MILESTONE_BONUSES
    
    def test_calculate_milestone_bonus_zero_characters(self, mock_db_session, sample_user):
        """Test milestone bonus for zero characters."""
        mock_bottle_query = MagicMock()
        mock_bottle_query.count.return_value = 0
        mock_db_session.query.return_value.filter_by.return_value = mock_bottle_query
        
        bonus = calculate_milestone_bonus(mock_db_session, sample_user.id)
        
        assert bonus == 0  # No bonus for 0 characters
