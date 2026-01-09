"""Script to run all tests and report failures."""

import subprocess
import sys

def run_tests():
    """Run all tests and capture output."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "endpoint/tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
