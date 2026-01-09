#!/usr/bin/env python3
"""Test models.characters module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from models.characters import get_character_config, get_character_id, get_system_prompt_for_character

print("Testing models.characters...")

# Test get_character_config
config = get_character_config("00001")
assert "name" in config
assert "product_id" in config
print(f"✓ get_character_config('00001') = {config['name']}")

# Test get_character_id
char_id = get_character_id("00001")
assert char_id == "00001"
print(f"✓ get_character_id('00001') = {char_id}")

# Test get_system_prompt_for_character
prompt = get_system_prompt_for_character("00001")
assert len(prompt) > 0
print(f"✓ get_system_prompt_for_character('00001') returns prompt ({len(prompt)} chars)")

print("\n✅ models.characters module works correctly!")
