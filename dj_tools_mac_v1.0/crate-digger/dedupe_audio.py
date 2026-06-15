#!/usr/bin/env python3
"""
Audio dedupe (macOS) -- the Mac equivalent of dedupe_audio.ps1.

Recursively fingerprints every .mp3 under a folder using fpcalc (Chromaprint)
and moves duplicates into a _dupes subfolder at the root of that folder.

- The first file seen with a given fingerprint stays in place.
- Every later file with the same fingerprint is moved to <root>/_dupes/.
- Nothing is ever deleted. Files are only moved.

Requires fpcalc on PATH (brew install chromaprint), or a bundled fpcalc next
to this script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
_FPCALC_BIN = "fpcalc.exe" if os.name == "nt" else "fpcalc"
DEFAULT_FPCALC = SCRIPT_DIR / _FPCALC_BIN
DEFAULT_ROOT = str(Path.home() / "Music" / "SoundCloud")


def find_fpcalc() -> Path | None:
    if DEFAULT_FPCALC.exists():
        return DEFAULT_FPCALC
    on_path = shutil.which("fpcalc")
    return Path(on_path) if on_path else None


def normalize_input_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def get_fingerprint(fpcalc: Path, file_path: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(fpcalc), "-raw", "-length", "120", "--", str(file_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("FINGERPRINT="):
            return line[len("FINGERPRINT="):]
    return None


def unique_target(dupe_root: Path, file_path: Path, index: int) -> Path:
    target = dupe_root / file_path.name
    if target.exists():
        target = dupe_root / f"{file_path.stem}__dup_{index}{file_path.suffix}"
    return target


def main() -> int:
    fpcalc = find_fpcalc()
    if fpcalc is None:
        print(f"ERROR: fpcalc not found at {DEFAULT_FPCALC} or on PATH.")
        print("       Install it with 'brew install chromaprint'.")
        return 1

    if len(sys.argv) > 1:
        music_input = sys.argv[1]
    else:
        music_input = input(
            f"Enter music root path, press ENTER for default [{DEFAULT_ROOT}], or Q to return to menu: "
        )
        if music_input.strip().lower() == "q":
            print("Returning to menu.")
            return 0
        if not music_input.strip():
            music_input = DEFAULT_ROOT

    music_input = normalize_input_path(music_input)
    if not music_input:
        music_input = DEFAULT_ROOT

    music_root = Path(music_input).expanduser().resolve()
    if not music_root.exists():
        print(f"ERROR: music root not found: {music_root}")
        return 1

    dupe_root = music_root / "_dupes"
    dupe_root.mkdir(parents=True, exist_ok=True)
    dupe_root_resolved = dupe_root.resolve()

    files = [
        p
        for p in sorted(music_root.rglob("*.mp3"))
        if p.is_file() and dupe_root_resolved not in p.resolve().parents
    ]
    total = len(files)

    print()
    print("=== AUDIO DEDUPE START ===")
    print(f"Tool folder: {SCRIPT_DIR}")
    print(f"Music root: {music_root}")
    print(f"Duplicate folder: {dupe_root}")
    print(f"MP3 files to fingerprint: {total}")
    print()

    if total == 0:
        print(f"No MP3 files found under {music_root}. Nothing to dedupe.")
        print()
        print("=== AUDIO DEDUPE END ===")
        return 0

    seen: dict[str, str] = {}
    moved = skipped = errors = 0

    for index, file_path in enumerate(files, 1):
        print(f"[DEDUPE] ({index}/{total}) {file_path}")
        try:
            fingerprint = get_fingerprint(fpcalc, file_path)
            if fingerprint is None:
                print(f"[DEDUPE] Skipped (no fingerprint): {file_path.name}")
                skipped += 1
                continue

            if fingerprint in seen:
                target = unique_target(dupe_root, file_path, index)
                shutil.move(str(file_path), str(target))
                print(f"[DEDUPE] Moved duplicate -> {target}")
                moved += 1
            else:
                seen[fingerprint] = str(file_path)
        except Exception as exc:  # noqa: BLE001 - keep scanning on any error
            errors += 1
            print(f"[DEDUPE] Error on {file_path.name}: {exc}")
            continue

    print()
    print("=== AUDIO DEDUPE END ===")
    print(f"Fingerprinted: {total - skipped - errors} of {total}")
    print(f"Duplicates moved: {moved}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] dedupe_audio failed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
