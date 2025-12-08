#!/usr/bin/env python3
"""
Convert .gif files into WhatsApp-compatible MP4 “GIFs”.

Constraints we aim for:
- Format: MP4 (H.264)
- Duration: <= 6 seconds (we trim longer GIFs)
- No audio
- Reasonable resolution (we scale to max 512px on longer side)
- Recommended size: <= ~1.5MB (we warn if larger)

Requirements:
- ffmpeg and ffprobe installed and available on PATH.
"""

import subprocess
import sys
from pathlib import Path

MAX_DURATION_SEC = 6
MAX_LONG_SIDE = 512
RECOMMENDED_MAX_KB = 1500  # ~1.5MB


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command, raise on non-zero exit."""
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def get_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe, or 0.0 on failure."""
    try:
        result = run_cmd([
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1",
            str(path),
        ])
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def convert_gif_to_mp4(input_path: Path, output_path: Path) -> bool:
    """
    Convert a GIF to WhatsApp-style MP4:
    - Strip audio
    - Limit to MAX_DURATION_SEC (trim if longer)
    - Scale so that longer side <= MAX_LONG_SIDE
    """
    print(f"\nConverting: {input_path.name}")

    # Check duration (optional, mostly for informational logging)
    duration = get_duration(input_path)
    if duration > 0:
        print(f"  Original duration: {duration:.2f}s")
    else:
        print("  Original duration: (unknown, ffprobe failed; continuing)")

    # ffmpeg filter: scale longer side to MAX_LONG_SIDE, preserve aspect
    # 'scale=' uses -2 to keep width/height even (required by some encoders).
    scale_filter = f"scale='if(gt(a,1),{MAX_LONG_SIDE},-2)':'if(gt(a,1),-2,{MAX_LONG_SIDE})'"

    # Build ffmpeg command
    # -an: no audio
    # -t: trim to MAX_DURATION_SEC
    # -movflags +faststart: good practice for web/streaming
    cmd = [
        "ffmpeg",
        "-y",  # overwrite
        "-i", str(input_path),
        "-an",
        "-t", str(MAX_DURATION_SEC),
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        print("  Running ffmpeg...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            print("  ❌ ffmpeg failed")
            print("  --- ffmpeg stderr ---")
            print(proc.stderr)
            return False
    except FileNotFoundError:
        print("  ❌ ffmpeg not found. Install ffmpeg and ensure it is on your PATH.")
        return False

    if not output_path.exists():
        print("  ❌ Output file not created.")
        return False

    size_kb = output_path.stat().st_size / 1024
    print(f"  ✅ Created: {output_path.name} ({size_kb:.1f} KB)")

    if size_kb > RECOMMENDED_MAX_KB:
        print(f"  ⚠️  File is larger than ~1.5MB; WhatsApp may reject it or load slowly.")

    return True


def main() -> int:
    """
    Usage:
        python scripts/convert_gifs_to_mp4.py [GIF_DIR]

    - If GIF_DIR is omitted, defaults to project_root / \"GIF\".
    - Converts all *.gif files in that directory to *_whatsapp.mp4.
    """
    project_root = Path(__file__).parent
    if len(sys.argv) > 1:
        gif_dir = Path(sys.argv[1])
        if not gif_dir.is_absolute():
            gif_dir = project_root / gif_dir
    else:
        gif_dir = project_root / "GIF"

    if not gif_dir.exists():
        print(f"❌ GIF directory not found: {gif_dir}")
        return 1

    gifs = sorted(gif_dir.glob("*.gif"))
    if not gifs:
        print(f"❌ No .gif files found in {gif_dir}")
        return 1

    print("=" * 60)
    print("Converting GIFs to WhatsApp-style MP4")
    print("=" * 60)
    print(f"Directory: {gif_dir}")
    print(f"Found {len(gifs)} GIF file(s)\n")

    results = []
    for gif in gifs:
        # e.g. \"Diva Reaction GIF by MOODMAN.gif\" -> \"Diva Reaction GIF by MOODMAN_whatsapp.mp4\"
        output_path = gif.with_suffix("")  # strip .gif
        output_path = output_path.with_name(output_path.name + "_whatsapp.mp4")
        ok = convert_gif_to_mp4(gif, output_path)
        results.append((gif.name, output_path.name, ok))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success = 0
    for src, dst, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {src} -> {dst}")
        if ok:
            success += 1

    print(f"\nConverted successfully: {success}/{len(results)}")
    if success > 0:
        print("\nNext steps:")
        print("  1. Reference the new *_whatsapp.mp4 filenames in gifs.json under \"filename\".")
        print("  2. Run: python scripts/load_gifs.py")
        print("  3. Test: python test_send_gif.py +YOUR_PHONE_NUMBER")

    return 0 if success == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

    