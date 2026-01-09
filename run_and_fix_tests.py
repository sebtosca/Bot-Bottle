"""Run tests and report failures for fixing."""

import subprocess
import sys
import re

def run_tests_category(category):
    """Run tests for a category and return failures."""
    print(f"\n{'='*70}")
    print(f"Testing: {category}")
    print(f"{'='*70}\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", category, "-v", "--tb=line", "--maxfail=10"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Extract failures
    failures = []
    if "FAILED" in result.stdout or "ERROR" in result.stdout:
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if "FAILED" in line:
                failures.append(line.strip())
            elif "ERROR" in line and "collecting" not in line:
                failures.append(line.strip())
    
    return failures, result.returncode

# Test categories
categories = [
    "endpoint/tests/unit/webhook/",
    "endpoint/tests/unit/security/",
    "endpoint/tests/unit/middleware/",
    "endpoint/tests/unit/helpers/",
    "endpoint/tests/integration/",
    "endpoint/tests/e2e/"
]

all_failures = []
for category in categories:
    failures, code = run_tests_category(category)
    all_failures.extend(failures)
    if code != 0:
        print(f"\n❌ {len(failures)} failure(s) in {category}")

print(f"\n{'='*70}")
print(f"SUMMARY: {len(all_failures)} total failures found")
print(f"{'='*70}")
for failure in all_failures[:20]:  # Show first 20
    print(f"  {failure}")
