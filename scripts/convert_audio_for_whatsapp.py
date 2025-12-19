#!/usr/bin/env python3
"""Convert audio file to WhatsApp-compatible format.

WhatsApp audio requirements:
- Format: MP3, AAC, AMR, OGG (Opus), or MP4 Audio
- Max size: 16 MB
- Recommended MP3 settings:
  - Bitrate: 128 kbps
  - Sample Rate: 44.1 kHz
  - Channels: Mono (1 channel)

Usage:
    python scripts/convert_audio_for_whatsapp.py [input_file] [output_file]
    
Example:
    python scripts/convert_audio_for_whatsapp.py music/happy-tune-30s-449787.mp3 music/happy-tune-30s-449787_whatsapp.mp3
"""

import sys
import subprocess
from pathlib import Path

def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def convert_audio(input_path: Path, output_path: Path):
    """Convert audio to WhatsApp-compatible format."""
    print("=" * 60)
    print("🔄 CONVERTING AUDIO FOR WHATSAPP")
    print("=" * 60)
    print()
    
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        print()
        print("Available files in the same directory:")
        if input_path.parent.exists():
            for f in sorted(input_path.parent.glob("*.mp3")):
                print(f"  - {f.name}")
        return 1
    
    if not check_ffmpeg():
        print("❌ ffmpeg not found!")
        print()
        print("Install ffmpeg:")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        print("  Or use: winget install ffmpeg")
        print("  Or use: choco install ffmpeg")
        print()
        print("After installing, restart your terminal and try again.")
        return 1
    
    print(f"   Input file: {input_path}")
    print(f"   Output file: {output_path}")
    print()
    print("   Converting with settings:")
    print("   - Codec: libmp3lame (MP3)")
    print("   - Bitrate: 128 kbps")
    print("   - Sample Rate: 44.1 kHz")
    print("   - Channels: Mono (1 channel)")
    print()
    
    # Build ffmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-acodec', 'libmp3lame',
        '-ab', '128k',
        '-ar', '44100',
        '-ac', '1',
        '-y',  # Overwrite output file if exists
        str(output_path)
    ]
    
    try:
        print("   Running ffmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            if output_path.exists():
                input_size = input_path.stat().st_size / (1024 * 1024)
                output_size = output_path.stat().st_size / (1024 * 1024)
                print()
                print("=" * 60)
                print("✅ CONVERSION SUCCESSFUL!")
                print("=" * 60)
                print(f"   Input size: {input_size:.2f} MB")
                print(f"   Output size: {output_size:.2f} MB")
                print(f"   Output file: {output_path}")
                print()
                print("   ✅ File is now WhatsApp-compatible!")
                return 0
            else:
                print("   ❌ Output file was not created")
                return 1
        else:
            print("   ❌ Conversion failed")
            print(f"   Error: {result.stderr}")
            return 1
            
    except subprocess.TimeoutExpired:
        print("   ❌ Conversion timed out (> 5 minutes)")
        return 1
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 1

def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    
    if len(sys.argv) < 2:
        print("Usage: python scripts/convert_audio_for_whatsapp.py [input_file] [output_file]")
        print()
        print("Example:")
        print("  python scripts/convert_audio_for_whatsapp.py music/happy-tune-30s-449787.mp3 music/happy-tune-30s-449787_whatsapp.mp3")
        print()
        print("Available files in music/:")
        music_dir = project_root / "music"
        if music_dir.exists():
            for f in music_dir.glob("*.mp3"):
                print(f"  - {f.name}")
        return 1
    
    # Handle both relative and absolute paths
    input_arg = sys.argv[1]
    if Path(input_arg).is_absolute():
        input_file = Path(input_arg)
    else:
        input_file = project_root / input_arg
    
    # Resolve the path to handle any symlinks or relative issues
    try:
        input_file = input_file.resolve()
    except:
        pass  # If resolve fails, use as-is
    
    if len(sys.argv) > 2:
        output_arg = sys.argv[2]
        if Path(output_arg).is_absolute():
            output_file = Path(output_arg)
        else:
            output_file = project_root / output_arg
    else:
        # Auto-generate output filename
        stem = input_file.stem
        output_file = input_file.parent / f"{stem}_whatsapp{input_file.suffix}"
    
    return convert_audio(input_file, output_file)

if __name__ == "__main__":
    exit(main())
