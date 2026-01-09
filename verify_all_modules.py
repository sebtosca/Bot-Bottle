#!/usr/bin/env python3
"""Verify all modularized files compile correctly."""

import sys
import ast
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# All files to verify
files = [
    # Core
    "core/__init__.py",
    "core/game/__init__.py",
    "core/game/feeding_game.py",
    "core/state/__init__.py",
    "core/state/bottle_state.py",
    "core/points/__init__.py",
    "core/points/rewards.py",
    
    # Features
    "features/__init__.py",
    "features/receipt/__init__.py",
    "features/receipt/verification.py",
    "features/stats/__init__.py",
    "features/stats/visualizer.py",
    "features/stats/display.py",
    "features/promos/__init__.py",
    "features/promos/supermarket.py",
    
    # Services
    "services/__init__.py",
    "services/whatsapp/__init__.py",
    "services/whatsapp/client.py",
    
    # Models
    "models/__init__.py",
    "models/characters.py",
]

print("=" * 70)
print("Verifying All Modularized Files")
print("=" * 70)

errors = []
for file_path in files:
    full_path = project_root / file_path
    if not full_path.exists():
        errors.append(f"{file_path}: File not found")
        print(f"✗ {file_path}")
        continue
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f"✓ {file_path}")
    except SyntaxError as e:
        errors.append(f"{file_path}: Syntax error at line {e.lineno}: {e.msg}")
        print(f"✗ {file_path}: {e.msg} at line {e.lineno}")
    except Exception as e:
        errors.append(f"{file_path}: {e}")
        print(f"✗ {file_path}: {e}")

print("\n" + "=" * 70)
if errors:
    print(f"❌ {len(errors)} error(s) found:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print(f"✅ All {len(files)} files have valid Python syntax!")
    print("\nNote: Some imports may fail without dependencies installed.")
    print("Install dependencies: pip install -r requirements.txt")
    sys.exit(0)
