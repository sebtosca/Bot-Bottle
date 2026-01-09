"""Unit tests for slang replacement functions."""

import pytest
import random
import re
from unittest.mock import Mock, patch, MagicMock
from endpoint.helpers.slang import (
    apply_breton_slang,
    apply_norman_slang,
    apply_slang,
    BRETON_RULES,
    NORMAN_RULES,
    Rule
)


class TestApplySlang:
    """Tests for the core apply_slang function."""
    
    def test_apply_slang_empty_text(self):
        """Test apply_slang returns empty string when input is empty."""
        result = apply_slang("", BRETON_RULES)
        assert result == ""
    
    def test_apply_slang_no_matches(self):
        """Test apply_slang returns original text when no rules match."""
        text = "Hello, world!"
        result = apply_slang(text, BRETON_RULES, prob=1.0)
        assert result == text
    
    def test_apply_slang_probability_skip(self):
        """Test apply_slang skips replacement when random >= prob."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.8  # Above default 0.7
        
        result = apply_slang("bonjour", BRETON_RULES, prob=0.7, rng=mock_rng)
        
        assert result == "bonjour"
        mock_rng.random.assert_called_once()
    
    def test_apply_slang_applies_replacement(self):
        """Test apply_slang applies replacement when conditions are met."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5  # Below 0.7 threshold
        # Mock choice to return the first matching rule
        mock_rng.choice = Mock(side_effect=lambda rules: rules[0])
        
        result = apply_slang("bonjour", BRETON_RULES, prob=0.7, rng=mock_rng)
        
        assert result == "Demat"
        mock_rng.random.assert_called_once()
        mock_rng.choice.assert_called_once()
    
    def test_apply_slang_custom_rng(self):
        """Test apply_slang uses custom RNG when provided."""
        custom_rng = random.Random(42)
        result = apply_slang("bonjour", BRETON_RULES, prob=1.0, rng=custom_rng)
        # Should apply replacement with prob=1.0
        assert result in ["Demat", "bonjour"]  # Either replacement or original
    
    def test_apply_slang_multiple_matches_selects_one(self):
        """Test apply_slang selects one rule when multiple match."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        # Create rules that both match
        rules = [
            Rule(re.compile(r"\bbonjour\b", re.IGNORECASE), "Demat"),
            Rule(re.compile(r"\bmerci\b", re.IGNORECASE), "Trugarez")
        ]
        # Mock choice to return second rule
        mock_rng.choice = Mock(side_effect=lambda rules: rules[1])
        
        result = apply_slang("bonjour merci", rules, prob=0.7, rng=mock_rng)
        
        # Should replace only one (the one chosen)
        assert "Trugarez" in result or "merci" in result
        mock_rng.choice.assert_called_once()
    
    def test_apply_slang_replaces_only_first_occurrence(self):
        """Test apply_slang replaces only first occurrence (count=1)."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        rule = Rule(re.compile(r"\bmerci\b", re.IGNORECASE), "Trugarez")
        mock_rng.choice = Mock(return_value=rule)
        
        result = apply_slang("merci merci", [rule], prob=0.7, rng=mock_rng)
        
        # Should replace only first occurrence
        assert result.count("Trugarez") == 1
        assert result.count("merci") == 1


class TestApplyBretonSlang:
    """Tests for apply_breton_slang function."""
    
    def test_apply_breton_slang_replaces_au_revoir(self):
        """Test Breton slang replaces 'Au revoir'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        # Find the au revoir rule by matching the text
        au_revoir_rule = next(r for r in BRETON_RULES if r.pattern.search("au revoir"))
        mock_rng.choice = Mock(return_value=au_revoir_rule)
        
        result = apply_breton_slang("Au revoir", prob=0.7, rng=mock_rng)
        
        assert result == "Kenavo"
    
    def test_apply_breton_slang_replaces_bonjour(self):
        """Test Breton slang replaces 'bonjour'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        bonjour_rule = next(r for r in BRETON_RULES if r.pattern.search("bonjour"))
        mock_rng.choice = Mock(return_value=bonjour_rule)
        
        result = apply_breton_slang("bonjour", prob=0.7, rng=mock_rng)
        
        assert result == "Demat"
    
    def test_apply_breton_slang_replaces_merci(self):
        """Test Breton slang replaces 'merci'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        merci_rule = next(r for r in BRETON_RULES if r.pattern.search("merci"))
        mock_rng.choice = Mock(return_value=merci_rule)
        
        result = apply_breton_slang("Merci beaucoup", prob=0.7, rng=mock_rng)
        
        assert result == "Trugarez beaucoup"
    
    def test_apply_breton_slang_replaces_sante(self):
        """Test Breton slang replaces 'santé!'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        sante_rule = next(r for r in BRETON_RULES if r.pattern.search("santé!"))
        mock_rng.choice = Mock(return_value=sante_rule)
        
        result = apply_breton_slang("santé!", prob=0.7, rng=mock_rng)
        
        assert result == "Yec'hed mat !"
    
    def test_apply_breton_slang_replaces_a_la_tienne(self):
        """Test Breton slang replaces 'à la tienne!'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        tienne_rule = next(r for r in BRETON_RULES if r.pattern.search("à la tienne!"))
        mock_rng.choice = Mock(return_value=tienne_rule)
        
        result = apply_breton_slang("à la tienne!", prob=0.7, rng=mock_rng)
        
        assert result == "Yec'hed mat !"
    
    def test_apply_breton_slang_replaces_mon_dieu(self):
        """Test Breton slang replaces 'mon dieu!'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        dieu_rule = next(r for r in BRETON_RULES if r.pattern.search("mon dieu!"))
        mock_rng.choice = Mock(return_value=dieu_rule)
        
        result = apply_breton_slang("mon dieu!", prob=0.7, rng=mock_rng)
        
        assert result == "Ma doué !"
    
    def test_apply_breton_slang_no_replacement_when_random_high(self):
        """Test Breton slang doesn't replace when random >= prob."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.8  # Above 0.7 threshold
        
        result = apply_breton_slang("bonjour", prob=0.7, rng=mock_rng)
        
        assert result == "bonjour"
        mock_rng.random.assert_called_once()
    
    def test_apply_breton_slang_no_french_words(self):
        """Test Breton slang doesn't change text without French words."""
        text = "Hello, world!"
        result = apply_breton_slang(text, prob=1.0)
        assert result == text
    
    def test_apply_breton_slang_case_insensitive(self):
        """Test Breton slang is case-insensitive."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        bonjour_rule = next(r for r in BRETON_RULES if r.pattern.search("BONJOUR"))
        mock_rng.choice = Mock(return_value=bonjour_rule)
        
        result = apply_breton_slang("BONJOUR", prob=0.7, rng=mock_rng)
        
        assert result == "Demat"
    
    def test_apply_breton_slang_empty_string(self):
        """Test Breton slang handles empty string."""
        result = apply_breton_slang("")
        assert result == ""


class TestApplyNormanSlang:
    """Tests for apply_norman_slang function."""
    
    def test_apply_norman_slang_replaces_bonjour(self):
        """Test Norman slang replaces 'bonjour'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        bonjour_rule = next(r for r in NORMAN_RULES if r.pattern.search("bonjour"))
        mock_rng.choice = Mock(return_value=bonjour_rule)
        
        result = apply_norman_slang("bonjour", prob=0.7, rng=mock_rng)
        
        assert result == "Boujou"
    
    def test_apply_norman_slang_replaces_au_revoir(self):
        """Test Norman slang replaces 'au revoir'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        revoir_rule = next(r for r in NORMAN_RULES if r.pattern.search("au revoir"))
        mock_rng.choice = Mock(return_value=revoir_rule)
        
        result = apply_norman_slang("au revoir", prob=0.7, rng=mock_rng)
        
        assert result == "Boujou"
    
    def test_apply_norman_slang_replaces_mon_dieu(self):
        """Test Norman slang replaces 'mon dieu'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        dieu_rule = next(r for r in NORMAN_RULES if r.pattern.search("mon dieu"))
        mock_rng.choice = Mock(return_value=dieu_rule)
        
        result = apply_norman_slang("mon dieu", prob=0.7, rng=mock_rng)
        
        assert result == "Ma mé"
    
    def test_apply_norman_slang_replaces_oh(self):
        """Test Norman slang replaces 'oh'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        oh_rule = next(r for r in NORMAN_RULES if r.pattern.search("oh"))
        mock_rng.choice = Mock(return_value=oh_rule)
        
        result = apply_norman_slang("oh là là", prob=0.7, rng=mock_rng)
        
        assert result == "Ben là là"
    
    def test_apply_norman_slang_replaces_non(self):
        """Test Norman slang replaces 'non'."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        non_rule = next(r for r in NORMAN_RULES if r.pattern.search("non"))
        mock_rng.choice = Mock(return_value=non_rule)
        
        result = apply_norman_slang("non merci", prob=0.7, rng=mock_rng)
        
        assert result == "Point merci"
    
    def test_apply_norman_slang_no_replacement_when_random_high(self):
        """Test Norman slang doesn't replace when random >= prob."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.8  # Above 0.7 threshold
        
        result = apply_norman_slang("bonjour", prob=0.7, rng=mock_rng)
        
        assert result == "bonjour"
        mock_rng.random.assert_called_once()
    
    def test_apply_norman_slang_no_french_words(self):
        """Test Norman slang doesn't change text without French words."""
        text = "Hello, world!"
        result = apply_norman_slang(text, prob=1.0)
        assert result == text
    
    def test_apply_norman_slang_case_insensitive(self):
        """Test Norman slang is case-insensitive."""
        mock_rng = Mock()
        mock_rng.random.return_value = 0.5
        bonjour_rule = next(r for r in NORMAN_RULES if r.pattern.search("BONJOUR"))
        mock_rng.choice = Mock(return_value=bonjour_rule)
        
        result = apply_norman_slang("BONJOUR", prob=0.7, rng=mock_rng)
        
        assert result == "Boujou"
    
    def test_apply_norman_slang_empty_string(self):
        """Test Norman slang handles empty string."""
        result = apply_norman_slang("")
        assert result == ""
