#!/usr/bin/env python3
"""Script to check test coverage and identify gaps."""

import subprocess
import sys

def run_coverage_check():
    """Run coverage check and parse results."""
    print("Running coverage check...")
    result = subprocess.run(
        [
            "python", "-m", "pytest",
            "llm/tests/unit/",
            "models/tests/unit/",
            "services/whatsapp/tests/unit/",
            "--cov=llm",
            "--cov=models",
            "--cov=services",
            "--cov-report=term",
            "-q"
        ],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    
    # Extract coverage percentages
    lines = result.stdout.split('\n')
    for line in lines:
        if 'llm/' in line or 'models/' in line or 'services/' in line or 'TOTAL' in line:
            if '%' in line:
                print(f"COVERAGE: {line.strip()}")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_coverage_check())
