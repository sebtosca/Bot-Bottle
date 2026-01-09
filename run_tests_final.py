"""Run all tests and report failures."""

import subprocess
import sys

print("Running all endpoint tests...\n")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "endpoint/tests/", "-v", "--tb=line", "--maxfail=20"],
    capture_output=True,
    text=True,
    timeout=120
)

print(result.stdout)

if result.stderr:
    print("\nSTDERR:", result.stderr)

# Extract summary
if "failed" in result.stdout.lower() or "error" in result.stdout.lower():
    print("\n" + "="*60)
    print("FAILURES DETECTED")
    print("="*60)
    lines = result.stdout.split('\n')
    for line in lines:
        if "FAILED" in line or "ERROR" in line:
            print(line)
else:
    print("\n✅ All tests passed!")

sys.exit(result.returncode)
