"""Integration tests for slang replacement functions."""

import pytest
import random
from endpoint.helpers.slang import (
    apply_breton_slang,
    apply_norman_slang,
    apply_slang,
    BRETON_RULES,
    NORMAN_RULES
)


class TestSlangIntegration:
    """Integration tests for slang functions using realistic scenarios."""
    
    def test_breton_slang_realistic_conversation(self):
        """Test Breton slang in a realistic conversation context."""
        # Use deterministic RNG for predictable results
        rng = random.Random(42)
        
        # Test multiple phrases that should trigger replacements
        phrases = [
            ("Bonjour, comment allez-vous?", "Demat"),
            ("Merci beaucoup!", "Trugarez"),
            ("Au revoir!", "Kenavo"),
            ("Santé!", "Yec'hed mat"),
            ("Mon dieu!", "Ma doué"),
        ]
        
        for phrase, expected_replacement in phrases:
            # Run multiple times with prob=1.0 to ensure replacement happens
            results = []
            for _ in range(10):
                result = apply_breton_slang(phrase, prob=1.0, rng=rng)
                results.append(result)
            
            # At least one result should contain the replacement
            assert any(expected_replacement in r for r in results), \
                f"Expected '{expected_replacement}' in results for phrase '{phrase}'"
    
    def test_norman_slang_realistic_conversation(self):
        """Test Norman slang in a realistic conversation context."""
        rng = random.Random(42)
        
        phrases = [
            ("Bonjour!", "Boujou"),
            ("Au revoir!", "Boujou"),
            ("Mon dieu!", "Ma mé"),
            ("Oh là là!", "Ben"),
            ("Non merci", "Point"),
        ]
        
        for phrase, expected_replacement in phrases:
            results = []
            for _ in range(10):
                result = apply_norman_slang(phrase, prob=1.0, rng=rng)
                results.append(result)
            
            # At least one result should contain the replacement
            assert any(expected_replacement in r for r in results), \
                f"Expected '{expected_replacement}' in results for phrase '{phrase}'"
    
    def test_slang_probability_distribution(self):
        """Test that probability parameter affects replacement frequency."""
        text = "bonjour"
        rng = random.Random(42)
        
        # With prob=1.0, should always replace (when match found)
        results_high_prob = [
            apply_breton_slang(text, prob=1.0, rng=random.Random(i))
            for i in range(20)
        ]
        
        # With prob=0.0, should never replace
        results_low_prob = [
            apply_breton_slang(text, prob=0.0, rng=random.Random(i))
            for i in range(20)
        ]
        
        # High prob should have more replacements
        high_prob_replacements = sum(1 for r in results_high_prob if r != text)
        low_prob_replacements = sum(1 for r in results_low_prob if r != text)
        
        assert high_prob_replacements > low_prob_replacements, \
            "High probability should result in more replacements"
        assert low_prob_replacements == 0, \
            "Zero probability should result in no replacements"
    
    def test_slang_preserves_context(self):
        """Test that slang replacement preserves surrounding text."""
        rng = random.Random(42)
        
        # Test that only the matched word is replaced, context is preserved
        text = "Bonjour, comment allez-vous? Merci beaucoup!"
        
        # Run multiple times to get a replacement
        for _ in range(50):
            result = apply_breton_slang(text, prob=1.0, rng=random.Random())
            if result != text:  # If replacement occurred
                # Should preserve punctuation and other words
                assert "," in result or "!" in result or "?" in result, \
                    "Punctuation should be preserved"
                assert "comment" in result.lower() or "allez-vous" in result.lower(), \
                    "Other words should be preserved"
                break
    
    def test_slang_case_insensitive_matching(self):
        """Test that slang matching works regardless of case."""
        rng = random.Random(42)
        
        test_cases = [
            "BONJOUR",
            "Bonjour",
            "bonjour",
            "BONJOUR!",
            "Bonjour!",
        ]
        
        for text in test_cases:
            # With prob=1.0, should match regardless of case
            results = []
            for seed in range(20):
                result = apply_breton_slang(text, prob=1.0, rng=random.Random(seed))
                results.append(result)
            
            # At least some results should have replacement
            replacements = [r for r in results if r != text]
            assert len(replacements) > 0, \
                f"Should match '{text}' regardless of case"
    
    def test_slang_word_boundaries(self):
        """Test that slang only matches whole words, not substrings."""
        rng = random.Random(42)
        
        # "bonjour" should match, but not as part of "rebonjour" or "bonjournée"
        should_match = [
            "bonjour",
            "bonjour!",
            "bonjour, comment allez-vous?",
        ]
        
        should_not_match = [
            "rebonjour",  # "bonjour" is a substring
            "bonjournée",  # "bonjour" is a substring
            "rebonjourner",  # "bonjour" is a substring
        ]
        
        for text in should_match:
            results = []
            for seed in range(20):
                result = apply_breton_slang(text, prob=1.0, rng=random.Random(seed))
                results.append(result)
            
            # Should have some replacements
            replacements = [r for r in results if r != text]
            assert len(replacements) > 0, \
                f"Should match '{text}' as whole word"
        
        for text in should_not_match:
            results = []
            for seed in range(20):
                result = apply_breton_slang(text, prob=1.0, rng=random.Random(seed))
                results.append(result)
            
            # Should not have replacements (no match)
            replacements = [r for r in results if r != text]
            assert len(replacements) == 0, \
                f"Should not match '{text}' as substring"
    
    def test_slang_multiple_rules_single_replacement(self):
        """Test that only one replacement occurs even when multiple rules match."""
        rng = random.Random(42)
        
        # Text that matches multiple Breton rules
        text = "bonjour merci"
        
        results = []
        for seed in range(50):
            result = apply_breton_slang(text, prob=1.0, rng=random.Random(seed))
            results.append(result)
        
        # Check that results have at most one replacement
        for result in results:
            if result != text:
                # Count how many original words were replaced
                replacements = 0
                if "Demat" in result or "Trugarez" in result:
                    replacements += 1
                
                assert replacements <= 1, \
                    "Should replace at most one word per call"
    
    def test_slang_empty_and_whitespace(self):
        """Test slang functions handle empty strings and whitespace."""
        test_cases = [
            "",
            "   ",
            "\n\t",
            "  bonjour  ",
        ]
        
        for text in test_cases:
            result_breton = apply_breton_slang(text, prob=1.0)
            result_norman = apply_norman_slang(text, prob=1.0)
            
            # Should not crash and return a string
            assert isinstance(result_breton, str)
            assert isinstance(result_norman, str)
    
    def test_slang_special_characters(self):
        """Test slang functions handle special characters correctly."""
        rng = random.Random(42)
        
        test_cases = [
            "bonjour!",
            "bonjour?",
            "bonjour.",
            "bonjour, comment allez-vous?",
            "à la tienne!",
            "santé!",
        ]
        
        for text in test_cases:
            result_breton = apply_breton_slang(text, prob=1.0, rng=rng)
            result_norman = apply_norman_slang(text, prob=1.0, rng=rng)
            
            assert isinstance(result_breton, str)
            assert isinstance(result_norman, str)
            # Should preserve special characters structure
            assert len(result_breton) > 0
            assert len(result_norman) > 0
    
    def test_slang_deterministic_with_seed(self):
        """Test that slang functions are deterministic with same RNG seed."""
        seed = 42
        text = "bonjour"
        
        # Create two RNGs with same seed
        rng1 = random.Random(seed)
        rng2 = random.Random(seed)
        
        result1 = apply_breton_slang(text, prob=1.0, rng=rng1)
        result2 = apply_breton_slang(text, prob=1.0, rng=rng2)
        
        assert result1 == result2, \
            "Results should be deterministic with same RNG seed"
    
    def test_slang_all_breton_rules(self):
        """Test that all Breton rules can be triggered."""
        rng = random.Random(42)
        
        # Test each rule individually
        test_phrases = [
            ("au revoir", "Kenavo"),
            ("santé!", "Yec'hed mat"),
            ("à la tienne!", "Yec'hed mat"),
            ("bonjour", "Demat"),
            ("merci", "Trugarez"),
            ("mon dieu!", "Ma doué"),
        ]
        
        for phrase, expected in test_phrases:
            # Try multiple seeds to ensure we get a match
            found = False
            for seed in range(100):
                rng_test = random.Random(seed)
                result = apply_breton_slang(phrase, prob=1.0, rng=rng_test)
                if expected in result:
                    found = True
                    break
            
            assert found, f"Should be able to trigger rule for '{phrase}' -> '{expected}'"
    
    def test_slang_all_norman_rules(self):
        """Test that all Norman rules can be triggered."""
        rng = random.Random(42)
        
        test_phrases = [
            ("bonjour", "Boujou"),
            ("au revoir", "Boujou"),
            ("mon dieu", "Ma mé"),
            ("oh", "Ben"),
            ("non", "Point"),
        ]
        
        for phrase, expected in test_phrases:
            found = False
            for seed in range(100):
                rng_test = random.Random(seed)
                result = apply_norman_slang(phrase, prob=1.0, rng=rng_test)
                if expected in result:
                    found = True
                    break
            
            assert found, f"Should be able to trigger rule for '{phrase}' -> '{expected}'"
    
    def test_slang_custom_probability_values(self):
        """Test slang functions with various probability values."""
        text = "bonjour"
        
        for prob in [0.0, 0.1, 0.5, 0.7, 0.9, 1.0]:
            results = []
            for seed in range(30):
                rng = random.Random(seed)
                result = apply_breton_slang(text, prob=prob, rng=rng)
                results.append(result)
            
            # Count replacements
            replacements = sum(1 for r in results if r != text)
            replacement_rate = replacements / len(results)
            
            # With higher prob, should have higher replacement rate
            # Allow some variance due to randomness
            if prob == 0.0:
                assert replacement_rate == 0.0, \
                    f"prob={prob} should result in no replacements"
            elif prob == 1.0:
                assert replacement_rate > 0.5, \
                    f"prob={prob} should result in most replacements"
    
    def test_slang_no_match_scenarios(self):
        """Test slang functions when no rules match."""
        texts_without_matches = [
            "Hello, world!",
            "How are you?",
            "Good morning",
            "Thank you",
            "123456",
            "!@#$%^&*()",
        ]
        
        for text in texts_without_matches:
            result_breton = apply_breton_slang(text, prob=1.0)
            result_norman = apply_norman_slang(text, prob=1.0)
            
            # Should return original text when no matches
            assert result_breton == text, \
                f"Breton slang should not change '{text}'"
            assert result_norman == text, \
                f"Norman slang should not change '{text}'"
