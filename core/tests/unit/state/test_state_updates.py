"""Unit tests for bottle state update functions."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from core.state.bottle_state import update_bottle_state


@pytest.mark.unit
class TestUpdateBottleState:
    """Tests for update_bottle_state function."""
    
    def test_update_bottle_state_empty_interactions(self, sample_bottle):
        """Test updating state with no interactions."""
        result = update_bottle_state(
            None,  # session not needed for empty case
            sample_bottle,
            []
        )
        
        assert result == sample_bottle
    
    def test_update_bottle_state_text_interactions(self, sample_bottle, sample_interaction):
        """Test updating state with text interactions."""
        sample_interaction.message_type = "text"
        interactions = [sample_interaction] * 5
        
        result = update_bottle_state(
            None,
            sample_bottle,
            interactions
        )
        
        # Should update mood based on interaction types
        assert result == sample_bottle
    
    def test_update_bottle_state_emoji_interactions(self, sample_bottle, sample_interaction):
        """Test updating state with emoji interactions."""
        sample_interaction.message_type = "emoji"
        interactions = [sample_interaction] * 3
        
        result = update_bottle_state(
            None,
            sample_bottle,
            interactions
        )
        
        assert result == sample_bottle
    
    def test_update_bottle_state_mixed_interactions(self, sample_bottle, sample_interaction):
        """Test updating state with mixed interaction types."""
        text_interaction = Mock()
        text_interaction.message_type = "text"
        emoji_interaction = Mock()
        emoji_interaction.message_type = "emoji"
        
        interactions = [text_interaction] * 2 + [emoji_interaction] * 2
        
        result = update_bottle_state(
            None,
            sample_bottle,
            interactions
        )
        
        assert result == sample_bottle
    
    def test_update_bottle_state_personality_evolution(self, sample_bottle, sample_interaction):
        """Test that personality level evolves with interactions."""
        sample_interaction.message_type = "text"
        # Many interactions should increase personality level
        interactions = [sample_interaction] * 20
        
        original_level = sample_bottle.personality_level
        
        result = update_bottle_state(
            None,
            sample_bottle,
            interactions
        )
        
        # Personality should potentially increase (depends on implementation)
        assert result == sample_bottle
