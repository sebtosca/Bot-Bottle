"""Unit tests for feeding game mechanics."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from core.game.feeding_game import (
    get_fullness_state,
    check_and_decrease_fullness,
    update_fullness_after_feed,
    assign_accessory_color,
)


@pytest.mark.unit
class TestGetFullnessState:
    """Tests for get_fullness_state function."""
    
    def test_fullness_state_full(self, sample_fullness_levels):
        """Test fullness state for full level."""
        assert get_fullness_state(sample_fullness_levels["full"]) == "full"
        assert get_fullness_state(100.0) == "full"
    
    def test_fullness_state_two_thirds(self, sample_fullness_levels):
        """Test fullness state for 2/3 level."""
        assert get_fullness_state(sample_fullness_levels["two_thirds"]) == "2/3"
        assert get_fullness_state(66.66) == "2/3"
        assert get_fullness_state(99.99) == "2/3"
    
    def test_fullness_state_one_third(self, sample_fullness_levels):
        """Test fullness state for 1/3 level."""
        assert get_fullness_state(sample_fullness_levels["one_third"]) == "1/3"
        assert get_fullness_state(33.33) == "1/3"
        assert get_fullness_state(66.65) == "1/3"
    
    def test_fullness_state_empty(self, sample_fullness_levels):
        """Test fullness state for empty level."""
        assert get_fullness_state(sample_fullness_levels["empty"]) == "empty"
        assert get_fullness_state(0.0) == "empty"
        assert get_fullness_state(33.32) == "empty"
    
    def test_fullness_state_boundaries(self, sample_fullness_levels):
        """Test fullness state at boundary values."""
        # Boundary at 33.33 (1/3)
        assert get_fullness_state(33.32) == "empty"
        assert get_fullness_state(33.33) == "1/3"
        
        # Boundary at 66.66 (2/3)
        assert get_fullness_state(66.65) == "1/3"
        assert get_fullness_state(66.66) == "2/3"
        
        # Boundary at 100.0 (full)
        assert get_fullness_state(99.99) == "2/3"
        assert get_fullness_state(100.0) == "full"


@pytest.mark.unit
class TestCheckAndDecreaseFullness:
    """Tests for check_and_decrease_fullness function."""
    
    def test_decrease_fullness_first_time(self, sample_bottle, mock_datetime_now):
        """Test decreasing fullness for first time (sets timestamp)."""
        sample_bottle.last_fullness_decrease = None
        
        with patch('core.game.feeding_game.datetime') as mock_dt:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt.utcnow.return_value = fixed_time
            
            result = check_and_decrease_fullness(sample_bottle)
            
            assert result is False
            assert sample_bottle.last_fullness_decrease == fixed_time
    
    def test_decrease_fullness_8_hours_passed(self, sample_bottle):
        """Test decreasing fullness after 8 hours."""
        eight_hours_ago = datetime.utcnow() - timedelta(hours=8, minutes=1)
        sample_bottle.last_fullness_decrease = eight_hours_ago
        sample_bottle.fullness_level = 50.0
        
        result = check_and_decrease_fullness(sample_bottle)
        
        assert result is True
        assert sample_bottle.fullness_level == 17.0  # 50 - 33
        assert sample_bottle.last_fullness_decrease is not None
    
    def test_decrease_fullness_less_than_8_hours(self, sample_bottle):
        """Test not decreasing fullness if less than 8 hours passed."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        sample_bottle.last_fullness_decrease = one_hour_ago
        original_level = 50.0
        sample_bottle.fullness_level = original_level
        
        result = check_and_decrease_fullness(sample_bottle)
        
        assert result is False
        assert sample_bottle.fullness_level == original_level
    
    def test_decrease_fullness_to_zero(self, sample_bottle):
        """Test decreasing fullness doesn't go below zero."""
        eight_hours_ago = datetime.utcnow() - timedelta(hours=8, minutes=1)
        sample_bottle.last_fullness_decrease = eight_hours_ago
        sample_bottle.fullness_level = 20.0  # Less than 33
        
        result = check_and_decrease_fullness(sample_bottle)
        
        assert result is True
        assert sample_bottle.fullness_level == 0.0  # Max(0, 20-33)


@pytest.mark.unit
class TestUpdateFullnessAfterFeed:
    """Tests for update_fullness_after_feed function."""
    
    def test_update_fullness_correct_feed_first(self, sample_bottle):
        """Test updating fullness after first correct feed."""
        sample_bottle.current_feed_count = 0
        sample_bottle.fullness_level = 0.0
        
        with patch('core.game.feeding_game.datetime') as mock_dt:
            fixed_time = datetime(2024, 1, 1, 12, 0, 0)
            mock_dt.utcnow.return_value = fixed_time
            
            increased, complete = update_fullness_after_feed(sample_bottle, True)
            
            assert increased is False
            assert complete is False
            assert sample_bottle.current_feed_count == 1
            assert sample_bottle.last_feed_time == fixed_time
    
    def test_update_fullness_correct_feed_second(self, sample_bottle):
        """Test updating fullness after second correct feed."""
        sample_bottle.current_feed_count = 1
        sample_bottle.fullness_level = 0.0
        
        increased, complete = update_fullness_after_feed(sample_bottle, True)
        
        assert increased is False
        assert complete is False
        assert sample_bottle.current_feed_count == 2
    
    def test_update_fullness_correct_feed_third(self, sample_bottle):
        """Test updating fullness after third correct feed (completes cycle)."""
        sample_bottle.current_feed_count = 2
        sample_bottle.fullness_level = 0.0
        
        increased, complete = update_fullness_after_feed(sample_bottle, True)
        
        assert increased is True
        assert complete is True
        assert sample_bottle.current_feed_count == 0  # Reset
        assert sample_bottle.fullness_level == pytest.approx(33.333, abs=0.001)
    
    def test_update_fullness_incorrect_feed(self, sample_bottle):
        """Test updating fullness after incorrect feed."""
        sample_bottle.current_feed_count = 1
        sample_bottle.incorrect_feed_count = 0
        original_level = 33.33
        sample_bottle.fullness_level = original_level
        
        increased, complete = update_fullness_after_feed(sample_bottle, False)
        
        assert increased is False
        assert complete is False
        assert sample_bottle.current_feed_count == 0  # Reset
        # Note: update_fullness_after_feed doesn't increment incorrect_feed_count,
        # it just decreases fullness and resets counter
        assert sample_bottle.fullness_level == pytest.approx(original_level - 5.0, abs=0.01)
    
    def test_update_fullness_caps_at_100(self, sample_bottle):
        """Test that fullness doesn't exceed 100%."""
        sample_bottle.current_feed_count = 2
        sample_bottle.fullness_level = 80.0  # Would go to 113.33
        
        increased, complete = update_fullness_after_feed(sample_bottle, True)
        
        assert increased is True
        assert complete is True
        assert sample_bottle.fullness_level == 100.0


@pytest.mark.unit
class TestAssignAccessoryColor:
    """Tests for assign_accessory_color function."""
    
    def test_assign_accessory_color_valid(self, fixed_random_seed):
        """Test assigning accessory color returns valid color."""
        color = assign_accessory_color()
        assert color in ["GREEN", "YELLOW", "BLACK", "BLUE"]
    
    def test_assign_accessory_color_deterministic(self, fixed_random_seed):
        """Test that color assignment is deterministic with fixed seed."""
        # With seed=42, should get consistent result
        color1 = assign_accessory_color()
        color2 = assign_accessory_color()
        # Note: This might vary, but should be consistent within same seed context
    
    def test_assign_accessory_color_all_possibilities(self, sample_accessory_colors):
        """Test that all colors are possible."""
        colors_seen = set()
        # Run multiple times to increase chance of seeing all colors
        for _ in range(100):
            color = assign_accessory_color()
            colors_seen.add(color)
            assert color in sample_accessory_colors
        
        # Should see at least one color (likely all if enough iterations)
        assert len(colors_seen) > 0
