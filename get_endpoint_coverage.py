#!/usr/bin/env python3
"""Get endpoint test coverage percentage."""

import subprocess
import sys
import re

print("Running endpoint tests with coverage...")
print("=" * 70)

# Run pytest with coverage
result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "endpoint/tests/unit/",
        "endpoint/tests/integration/",
        "--cov=endpoint",
        "--cov-report=term",
        "-q"
    ],
    capture_output=True,
    text=True,
    timeout=180
)

output = result.stdout + result.stderr

# Find the coverage table
lines = output.split('\n')
in_coverage_table = False
coverage_lines = []

for i, line in enumerate(lines):
    if 'Name' in line and 'Stmts' in line:
        in_coverage_table = True
        coverage_lines.append(line)
        continue
    if in_coverage_table:
        if line.strip() and ('endpoint' in line.lower() or 'TOTAL' in line or '---' in line):
            coverage_lines.append(line)
        if 'TOTAL' in line and '%' in line:
            coverage_lines.append(line)
            break

# Print coverage summary
if coverage_lines:
    print("\nCoverage Report:")
    print("=" * 70)
    for line in coverage_lines:
        print(line)
    
    # Extract total coverage
    total_line = coverage_lines[-1] if coverage_lines else ""
    match = re.search(r'(\d+)%', total_line)
    if match:
        coverage_pct = int(match.group(1))
        print("\n" + "=" * 70)
        if coverage_pct >= 80:
            print(f"✅ ENDPOINT COVERAGE: {coverage_pct}% (Meets 80% target!)")
        else:
            print(f"⚠️  ENDPOINT COVERAGE: {coverage_pct}% (Below 80% target)")
        print("=" * 70)
else:
    print("\n⚠️  Could not find coverage summary in output")
    print("\nLast 20 lines of output:")
    print("\n".join(lines[-20:]))

if result.returncode != 0:
    print(f"\n⚠️  Tests exited with code {result.returncode}")
    sys.exit(1)
