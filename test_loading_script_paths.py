#!/usr/bin/env python3
"""Test loading script paths."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.load_enhanced_gifs import GIF_DIRECTORIES, ENHANCED_JSON_FILES

print("GIF Directories:")
print(f"  Cherry: {GIF_DIRECTORIES['00001']}")
print(f"  Pompon: {GIF_DIRECTORIES['00002']}")

print("\nEnhanced JSON Files:")
print(f"  Cherry: {ENHANCED_JSON_FILES['00001']}")
print(f"  Pompon: {ENHANCED_JSON_FILES['00002']}")

# Verify paths exist
assert GIF_DIRECTORIES['00001'].exists(), f"Cherry GIF directory not found: {GIF_DIRECTORIES['00001']}"
assert GIF_DIRECTORIES['00002'].exists(), f"Pompon GIF directory not found: {GIF_DIRECTORIES['00002']}"
assert ENHANCED_JSON_FILES['00001'].exists(), f"Cherry JSON not found: {ENHANCED_JSON_FILES['00001']}"
assert ENHANCED_JSON_FILES['00002'].exists(), f"Pompon JSON not found: {ENHANCED_JSON_FILES['00002']}"

print("\n✅ Loading script paths are correct!")
