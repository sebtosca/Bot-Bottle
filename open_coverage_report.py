"""Generate and open HTML coverage report."""

import subprocess
import sys
import os
from pathlib import Path

# Run pytest with coverage
print("Generating coverage report...")
result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "endpoint/tests/unit/webhook/",
        "--cov=endpoint.webhook",
        "--cov-report=html",
        "--cov-report=term",
        "-q"
    ],
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)

# Check if report was generated
htmlcov_path = Path("htmlcov/index.html")
if htmlcov_path.exists():
    abs_path = htmlcov_path.absolute()
    print(f"\n✅ Coverage report generated at: {abs_path}")
    
    # Convert WSL path to Windows path if needed
    if "/mnt/c/" in str(abs_path):
        # WSL path: /mnt/c/Users/... -> C:\Users\...
        win_path = str(abs_path).replace("/mnt/c/", "C:\\").replace("/", "\\")
        print(f"Windows path: {win_path}")
    else:
        win_path = str(abs_path)
    
    # Open in browser (Windows)
    if sys.platform == "win32":
        os.startfile(win_path)
    elif "microsoft" in os.uname().release.lower() or "/mnt/" in str(abs_path):
        # WSL - use Windows cmd to open
        subprocess.run(["cmd.exe", "/c", "start", win_path], shell=False)
    else:
        # Linux/Mac
        subprocess.run(["xdg-open", str(abs_path)])
    
    print("Opening in browser...")
else:
    print(f"\n❌ Report not found at: {htmlcov_path.absolute()}")
    print("Full path:", htmlcov_path.absolute())
