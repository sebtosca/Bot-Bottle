#!/usr/bin/env python3
"""Check audio file format and convert if needed for WhatsApp compatibility.

WhatsApp Cloud API audio message requirements:
- Supported formats: MP3, AAC, AMR, OGG (Opus), MP4 Audio
- Maximum file size: 16 MB
- Recommended MP3 settings:
  - Bitrate: 128 kbps
  - Sample Rate: 44.1 kHz
  - Channels: Mono (1 channel)

Usage:
    python scripts/check_audio_format.py [audio_file_path]
"""

import sys
from pathlib import Path

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3NoHeaderError
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    print("⚠️  mutagen library not installed. Install with: pip install mutagen")
    print("   Will only check file size and extension.")

try:
    import subprocess
    HAS_FFMPEG = True
except ImportError:
    HAS_FFMPEG = False


def check_audio_file(file_path: Path):
    """Check audio file format and provide recommendations."""
    print("=" * 60)
    print("🎵 AUDIO FILE ANALYSIS")
    print("=" * 60)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    # Check file size
    file_size = file_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print(f"   File: {file_path.name}")
    print(f"   Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
    
    if file_size_mb > 16:
        print(f"   ❌ File size exceeds 16 MB limit!")
        print(f"   ⚠️  WhatsApp maximum is 16 MB")
        return False
    else:
        print(f"   ✅ File size is within 16 MB limit")
    
    # Check extension
    ext = file_path.suffix.lower()
    supported_extensions = ['.mp3', '.ogg', '.m4a', '.aac', '.amr']
    if ext not in supported_extensions:
        print(f"   ⚠️  Extension '{ext}' may not be supported")
        print(f"   Supported: {', '.join(supported_extensions)}")
    else:
        print(f"   ✅ Extension '{ext}' is supported")
    
    # Analyze MP3 file if mutagen is available
    if ext == '.mp3' and HAS_MUTAGEN:
        try:
            audio = MP3(file_path)
            
            # Get bitrate
            bitrate_kbps = audio.info.bitrate // 1000 if hasattr(audio.info, 'bitrate') else None
            if bitrate_kbps:
                print(f"   Bitrate: {bitrate_kbps} kbps")
                if bitrate_kbps != 128:
                    print(f"   ⚠️  Recommended: 128 kbps (current: {bitrate_kbps} kbps)")
                else:
                    print(f"   ✅ Bitrate is optimal (128 kbps)")
            
            # Get sample rate
            sample_rate = audio.info.sample_rate if hasattr(audio.info, 'sample_rate') else None
            if sample_rate:
                print(f"   Sample Rate: {sample_rate} Hz")
                if sample_rate != 44100:
                    print(f"   ⚠️  Recommended: 44.1 kHz (current: {sample_rate} Hz)")
                else:
                    print(f"   ✅ Sample rate is optimal (44.1 kHz)")
            
            # Get channels
            channels = audio.info.channels if hasattr(audio.info, 'channels') else None
            if channels:
                channel_type = "Mono" if channels == 1 else f"Stereo ({channels} channels)"
                print(f"   Channels: {channel_type}")
                if channels != 1:
                    print(f"   ⚠️  Recommended: Mono (1 channel) for voice messages")
                else:
                    print(f"   ✅ Mono channel (optimal for voice)")
            
            # Get length
            length = audio.info.length if hasattr(audio.info, 'length') else None
            if length:
                print(f"   Duration: {length:.2f} seconds ({length/60:.2f} minutes)")
            
        except ID3NoHeaderError:
            print(f"   ⚠️  MP3 file has no ID3 tags (may still work)")
        except Exception as e:
            print(f"   ⚠️  Could not analyze MP3 metadata: {e}")
    
    print()
    print("=" * 60)
    print("📋 RECOMMENDATIONS")
    print("=" * 60)
    
    if ext == '.mp3':
        print("   For best compatibility with WhatsApp voice messages:")
        print("   - Bitrate: 128 kbps")
        print("   - Sample Rate: 44.1 kHz")
        print("   - Channels: Mono (1 channel)")
        print()
        if HAS_FFMPEG:
            print("   To convert using ffmpeg:")
            output_file = file_path.parent / f"{file_path.stem}_whatsapp{file_path.suffix}"
            print(f"   ffmpeg -i \"{file_path}\" -acodec libmp3lame -ab 128k -ar 44100 -ac 1 \"{output_file}\"")
        else:
            print("   Install ffmpeg to convert audio files:")
            print("   - Windows: Download from https://ffmpeg.org/download.html")
            print("   - Or use online converters with these settings")
    else:
        print("   Consider converting to MP3 format for best compatibility")
        if HAS_FFMPEG:
            output_file = file_path.parent / f"{file_path.stem}_whatsapp.mp3"
            print(f"   ffmpeg -i \"{file_path}\" -acodec libmp3lame -ab 128k -ar 44100 -ac 1 \"{output_file}\"")
    
    print()
    return True


def main():
    """Main function."""
    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
    else:
        # Default to the voice message file
        project_root = Path(__file__).parent.parent
        audio_file = project_root / "music" / "happy-tune-30s-449787_whatsapp.mp3"
    
    if not audio_file.exists():
        print(f"❌ File not found: {audio_file}")
        print()
        print("Usage: python scripts/check_audio_format.py [audio_file_path]")
        return 1
    
    success = check_audio_file(audio_file)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
