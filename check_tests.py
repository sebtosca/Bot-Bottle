"""Check test results and report failures."""

import subprocess
import sys

test_categories = [
    "endpoint/tests/unit/",
    "endpoint/tests/integration/",
    "endpoint/tests/e2e/"
]

for category in test_categories:
    print(f"\n{'='*60}")
    print(f"Running tests in: {category}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", category, "-v", "--tb=line", "-q"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    # Check for failures
    if "FAILED" in result.stdout or "ERROR" in result.stdout:
        print(f"\n❌ FAILURES FOUND in {category}")
        # Extract failure details
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if "FAILED" in line or "ERROR" in line:
                print(f"  {line}")
                # Print context
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if j != i:
                        print(f"    {lines[j]}")
    else:
        print(f"\n✅ All tests passed in {category}")
