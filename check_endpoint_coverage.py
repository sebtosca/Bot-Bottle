#!/usr/bin/env python3
"""Quick script to check endpoint test coverage."""

import subprocess
import sys
import re

print("Running endpoint tests with coverage...")
print("=" * 60)

result = subprocess.run(
    [
        "python", "-m", "pytest",
        "endpoint/tests/",
        "--cov=endpoint",
        "--cov-report=term",
        "-q",
        "--tb=no"
    ],
    capture_output=True,
    text=True,
    timeout=120
)

# Extract coverage summary
output = result.stdout + result.stderr
lines = output.split('\n')

# Find coverage summary
in_summary = False
for line in lines:
    if 'Name' in line and 'Stmts' in line:
        in_summary = True
        print("\nCoverage Summary:")
        print("=" * 60)
        continue
    if in_summary:
        if 'endpoint' in line.lower() or 'TOTAL' in line:
            print(line)
        if 'TOTAL' in line and '%' in line:
            # Extract percentage
            match = re.search(r'(\d+)%', line)
            if match:
                coverage = int(match.group(1))
                print("\n" + "=" * 60)
                if coverage >= 80:
                    print(f"✅ Endpoint coverage: {coverage}% (Above 80% target)")
                else:
                    print(f"⚠️  Endpoint coverage: {coverage}% (Below 80% target)")
                print("=" * 60)
            break

if result.returncode != 0:
    print("\n⚠️  Some tests may have failed. Check output above.")
    sys.exit(1)
