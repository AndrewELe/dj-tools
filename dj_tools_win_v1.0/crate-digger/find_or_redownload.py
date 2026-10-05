#!/usr/bin/env python3
"""
Find a track locally, redownload from SoundCloud likes if missing.

1. Recursively scan a folder for an audio file whose name contains the
   given track name (case-insensitive substring).
2. If at least one match is found locally, print the path(s) and exit.
3. If nothing is found locally, enumerate the SoundCloud likes via yt-dlp
   in flat-playlist mode, filter for the same substring, present any
   matches numbered, and download whichever the user picks into a
   "lost tracks" subfolder of the searched folder.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a"}
DEFAULT_LIKES_URL = "https://soundcloud.com/druleprivate/likes"
LOST_TRACKS_DIRNAME = "lost tracks"

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_YTDLP = SCRIPT_DIR / "yt-dlp.exe"

LikeItem = Tuple[str, str, str]  # (id, title, url)


def get_cookie_args() -> List[str]:
    """SoundCloud login cookies, same precedence as digcrate.bat / grab-url.ps1:
    explicit file > sc_cookies.txt next to this script > browser (default none).
    Logging in raises the rate-limit ceiling and unlocks SoundCloud+/Go+ perks
    (256kbps "High Quality" AAC streams, Go+-exclusive tracks) instead of
    silently running anonymous. Set DJTOOLS_SC_COOKIES_BROWSER=none with no
    cookies file to run anonymously on purpose.
    """
    cookie_file = os.environ.get("DJTOOLS_SC_COOKIES_FILE")
    if not cookie_file:
        default_cookie_file = SCRIPT_DIR / "sc_cookies.txt"
        if default_cookie_file.exists():
            cookie_file = str(default_cookie_file)

    if cookie_file:
        print(f"[OK] Using SoundCloud login cookies from: {cookie_file}")
        return ["--cookies", cookie_file]

    cookie_browser = os.environ.get("DJTOOLS_SC_COOKIES_BROWSER", "none")
    if cookie_browser and cookie_browser.lower() != "none":
        return ["--cookies-from-browser", cookie_browser]

    print("[WARN] No sc_cookies.txt found - running anonymously (no Go+ streams).")
    return []


def normalize_input_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")


def find_local_matches(search_root: Path, needle: str) -> List[Path]:
    needle_l = needle.lower()
    matches: List[Path] = []
    for path in search_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        if needle_l in path.stem.lower():
            matches.append(path)
    return matches


def fetch_likes(ytdlp_path: Path, likes_url: str) -> List[LikeItem]:
    print(f"Fetching likes from {likes_url}")
    print("(this can take 10-30 seconds for a large likes list)...")

    cmd = [
        str(ytdlp_path),
        "--ignore-config",
        "--no-update",
        *get_cookie_args(),
        "--flat-playlist",
        "--print", "%(id)s|||%(title)s|||%(webpage_url)s",
        likes_url,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        print(f"[ERROR] yt-dlp failed listing likes (exit {result.returncode})")
        if result.stderr:
            for line in result.stderr.splitlines()[:10]:
                print(f"  {line}")
        return []

    items: List[LikeItem] = []
    for line in result.stdout.splitlines():
        parts = line.split("|||")
        if len(parts) >= 3 and parts[1].strip():
            items.append((parts[0], parts[1], parts[2]))
    return items


def filter_likes(items: List[LikeItem], needle: str) -> List[LikeItem]:
    needle_l = needle.lower()
    return [item for item in items if needle_l in item[1].lower()]


def parse_selection(raw: str, max_n: int) -> List[int]:
    raw = raw.strip().lower()
    if raw == "all":
        return list(range(1, max_n + 1))
    out: List[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            n = int(token)
        except ValueError:
            raise ValueError(f"'{token}' is not a number")
        if not (1 <= n <= max_n):
            raise ValueError(f"{n} is out of range (1-{max_n})")
        if n not in out:
            out.append(n)
    return out


def download_track(ytdlp_path: Path, url: str, output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(uploader)s - %(title)s.%(ext)s")

    cmd = [
        str(ytdlp_path),
        # Skip the crate digger's portable yt-dlp.conf: its --download-archive
        # would treat a lost track as "already downloaded" and exit 0 having
        # fetched nothing, and its 13-minute filter would drop long tracks.
        "--ignore-config",
        "--no-update",
        *get_cookie_args(),
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--format", "bestaudio",
        "--embed-thumbnail",
        "--embed-metadata",
        "--add-metadata",
        "--no-playlist",
        "--ignore-errors",
        "-o", output_template,
        url,
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def prompt_track_name(supplied: str | None) -> str | None:
    if supplied:
        return supplied.strip().strip('"').strip("'")
    raw = input("Enter the track name to find (or Q to return to menu): ")
    raw = raw.strip().strip('"').strip("'")
    if raw.lower() == "q":
        return None
    return raw


def prompt_search_folder(supplied: str | None) -> str | None:
    if supplied:
        return normalize_input_path(supplied)
    raw = input("Enter the folder to search recursively (or Q to return to menu): ")
    raw = normalize_input_path(raw)
    if raw.lower() == "q":
        return None
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find a track locally; redownload from SoundCloud likes if missing."
    )
    parser.add_argument("--track-name", help="Track name to search for")
    parser.add_argument("--search-folder", help="Folder to scan recursively")
    parser.add_argument(
        "--likes-url",
        default=DEFAULT_LIKES_URL,
        help=f"SoundCloud likes URL (default: {DEFAULT_LIKES_URL})",
    )
    parser.add_argument(
        "--ytdlp",
        type=Path,
        default=None,
        help="Override yt-dlp.exe path (default: bundled crate-digger/yt-dlp.exe)",
    )
    args = parser.parse_args()

    track_name = prompt_track_name(args.track_name)
    if track_name is None:
        print("Returning to menu.")
        return 0
    if not track_name:
        print("No track name provided.")
        return 1

    search_input = prompt_search_folder(args.search_folder)
    if search_input is None:
        print("Returning to menu.")
        return 0
    if not search_input:
        print("No folder provided.")
        return 1

    search_root = Path(search_input).expanduser().resolve()
    if not search_root.exists():
        print(f"Folder does not exist: {search_root}")
        return 1
    if not search_root.is_dir():
        print(f"Not a folder: {search_root}")
        return 1

    print()
    print(f"Searching {search_root} recursively for '{track_name}'...")
    local_matches = find_local_matches(search_root, track_name)

    if local_matches:
        print()
        print(f"Found {len(local_matches)} matching file(s) locally:")
        for m in local_matches:
            print(f"  {m}")
        return 0

    print("Not found locally.")
    print()

    ytdlp_path = args.ytdlp if args.ytdlp else DEFAULT_YTDLP
    if not ytdlp_path.exists():
        on_path = shutil.which("yt-dlp")
        if on_path:
            ytdlp_path = Path(on_path)
        else:
            print(f"Error: yt-dlp not found at {DEFAULT_YTDLP} or on PATH.")
            return 1

    all_likes = fetch_likes(ytdlp_path, args.likes_url)
    if not all_likes:
        print("Could not fetch likes list. Nothing more to try.")
        return 1

    print(f"Got {len(all_likes)} items from likes. Filtering for '{track_name}'...")
    matches = filter_likes(all_likes, track_name)

    if not matches:
        print()
        print(f"No matches found in your likes for '{track_name}'.")
        print("You may need to search SoundCloud or your other sources manually.")
        return 0

    print()
    print(f"Found {len(matches)} match(es) in your likes:")
    print()
    for i, (_track_id, title, url) in enumerate(matches, 1):
        print(f"  {i}. {title}")
        print(f"     {url}")
    print()

    pick = input(
        "Enter number(s) to download (e.g. '1' or '1,3'), 'all', or Q to return to menu: "
    ).strip()

    if pick.lower() == "q":
        print("Returning to menu.")
        return 0

    try:
        indices = parse_selection(pick, len(matches))
    except ValueError as exc:
        print(f"Invalid selection: {exc}")
        return 1

    if not indices:
        print("No tracks selected.")
        return 0

    selected = [matches[i - 1] for i in indices]
    lost_dir = search_root / LOST_TRACKS_DIRNAME

    print()
    print(f"Downloading {len(selected)} track(s) into {lost_dir}")
    print()

    successes = 0
    for _track_id, title, url in selected:
        print(f"[DOWNLOAD] {title}")
        if download_track(ytdlp_path, url, lost_dir):
            successes += 1
            print(f"           OK")
        else:
            print(f"           [FAIL] could not download")
        print()

    print(f"Done. {successes} of {len(selected)} downloaded to {lost_dir}.")
    return 0 if successes == len(selected) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] find_or_redownload failed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
