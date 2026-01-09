"""Integration tests for character models."""

import pytest
from models.characters import (
    get_character_config,
    get_system_prompt_for_character,
    get_character_id,
    CHARACTERS
)


@pytest.mark.integration
class TestCharacterIntegration:
    """Integration tests for character models."""
    
    def test_character_config_consistency(self):
        """Test character configs are consistent across functions."""
        for product_id in ["00001", "00002"]:
            config = get_character_config(product_id)
            prompt = get_system_prompt_for_character(product_id)
            char_id = get_character_id(product_id)
            
            # Verify consistency
            assert config["system_prompt"] == prompt
            assert config["character_id"] == char_id
            assert config["product_id"] == product_id
    
    def test_all_characters_accessible(self):
        """Test all characters in CHARACTERS dict are accessible."""
        for product_id in CHARACTERS.keys():
            config = get_character_config(product_id)
            assert config is not None
            assert config["product_id"] == product_id
            
            prompt = get_system_prompt_for_character(product_id)
            assert prompt is not None
            assert len(prompt) > 0
            
            char_id = get_character_id(product_id)
            assert char_id == product_id
    
    def test_fallback_behavior(self):
        """Test fallback to Cherry for invalid product IDs."""
        invalid_ids = ["99999", "", "invalid", None]
        
        for invalid_id in invalid_ids:
            config = get_character_config(invalid_id)
            assert config["product_id"] == "00001"  # Cherry
            
            prompt = get_system_prompt_for_character(invalid_id)
            cherry_prompt = CHARACTERS["00001"]["system_prompt"]
            assert prompt == cherry_prompt
            
            char_id = get_character_id(invalid_id)
            assert char_id == "00001"
