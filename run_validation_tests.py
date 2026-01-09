"""Run validation unit and integration tests."""

import subprocess
import sys

print("Running validation tests...\n")
print("=" * 70)

test_files = [
    "endpoint/tests/unit/security/test_validation.py",
    "endpoint/tests/integration/security/test_validation_integration.py",
]

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        *test_files,
        "-v",
        "--tb=short",
        "--color=yes",
    ],
    capture_output=False,
    timeout=120,
)

print("\n" + "=" * 70)
if result.returncode == 0:
    print("✅ All validation tests passed!")
else:
    print(f"❌ Tests failed with exit code {result.returncode}")
    sys.exit(result.returncode)
