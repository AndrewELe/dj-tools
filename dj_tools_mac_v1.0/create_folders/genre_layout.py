"""
The genre folder layout the whole toolkit builds and reads.

    00 new/                 <- inbox for tracks that aren't filed yet
    01 downtempo, organic/
        high/  mid/  low/
    02 afro house/
        high/  mid/  low/
    ...
    21 other/
        high/  mid/  low/

Genres sit at the top level, one click from the root of the USB, and are
numbered slowest to fastest so browsing them on the CDJs follows how a set
builds. The numbers come from the order of GENRES below, so to add, remove or
move a genre, edit that list and nothing else. Then run "Build / update genre
folders" from the menu, which renumbers existing folders to match.
"""

from __future__ import annotations

import re


ENERGY_LEVELS = ["high", "mid", "low"]

# Inbox for new downloads and anything sort_by_genre.py can't place. Numbered
# 00 so it stays at the top of the list.
NEW_FOLDER = "00 new"

# Slowest to fastest. Folder numbers are assigned from this order.
GENRES = [
    "downtempo, organic",
    "afro house",
    "deep house",
    "melodic house",
    "prog house",
    "house",
    "tech house",
    "minimal, deep tech",
    "breaks",
    "techno",
    "prog trance",
    "trance",
    "ukg, bass house",
    "dubstep",
    "trap",
    "hard techno",
    "hard dance",
    "hardstyle",
    "dnb",
    "happy hardcore",
    "other",
]

# "techno" -> "10 techno"
GENRE_FOLDERS: dict[str, str] = {
    genre: f"{number:02d} {genre}" for number, genre in enumerate(GENRES, start=1)
}

# Suffix clean_empty_music_folders.py adds to template folders with no music.
EMPTY_SUFFIX = " (empty)"

_NUMBERED_RE = re.compile(r"^\d{2} (.+)$")


def strip_empty_suffix(name: str) -> str:
    return name[: -len(EMPTY_SUFFIX)] if name.endswith(EMPTY_SUFFIX) else name


def genre_from_folder_name(name: str) -> str | None:
    """
    Return the genre a numbered folder holds, whatever its number.

    "10 techno" -> "techno", and so does "11 techno" left over from an older
    numbering, or "10 techno (empty)". Anything else returns None.
    """
    match = _NUMBERED_RE.match(strip_empty_suffix(name))
    if match and match.group(1) in GENRE_FOLDERS:
        return match.group(1)
    return None
