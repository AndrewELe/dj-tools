#!/usr/bin/env python3
"""
WAV to MP3 encoder (single file).

Encodes one .wav file to .mp3 using LAME V0 VBR. V0 is the standard
"best quality / smallest size" trade-off: practically transparent quality
at roughly 25-30% smaller than 320 CBR.

Uses the bundled ffmpeg.exe in crate-digger/ by default. Falls back to
ffmpeg on PATH if the bundled one is missing.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_FFMPEG = PROJECT_ROOT / "crate-digger" / "ffmpeg.exe"


def normalize_input_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def find_ffmpeg(explicit: Path | None) -> Path:
    if explicit and explicit.exists():
        return explicit
    if DEFAULT_FFMPEG.exists():
        return DEFAULT_FFMPEG
    on_path = shutil.which("ffmpeg")
    if on_path:
        return Path(on_path)
    raise FileNotFoundError(
        f"Could not find ffmpeg. Expected at {DEFAULT_FFMPEG} or on PATH."
    )


def unique_output_path(wav_path: Path) -> Path:
    candidate = wav_path.with_suffix(".mp3")
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        alt = wav_path.with_name(f"{wav_path.stem} ({counter}).mp3")
        if not alt.exists():
            return alt
        counter += 1


def encode_wav_to_mp3(wav_path: Path, ffmpeg_path: Path) -> Path:
    mp3_path = unique_output_path(wav_path)

    cmd = [
        str(ffmpeg_path),
        "-hide_banner",
        "-loglevel", "warning",
        "-i", str(wav_path),
        "-codec:a", "libmp3lame",
        "-q:a", "0",
        "-map_metadata", "0",
        str(mp3_path),
    ]

    print(f"[ENCODE] {wav_path.name} -> {mp3_path.name}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        if mp3_path.exists():
            try:
                mp3_path.unlink()
            except OSError:
                pass
        raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

    return mp3_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Encode a single WAV file to MP3 using LAME V0 VBR."
    )
    parser.add_argument("wav_file", nargs="?", help="Path to a .wav file")
    parser.add_argument(
        "--ffmpeg",
        type=Path,
        default=None,
        help="Override ffmpeg.exe path",
    )
    args = parser.parse_args()

    if args.wav_file:
        wav_input = args.wav_file
    else:
        wav_input = input("Enter the .wav file path (or Q to return to menu): ")

    wav_input = normalize_input_path(wav_input)

    if wav_input.lower() == "q":
        print("Returning to menu.")
        return 0

    if not wav_input:
        print("No file provided.")
        return 1

    wav_path = Path(wav_input).expanduser().resolve()

    if not wav_path.exists():
        print(f"File does not exist: {wav_path}")
        return 1

    if not wav_path.is_file():
        print(f"Not a file: {wav_path}")
        return 1

    if wav_path.suffix.lower() != ".wav":
        print(f"Not a .wav file: {wav_path}")
        return 1

    try:
        ffmpeg_path = find_ffmpeg(args.ffmpeg)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1

    original_size = wav_path.stat().st_size

    try:
        mp3_path = encode_wav_to_mp3(wav_path, ffmpeg_path)
    except RuntimeError as exc:
        print(f"[ERROR] Encoding failed: {exc}")
        return 1

    new_size = mp3_path.stat().st_size
    savings_pct = (1 - new_size / original_size) * 100 if original_size else 0.0

    print()
    print("Done.")
    print(f"Original (.wav):  {wav_path}")
    print(f"  Size:           {format_size(original_size)}")
    print(f"Encoded (.mp3):   {mp3_path}")
    print(f"  Size:           {format_size(new_size)}")
    print(f"  Savings:        {savings_pct:.1f}%")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] wav_to_mp3 failed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
