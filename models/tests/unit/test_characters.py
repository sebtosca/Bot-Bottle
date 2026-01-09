"""Unit tests for character models."""

import pytest
from models.characters import (
    get_character_config,
    get_system_prompt_for_character,
    get_character_id,
    CHARACTERS
)


@pytest.mark.unit
class TestGetCharacterConfig:
    """Tests for get_character_config function."""
    
    def test_get_cherry_config(self):
        """Test getting Cherry character config."""
        config = get_character_config("00001")
        
        assert config["name"] == "Cherry"
        assert config["product_id"] == "00001"
        assert config["type"] == "maraschino_cherry"
        assert "system_prompt" in config
        assert config["character_id"] == "00001"
    
    def test_get_pompon_config(self):
        """Test getting Pompon character config."""
        config = get_character_config("00002")
        
        assert config["name"] == "Pompon"
        assert config["product_id"] == "00002"
        assert config["type"] == "pompon_normand"
        assert "system_prompt" in config
        assert config["character_id"] == "00002"
    
    def test_get_invalid_product_id_falls_back_to_cherry(self):
        """Test invalid product_id falls back to Cherry."""
        config = get_character_config("99999")
        
        # Should return Cherry config as fallback
        assert config["name"] == "Cherry"
        assert config["product_id"] == "00001"
    
    def test_get_empty_product_id_falls_back_to_cherry(self):
        """Test empty product_id falls back to Cherry."""
        config = get_character_config("")
        
        assert config["name"] == "Cherry"
        assert config["product_id"] == "00001"
    
    def test_get_none_product_id_falls_back_to_cherry(self):
        """Test None product_id falls back to Cherry."""
        config = get_character_config(None)
        
        assert config["name"] == "Cherry"
        assert config["product_id"] == "00001"
    
    def test_config_has_required_fields(self):
        """Test config has all required fields."""
        for product_id in ["00001", "00002"]:
            config = get_character_config(product_id)
            
            assert "name" in config
            assert "product_id" in config
            assert "type" in config
            assert "system_prompt" in config
            assert "sticker_dir" in config
            assert "feeding_sticker_dir" in config
            assert "gif_dir" in config
            assert "money_gif_dir" in config
            assert "character_id" in config
            assert "money_per_bottle" in config
            assert "co2_per_bottle" in config


@pytest.mark.unit
class TestGetSystemPromptForCharacter:
    """Tests for get_system_prompt_for_character function."""
    
    def test_get_cherry_system_prompt(self):
        """Test getting Cherry system prompt."""
        prompt = get_system_prompt_for_character("00001")
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "cerise" in prompt.lower() or "cherry" in prompt.lower()
    
    def test_get_pompon_system_prompt(self):
        """Test getting Pompon system prompt."""
        prompt = get_system_prompt_for_character("00002")
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "pompon" in prompt.lower() or "normand" in prompt.lower()
    
    def test_get_invalid_product_id_returns_cherry_prompt(self):
        """Test invalid product_id returns Cherry prompt."""
        prompt = get_system_prompt_for_character("99999")
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should be Cherry's prompt
        cherry_prompt = CHARACTERS["00001"]["system_prompt"]
        assert prompt == cherry_prompt
    
    def test_system_prompt_is_not_empty(self):
        """Test system prompts are not empty."""
        for product_id in ["00001", "00002"]:
            prompt = get_system_prompt_for_character(product_id)
            assert len(prompt.strip()) > 0


@pytest.mark.unit
class TestGetCharacterId:
    """Tests for get_character_id function."""
    
    def test_get_cherry_character_id(self):
        """Test getting Cherry character ID."""
        char_id = get_character_id("00001")
        
        assert char_id == "00001"
    
    def test_get_pompon_character_id(self):
        """Test getting Pompon character ID."""
        char_id = get_character_id("00002")
        
        assert char_id == "00002"
    
    def test_get_invalid_product_id_returns_cherry_id(self):
        """Test invalid product_id returns Cherry ID."""
        char_id = get_character_id("99999")
        
        assert char_id == "00001"
    
    def test_character_id_matches_product_id(self):
        """Test character_id matches product_id."""
        for product_id in ["00001", "00002"]:
            char_id = get_character_id(product_id)
            assert char_id == product_id


@pytest.mark.unit
class TestCharactersDict:
    """Tests for CHARACTERS dictionary structure."""
    
    def test_characters_dict_has_expected_keys(self):
        """Test CHARACTERS dict has expected product IDs."""
        assert "00001" in CHARACTERS
        assert "00002" in CHARACTERS
    
    def test_character_config_structure(self):
        """Test each character config has correct structure."""
        required_fields = [
            "name", "product_id", "type", "system_prompt",
            "sticker_dir", "feeding_sticker_dir", "gif_dir",
            "money_gif_dir", "character_id", "money_per_bottle", "co2_per_bottle"
        ]
        
        for product_id, config in CHARACTERS.items():
            for field in required_fields:
                assert field in config, f"Missing field '{field}' in character {product_id}"
    
    def test_character_money_values(self):
        """Test money and CO2 values are positive."""
        for product_id, config in CHARACTERS.items():
            assert config["money_per_bottle"] > 0
            assert config["co2_per_bottle"] > 0
    
    def test_character_directories_are_strings(self):
        """Test directory fields are strings."""
        dir_fields = ["sticker_dir", "feeding_sticker_dir", "gif_dir", "money_gif_dir"]
        
        for product_id, config in CHARACTERS.items():
            for field in dir_fields:
                assert isinstance(config[field], str)
                assert len(config[field]) > 0
