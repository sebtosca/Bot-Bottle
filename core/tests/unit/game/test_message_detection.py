"""Unit tests for message detection functions."""

import pytest
from core.game.feeding_game import (
    detect_rules_request,
    detect_rename_request,
    extract_name_from_message,
)


@pytest.mark.unit
class TestDetectRulesRequest:
    """Tests for detect_rules_request function."""
    
    def test_detect_rules_request_positive(self):
        """Test detecting rules request with various keywords."""
        rules_messages = [
            "Quelles sont les règles?",
            "Règles du jeu",
            "Comment jouer?",
            "Comment ça marche?",
            "Les règles du jeu",
            "Règlement",
        ]
        
        for message in rules_messages:
            assert detect_rules_request(message) is True
    
    def test_detect_rules_request_negative(self):
        """Test not detecting rules request in normal messages."""
        normal_messages = [
            "Hello",
            "Comment allez-vous?",
            "Je veux jouer",
            # Note: "Règle générale" contains "règle" so it will match
            # This is expected behavior - any message with "règle" triggers detection
        ]
        
        for message in normal_messages:
            assert detect_rules_request(message) is False
    
    def test_detect_rules_request_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert detect_rules_request("RÈGLES") is True
        assert detect_rules_request("règles") is True
        assert detect_rules_request("Règles") is True
    
    def test_detect_rules_request_empty(self):
        """Test detecting rules request with empty message."""
        assert detect_rules_request("") is False
        assert detect_rules_request(None) is False
    
    def test_detect_rules_request_with_whitespace(self):
        """Test detecting rules request with whitespace."""
        assert detect_rules_request("  règles  ") is True
        assert detect_rules_request("\ncomment jouer\n") is True


@pytest.mark.unit
class TestDetectRenameRequest:
    """Tests for detect_rename_request function."""
    
    def test_detect_rename_request_positive(self):
        """Test detecting rename request with various keywords."""
        rename_messages = [
            "Renommer",
            "Changer nom",
            "Nouveau nom",
            "Appeler",
            "Nommer",
            "Changer de nom",
            "Renomme-moi",
            "Appelle-moi",
        ]
        
        for message in rename_messages:
            assert detect_rename_request(message) is True
    
    def test_detect_rename_request_negative(self):
        """Test not detecting rename request in normal messages."""
        normal_messages = [
            "Hello",
            "Comment allez-vous?",
            "Je veux un nom",
            "Nom de famille",
        ]
        
        for message in normal_messages:
            assert detect_rename_request(message) is False
    
    def test_detect_rename_request_case_insensitive(self):
        """Test that detection is case insensitive."""
        assert detect_rename_request("RENOMMER") is True
        assert detect_rename_request("renommer") is True
        assert detect_rename_request("Renommer") is True
    
    def test_detect_rename_request_empty(self):
        """Test detecting rename request with empty message."""
        assert detect_rename_request("") is False
        assert detect_rename_request(None) is False


@pytest.mark.unit
class TestExtractNameFromMessage:
    """Tests for extract_name_from_message function."""
    
    def test_extract_name_simple(self):
        """Test extracting simple name."""
        assert extract_name_from_message("Alice") == "Alice"
        assert extract_name_from_message("Bob") == "Bob"
    
    def test_extract_name_with_whitespace(self):
        """Test extracting name with whitespace."""
        assert extract_name_from_message("  Alice  ") == "Alice"
        assert extract_name_from_message("Bob Smith") == "Bob Smith"
    
    def test_extract_name_too_long(self):
        """Test not extracting name if too long."""
        long_name = "A" * 51
        assert extract_name_from_message(long_name) is None
    
    def test_extract_name_with_question(self):
        """Test not extracting name if contains question words."""
        question_messages = [
            "What is your name?",
            "Comment t'appelles-tu?",
            "Quel est ton nom?",
            "How are you?",
        ]
        
        for message in question_messages:
            assert extract_name_from_message(message) is None
    
    def test_extract_name_empty(self):
        """Test extracting name from empty message."""
        assert extract_name_from_message("") is None
        assert extract_name_from_message(None) is None
    
    def test_extract_name_valid_length(self):
        """Test extracting name with valid length."""
        assert extract_name_from_message("A" * 50) == "A" * 50
        assert extract_name_from_message("A" * 1) == "A"
    
    def test_extract_name_with_numbers(self):
        """Test extracting name with numbers."""
        assert extract_name_from_message("Alice123") == "Alice123"
        assert extract_name_from_message("Bob2") == "Bob2"
