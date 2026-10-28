#!/usr/bin/env python3
"""
Sort By Genre
-------------

Purpose:
    Read the genre metadata from every MP3 sitting directly in a folder, or in
    its "00 new" inbox, and move each track into the numbered genre folder for
    its genre.

    Genres and folder numbers come from create_folders/genre_layout.py, the
    same layout make_music_paths.py builds:

        00 new/                 07 tech house/          14 dubstep/
        01 downtempo, organic/  08 minimal, deep tech/  15 trap/
        02 afro house/          09 breaks/              16 hard techno/
        03 deep house/          10 techno/              17 hard dance/
        04 melodic house/       11 prog trance/         18 hardstyle/
        05 prog house/          12 trance/              19 dnb/
        06 house/               13 ukg, bass house/     20 happy hardcore/
                                                        21 other/

Why the mapping is so forgiving:
    These tags come from SoundCloud uploaders by way of yt-dlp, not from
    Beatport, so they are inconsistent. A survey of a 556-track library found
    the genre field holding all of these:

        "Drum & Bass", "drum & bass", "Drum&Bass", "Drum'n'Bass", "D&B",
        "Drum and Bass", "dnb", "dance, drumandbass", "Drum & Bass/",
        "Drum & Bass, 50cent, bootleg"

    ...all meaning the same thing. Others bury a real genre inside upload
    keyword spam ('Add "Tech House"', "##progressive house", "Remix, House").
    So a tag is matched in three passes: the whole string, then each
    comma/slash-separated part, then the longest known genre appearing anywhere
    in it as a whole word.

What lands in "00 new":
    - Files with no genre frame at all (51 of 556 in that same library).
    - SoundCloud's catch-all defaults: "Dance & EDM" (56 files), "Electronic"
      (30), "Dance". These are tags, but they say nothing worth filing on.
    - Genres outside the toolkit's taxonomy ("Indie Dance", "Pop", "Mashup").
    - Pure keyword spam ("umf, ultramusicfestival, swedishhousemafia").

    Unrecognized tags are listed in the summary with counts so the ones worth
    supporting can be added to GENRE_ALIASES below.

Scope:
    Only MP3s sitting directly in the folder or directly in its "00 new" folder
    are touched. Anything already in a genre folder is left alone, and tracks
    that still can't be placed stay in "00 new", so re-running is safe.

Typical use:
    Drop new downloads into "00 new" in your library and run this on the
    library. Or run gather_all_music.ps1 first to flatten everything into
    "All Music", then run this to split that flat pile into genre folders.

Examples:
    py sort_by_genre.py "C:\\Music\\SoundCloud\\All Music" --dry-run
    py sort_by_genre.py "C:\\Music\\SoundCloud\\All Music"
    py sort_by_genre.py "C:\\Music\\SoundCloud\\All Music" --with-energy
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

try:
    from mutagen import File as MutagenFile
    from mutagen import MutagenError
except ImportError:
    print(
        "Error: mutagen is not installed for this Python.\n"
        "       Run sort_by_genre.bat instead, which uses the musicKeyConversion venv,\n"
        "       or install it with: py -m pip install mutagen",
        file=sys.stderr,
    )
    raise SystemExit(1)

# The genre list lives with the folder tools so every script agrees on it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "create_folders"))
from genre_layout import ENERGY_LEVELS, GENRE_FOLDERS, NEW_FOLDER  # noqa: E402


AUDIO_EXTENSION = ".mp3"

# Where untagged and unrecognized tracks land.
UNSORTED_FOLDER = NEW_FOLDER

# Maps a normalized genre tag to the genre it's filed under. Genres are the
# names in create_folders/genre_layout.py, which supplies the folder number.
#
# Keys must already be normalized the way normalize_genre() normalizes tags:
# lowercase, "&" spelled out as "and", every other punctuation mark collapsed to
# a single space. That is why entries look like "drum and bass" rather than
# "Drum & Bass", and why Beatport's combined names lose their slashes
# ("techno peak time driving" is the tag "Techno (Peak Time / Driving)").
GENRE_ALIASES: dict[str, str] = {
    # afro house
    "afro house": "afro house",
    "afro tech": "afro house",
    "afrobeat": "afro house",
    "amapiano": "afro house",
    # breaks
    "breaks": "breaks",
    "breakbeat": "breaks",
    "breakbeats": "breaks",
    "breaks breakbeat uk bass": "breaks",
    "nu skool breaks": "breaks",
    "big beat": "breaks",
    # dnb
    "dnb": "dnb",
    "d and b": "dnb",
    "drum and bass": "dnb",
    "drum n bass": "dnb",
    "drumandbass": "dnb",
    "drumnbass": "dnb",
    "liquid dnb": "dnb",
    "liquid drum and bass": "dnb",
    "neurofunk": "dnb",
    "jump up": "dnb",
    "halftime": "dnb",
    "drumstep": "dnb",
    "jungle": "dnb",
    # dubstep
    "dubstep": "dubstep",
    "riddim": "dubstep",
    "brostep": "dubstep",
    "melodic dubstep": "dubstep",
    "deep dubstep": "dubstep",
    "tearout": "dubstep",
    "colour bass": "dubstep",
    # happy hardcore
    "happy hardcore": "happy hardcore",
    "jumpcore": "happy hardcore",
    "hardcore": "happy hardcore",
    "uk hardcore": "happy hardcore",
    "uptempo": "happy hardcore",
    "uptempo hardcore": "happy hardcore",
    "frenchcore": "happy hardcore",
    "gabber": "happy hardcore",
    # minimal, deep tech
    "minimal": "minimal, deep tech",
    "deep tech": "minimal, deep tech",
    "minimal deep tech": "minimal, deep tech",
    "minimal techno": "minimal, deep tech",
    "microhouse": "minimal, deep tech",
    # downtempo, organic
    "organic house": "downtempo, organic",
    "organic house downtempo": "downtempo, organic",
    "downtempo": "downtempo, organic",
    "chill out": "downtempo, organic",
    "ambient": "downtempo, organic",
    "balearic": "downtempo, organic",
    "lounge": "downtempo, organic",
    # techno
    "techno": "techno",
    "techno peak time driving": "techno",
    "peak time techno": "techno",
    "driving techno": "techno",
    "techno raw deep hypnotic": "techno",
    "raw techno": "techno",
    "hypnotic techno": "techno",
    "detroit techno": "techno",
    "acid techno": "techno",
    "dub techno": "techno",
    "industrial techno": "techno",
    # trance
    "trance": "trance",
    "trance main floor": "trance",
    "psy trance": "trance",
    "psytrance": "trance",
    "psychedelic trance": "trance",
    "goa trance": "trance",
    "uplifting trance": "trance",
    "vocal trance": "trance",
    "tech trance": "trance",
    "hard trance": "trance",
    # trap
    "trap": "trap",
    "trap wave": "trap",
    "hybrid trap": "trap",
    "festival trap": "trap",
    # ukg, bass house
    "uk bass": "ukg, bass house",
    "bassline": "ukg, bass house",
    "uk garage": "ukg, bass house",
    "uk garage bassline": "ukg, bass house",
    "garage": "ukg, bass house",
    "2 step": "ukg, bass house",
    "speed garage": "ukg, bass house",
    "bass house": "ukg, bass house",
    # house
    "house": "house",
    "jackin house": "house",
    "electro house": "house",
    "future house": "house",
    "funky house": "house",
    "soulful house": "house",
    "disco house": "house",
    "acid house": "house",
    "classic house": "house",
    "nu disco": "house",
    "nu disco disco": "house",
    "big room": "house",
    "big room house": "house",
    "deep house": "deep house",
    "tech house": "tech house",
    # "Melodic" on its own is always melodic house/techno in this kind of
    # library; it never shows up meaning melodic dubstep or melodic dnb, which
    # carry those full names instead.
    "melodic": "melodic house",
    "melodic house": "melodic house",
    "melodic techno": "melodic house",
    "melodictechno": "melodic house",
    "melodic house and techno": "melodic house",
    # hardstyle
    "hardstyle": "hardstyle",
    "rawstyle": "hardstyle",
    "raw hardstyle": "hardstyle",
    "euphoric hardstyle": "hardstyle",
    "hardstyle hardcore": "hardstyle",
    "hard dance": "hard dance",
    "hard dance hardcore": "hard dance",
    "hard techno": "hard techno",
    # progressive
    "progressive house": "prog house",
    "prog house": "prog house",
    "progressive trance": "prog trance",
    "prog trance": "prog trance",
}

# Longest alias first, so substring matching picks "tech house" over "house"
# and "melodic techno" over "techno".
ALIASES_BY_LENGTH = sorted(GENRE_ALIASES, key=len, reverse=True)

# Tags that technically say something but are too broad to file on. "Dance &
# EDM" is what SoundCloud stamps on an upload when the artist picks nothing, so
# it means "untagged" in practice. These are treated as a missing tag so they
# surface in "00 new" rather than getting a bad guess.
GENERIC_TAGS = {
    "",
    "edm",
    "dance and edm",
    "electronic",
    "electronica",
    "eletronica",
    "eletronic",
    "electro",
    "dance",
    "dance electro pop",
    "emotional dance",
    "club",
    "audio",
    "music",
    "other",
    "unknown",
    "none",
    "n a",
    "na",
    "misc",
    "miscellaneous",
    "mashup",
    "remix",
    "bootleg",
    "free download",
    "original mix",
    "extended mix",
}


def normalize_genre(text: str) -> str:
    """
    Fold a raw genre tag down to lowercase words separated by single spaces.

    "Drum & Bass" -> "drum and bass"        "Drum'n'Bass"    -> "drum n bass"
    "Psy-Trance"  -> "psy trance"           '##progressive house'
    "D&B"         -> "d and b"                               -> "progressive house"
    """
    s = text.strip().lower()
    s = s.replace("&", " and ").replace("+", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def read_genre_tag(path: Path) -> str:
    """
    Return the raw genre string from the file's tags, or "" if there isn't one.

    mutagen's TCON.genres resolves the numeric ID3v1 references some older
    taggers write (e.g. "(17)") into readable names, so prefer it over .text.
    """
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return ""

    tags = audio.tags

    # ID3 (MP3/AIFF)
    if hasattr(tags, "getall"):
        for frame in tags.getall("TCON"):
            for value in getattr(frame, "genres", None) or []:
                if value and value.strip():
                    return value.strip()
            for value in getattr(frame, "text", None) or []:
                if str(value).strip():
                    return str(value).strip()

    # Vorbis comments / MP4 atoms, in case the folder isn't purely MP3.
    for key in ("genre", "GENRE", "\xa9gen"):
        try:
            values = tags.get(key)
        except Exception:
            values = None
        if values:
            for value in values if isinstance(values, list) else [values]:
                if str(value).strip():
                    return str(value).strip()

    return ""


def resolve_genre_path(raw_genre: str) -> Optional[tuple[str, ...]]:
    """
    Map a raw genre tag onto folder segments, or None if it can't be placed.

    Three passes, most specific first:
      1. The whole tag                  "Melodic House & Techno"
      2. Each comma/slash-separated part
                                        "Afro House / Deep House" -> afro house
                                        "dance, drumandbass"      -> dnb
      3. The longest known genre appearing anywhere in it as a whole word
                                        "Techno & Dance"          -> techno
                                        'Add "Tech House"'        -> tech house

    Pass 3 matches on whole words only, so "Anjunadeep, Cubicolor" does not get
    read as "deep" and filed under deep house.
    """
    if not raw_genre:
        return None

    whole = normalize_genre(raw_genre)
    if whole in GENERIC_TAGS:
        return None

    if whole in GENRE_ALIASES:
        return (GENRE_FOLDERS[GENRE_ALIASES[whole]],)

    for part in re.split(r"[/,;|]", raw_genre):
        normalized = normalize_genre(part)
        if normalized in GENRE_ALIASES:
            return (GENRE_FOLDERS[GENRE_ALIASES[normalized]],)

    padded = f" {whole} "
    for alias in ALIASES_BY_LENGTH:
        if f" {alias} " in padded:
            return (GENRE_FOLDERS[GENRE_ALIASES[alias]],)

    return None


def is_meaningless(raw_genre: str) -> bool:
    """True when the tag is missing or one of the catch-all defaults."""
    return normalize_genre(raw_genre) in GENERIC_TAGS


def ensure_folder(root: Path, segments: tuple[str, ...], with_energy: bool) -> Path:
    """Create the genre folder, plus its energy subfolders on request."""
    target = root.joinpath(*segments)
    target.mkdir(parents=True, exist_ok=True)

    if with_energy:
        for level in ENERGY_LEVELS:
            (target / level).mkdir(exist_ok=True)

    return target


def print_mapping() -> None:
    print("\nGenre tag -> folder")
    print("-" * 60)
    by_folder: dict[str, list[str]] = {}
    for alias, genre in GENRE_ALIASES.items():
        by_folder.setdefault(GENRE_FOLDERS[genre], []).append(alias)
    for folder in sorted(by_folder):
        print(f"\n{folder}/")
        for alias in sorted(by_folder[folder]):
            print(f"    {alias}")
    print(f"\nEverything else -> {UNSORTED_FOLDER}/")


def normalize_input_path(raw_input: str) -> str:
    return raw_input.strip().strip('"').strip("'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move MP3s into genre subfolders based on their metadata."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder holding the MP3s to sort. Prompted for if omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show where every track would go without moving anything.",
    )
    parser.add_argument(
        "--with-energy",
        action="store_true",
        help="Also create high/mid/low folders inside each genre folder.",
    )
    parser.add_argument(
        "--show-map",
        action="store_true",
        help="Print the genre tag to folder mapping and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.show_map:
        print_mapping()
        return 0

    if args.folder:
        folder_input = normalize_input_path(args.folder)
    else:
        folder_input = normalize_input_path(
            input("Enter the folder holding your MP3s (or Q to return to menu): ")
        )
        if folder_input.lower() == "q":
            print("Returning to menu.")
            return 0

    if not folder_input:
        print("Error: no folder path entered.", file=sys.stderr)
        return 2

    root = Path(folder_input).expanduser()
    if not root.exists():
        print(f"Error: path does not exist: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"Error: path is not a folder: {root}", file=sys.stderr)
        return 2

    root = root.resolve()

    # Only files sitting directly in the folder or its inbox. Tracks already
    # inside a genre folder have been sorted, which makes re-running a no-op.
    inbox = root / UNSORTED_FOLDER
    files = sorted(
        (
            p
            for folder in (root, inbox)
            if folder.is_dir()
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == AUDIO_EXTENSION
        ),
        key=lambda p: p.name.lower(),
    )

    print()
    print("=== SORT BY GENRE START ===")
    print(f"Folder: {root}")
    print(f"Tracks to sort: {len(files)}")
    if args.dry_run:
        print("Mode: DRY RUN (nothing will be moved)")
    print()

    if not files:
        print(f"No MP3s found directly in {root} or {inbox.name}/. Nothing to do.")
        print()
        print("=== SORT BY GENRE END ===")
        return 0

    sorted_count = 0
    untagged_count = 0
    unrecognized_count = 0
    skipped_count = 0
    error_count = 0
    folder_counts: Counter[str] = Counter()
    unrecognized_tags: Counter[str] = Counter()

    for path in files:
        try:
            raw_genre = read_genre_tag(path)
            segments = resolve_genre_path(raw_genre)

            if segments is None:
                if is_meaningless(raw_genre):
                    untagged_count += 1
                else:
                    unrecognized_count += 1
                    unrecognized_tags[raw_genre] += 1
                segments = (UNSORTED_FOLDER,)
                placed = False
            else:
                placed = True

            display_folder = "/".join(segments)
            destination = root.joinpath(*segments) / path.name

            if destination == path:
                # Already in the inbox and still can't be placed.
                folder_counts[display_folder] += 1
                continue

            if destination.exists():
                print(f"[SKIP] {path.name} -> {display_folder}/ (name already taken)")
                skipped_count += 1
                continue

            label = raw_genre if raw_genre else "<no genre tag>"

            if args.dry_run:
                print(f"[DRY-RUN] {display_folder}/ <- {path.name}  [{label}]")
            else:
                ensure_folder(root, segments, args.with_energy and placed)
                path.rename(destination)
                print(f"[MOVE] {display_folder}/ <- {path.name}  [{label}]")

            folder_counts[display_folder] += 1
            if placed:
                sorted_count += 1

        except MutagenError as e:
            error_count += 1
            print(f"[ERROR] {path.name} | MutagenError: {e}", file=sys.stderr)
        except Exception as e:
            error_count += 1
            print(f"[ERROR] {path.name} | {type(e).__name__}: {e}", file=sys.stderr)

    print()
    print("=== SORT BY GENRE END ===")
    print("-" * 60)
    verb = "Would sort" if args.dry_run else "Sorted"
    print(f"{verb} into genre folders:       {sorted_count}")
    print(f"No genre tag / catch-all tag:    {untagged_count}  -> {UNSORTED_FOLDER}/")
    print(f"Genre not in the taxonomy:       {unrecognized_count}  -> {UNSORTED_FOLDER}/")
    print(f"Skipped (name already taken):    {skipped_count}")
    print(f"Errors:                          {error_count}")

    if folder_counts:
        print()
        print("Tracks per folder:")
        for folder, count in sorted(folder_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"    {folder + '/':<40} {count}")

    if unrecognized_tags:
        print()
        print("Genre tags that aren't in the taxonomy:")
        for tag, count in sorted(unrecognized_tags.items(), key=lambda kv: (-kv[1], kv[0])):
            shown = tag if len(tag) <= 46 else tag[:43] + "..."
            print(f"    {count:>4}  {shown!r}")
        print()
        print("    Worth filing automatically? Add it to GENRE_ALIASES in")
        print("    sort_by_genre.py and re-run to sort the '00 new' folder.")

    if not args.dry_run and folder_counts and not args.with_energy:
        print()
        print("Note: the Rekordbox XML generator only reads tracks inside")
        print("      high/mid/low folders. Sort each genre folder by energy,")
        print("      or re-run with --with-energy to have them created for you.")

    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        raise SystemExit(130)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\n[ERROR] sort_by_genre failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        raise SystemExit(1)
