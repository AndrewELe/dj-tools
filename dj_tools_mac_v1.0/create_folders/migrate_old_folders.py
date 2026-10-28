"""
Move tracks from the old folder layouts into the numbered genre library.

Handles two kinds of old folder:

  1. Dated crate trees from the old "Build new dated crate tree":
         sorted 10.20.26/house/deep house/high/track.mp3
             -> 03 deep house/high/track.mp3
     The same layout sort_by_genre.py used to make (house/deep house/...,
     to organize/) is handled too.

  2. Genre folders from an older numbering, after GENRES in genre_layout.py
     has been edited:
         13 trance/high/track.mp3  ->  12 trance/high/track.mp3

Energy folders and anything below them are kept as they are. A track whose
name is already taken at the destination is left where it is and reported.
Tracks with no clear new home (tracks filed straight into progressive/, or
folders this doesn't recognise) are left where they are and reported.
Folders emptied by the move are removed.

Usage:
    py migrate_old_folders.py <folder holding the old folders> [library folder]

The library folder defaults to the first folder. Nothing moves until you
confirm the preview.
"""

from __future__ import annotations

import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from genre_layout import (
    EMPTY_SUFFIX,
    GENRE_FOLDERS,
    NEW_FOLDER,
    genre_from_folder_name,
    strip_empty_suffix,
)


AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".aiff",
    ".aif",
    ".m4a",
    ".aac",
    ".ogg",
}

# Old top-level genre folder -> new genre. None means there's no single new
# home: tracks filed straight into progressive/ could be house or trance.
LEGACY_GENRES: dict[str, str | None] = {
    "afro house": "afro house",
    "breaks": "breaks",
    "dnb": "dnb",
    "dubstep": "dubstep",
    "happy hardcore, jumpcore": "happy hardcore",
    "minimal, deep tech": "minimal, deep tech",
    "organic house, downtempo": "downtempo, organic",
    "techno": "techno",
    "trance": "trance",
    "trap": "trap",
    "uk bass": "ukg, bass house",
    "other": "other",
    "house": "house",
    "hardstyle": "hardstyle",
    "progressive": None,
}

LEGACY_SUBGENRES: dict[tuple[str, str], str] = {
    ("house", "deep house"): "deep house",
    ("house", "tech house"): "tech house",
    ("house", "melodic house, techno"): "melodic house",
    ("hardstyle", "hard dance"): "hard dance",
    ("hardstyle", "hard techno"): "hard techno",
    ("progressive", "progressive house"): "prog house",
    ("progressive", "progressive trance"): "prog trance",
}

# sort_by_genre.py's old inbox, now NEW_FOLDER.
LEGACY_INBOX = "to organize"


@dataclass
class Move:
    source: Path
    destination: Path


@dataclass
class Plan:
    moves: list[Move] = field(default_factory=list)
    conflicts: list[Move] = field(default_factory=list)
    left_behind: list[Path] = field(default_factory=list)
    # Folders to remove once the moves have emptied them.
    tidy_roots: list[Path] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.moves or self.conflicts or self.left_behind)


def normalize_input_path(raw_input: str) -> str:
    return raw_input.strip().strip('"').strip("'")


def is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS and not is_hidden(path)


def audio_files_under(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if is_audio(p))


def child_dirs(folder: Path) -> list[Path]:
    return sorted(
        (p for p in folder.iterdir() if p.is_dir() and not is_hidden(p)),
        key=lambda p: p.name.lower(),
    )


def is_legacy_folder_name(name: str) -> bool:
    name = strip_empty_suffix(name)
    return name in LEGACY_GENRES or name == LEGACY_INBOX


def is_old_crate(folder: Path) -> bool:
    return any(is_legacy_folder_name(child.name) for child in child_dirs(folder))


def is_current_folder_name(name: str) -> bool:
    return strip_empty_suffix(name) == NEW_FOLDER or genre_from_folder_name(name) is not None


def find_old_crates(source: Path) -> list[Path]:
    crates: list[Path] = []
    if is_old_crate(source):
        crates.append(source)

    for child in child_dirs(source):
        if is_legacy_folder_name(child.name) or is_current_folder_name(child.name):
            continue
        if is_old_crate(child):
            crates.append(child)

    return crates


def clean_dir_parts(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Drop " (empty)" from folder names, leaving the filename untouched."""
    return tuple(strip_empty_suffix(p) for p in parts[:-1]) + parts[-1:]


def legacy_destination(top_name: str, rel_parts: tuple[str, ...]) -> tuple[str, tuple[str, ...]] | None:
    """
    Work out where a track in an old genre folder goes.

    top_name  - the old top-level folder, e.g. "house"
    rel_parts - the track's path below it, e.g. ("deep house", "high", "x.mp3")

    Returns (new top-level folder, path below it), or None if there's no home.
    """
    if top_name == LEGACY_INBOX:
        return NEW_FOLDER, rel_parts

    if len(rel_parts) > 1:
        subgenre = LEGACY_SUBGENRES.get((top_name, strip_empty_suffix(rel_parts[0])))
        if subgenre is not None:
            return GENRE_FOLDERS[subgenre], rel_parts[1:]

    genre = LEGACY_GENRES.get(top_name)
    if genre is None:
        return None
    return GENRE_FOLDERS[genre], rel_parts


def plan_migration(source: Path, library: Path) -> Plan:
    plan = Plan()
    planned: set[Path] = set()

    def add_move(track: Path, destination: Path) -> None:
        move = Move(track, destination)
        if destination.exists() or destination in planned:
            plan.conflicts.append(move)
        else:
            planned.add(destination)
            plan.moves.append(move)

    for crate in find_old_crates(source):
        # When the library is this folder or sits inside it, only the old genre
        # folders are touched. Tidying the whole thing would take the library's
        # empty template folders with it.
        crate_is_library = crate == library or crate in library.parents

        if crate_is_library:
            plan.tidy_roots.extend(
                child for child in child_dirs(crate) if is_legacy_folder_name(child.name)
            )
        else:
            plan.tidy_roots.append(crate)
            plan.left_behind.extend(p for p in crate.iterdir() if is_audio(p))

        for top in child_dirs(crate):
            top_name = strip_empty_suffix(top.name)

            if not is_legacy_folder_name(top_name):
                # The library's own folders, or something we don't recognise.
                # Only worth reporting inside an old crate.
                if not crate_is_library:
                    plan.left_behind.extend(audio_files_under(top))
                continue

            for track in audio_files_under(top):
                rel_parts = clean_dir_parts(track.relative_to(top).parts)
                target = legacy_destination(top_name, rel_parts)
                if target is None:
                    plan.left_behind.append(track)
                    continue
                new_top, below = target
                add_move(track, library / new_top / Path(*below))

    # Genre folders whose number no longer matches GENRES.
    for child in child_dirs(library):
        genre = genre_from_folder_name(child.name)
        if genre is None or strip_empty_suffix(child.name) == GENRE_FOLDERS[genre]:
            continue
        plan.tidy_roots.append(child)
        for track in audio_files_under(child):
            rel_parts = clean_dir_parts(track.relative_to(child).parts)
            add_move(track, library / GENRE_FOLDERS[genre] / Path(*rel_parts))

    return plan


def relative_to_either(path: Path, *roots: Path) -> Path:
    for root in roots:
        try:
            return path.relative_to(root)
        except ValueError:
            continue
    return path


def print_plan(plan: Plan, source: Path, library: Path) -> None:
    if plan.moves:
        print("\nTracks to move:\n")
        groups: Counter[tuple[Path, Path]] = Counter()
        for move in plan.moves:
            groups[(
                relative_to_either(move.source.parent, source, library),
                relative_to_either(move.destination.parent, library),
            )] += 1
        for (from_dir, to_dir), count in sorted(groups.items(), key=lambda kv: str(kv[0][0]).lower()):
            print(f"  {count:>5}  {from_dir}  ->  {to_dir}")

    if plan.conflicts:
        print("\nAlready at the destination, left where they are:\n")
        for move in plan.conflicts:
            print(f"  {relative_to_either(move.source, source, library)}")

    if plan.left_behind:
        print("\nNo clear new home, left where they are (move these by hand):\n")
        groups_left: Counter[Path] = Counter(
            relative_to_either(p.parent, source, library) for p in plan.left_behind
        )
        for folder, count in sorted(groups_left.items(), key=lambda kv: str(kv[0]).lower()):
            print(f"  {count:>5}  {folder}")

    print("\nSummary:")
    print(f"Move:          {len(plan.moves)}")
    print(f"Already there: {len(plan.conflicts)}")
    print(f"No new home:   {len(plan.left_behind)}")


def unmark_empty(library: Path, folder: Path) -> None:
    """
    Make sure folder exists, reusing any " (empty)" copy of it or its parents.

    clean_empty_music_folders.py renames template folders with no music to
    "x (empty)". Moving a track in means they aren't empty any more.
    """
    current = library
    for part in folder.relative_to(library).parts:
        plain = current / part
        marked = current / f"{part}{EMPTY_SUFFIX}"
        if not plain.exists() and marked.is_dir():
            marked.rename(plain)
        current = plain
    folder.mkdir(parents=True, exist_ok=True)


def remove_empty_dirs(root: Path) -> int:
    if not root.is_dir():
        return 0

    removed = 0
    folders = sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
    for folder in folders + [root]:
        try:
            folder.rmdir()
            removed += 1
        except OSError:
            pass  # not empty
    return removed


def apply_plan(plan: Plan, library: Path) -> dict[str, int]:
    results = {"moved": 0, "errors": 0, "folders_removed": 0}

    for move in plan.moves:
        try:
            unmark_empty(library, move.destination.parent)
            shutil.move(str(move.source), str(move.destination))
            results["moved"] += 1
        except OSError as e:
            print(f"[ERROR] {move.source} | {e}")
            results["errors"] += 1

    for root in plan.tidy_roots:
        results["folders_removed"] += remove_empty_dirs(root)

    return results


def run(source: Path, library: Path) -> None:
    """Preview, confirm and apply. Shared with make_music_paths.py."""
    plan = plan_migration(source, library)
    if plan.is_empty():
        print("\nNo tracks found in the old folder layout. Nothing to move.")
        return

    print_plan(plan, source, library)

    if not plan.moves:
        print("\nNothing can be moved automatically.")
        return

    confirm = input("\nMove these tracks now? (y/n): ").strip().lower()
    if confirm != "y":
        print("\nCancelled. Nothing was moved.")
        return

    print("\nMoving...")
    results = apply_plan(plan, library)
    print("\nDone.")
    print(f"Moved:                 {results['moved']}")
    print(f"Errors:                {results['errors']}")
    print(f"Empty folders removed: {results['folders_removed']}")


def prompt_for_folder(prompt: str) -> Path | None:
    raw = normalize_input_path(input(prompt))
    if raw.lower() == "q" or not raw:
        return None
    return Path(raw)


def main() -> None:
    if len(sys.argv) > 1:
        source = Path(normalize_input_path(sys.argv[1]))
    else:
        source = prompt_for_folder("Enter the folder holding your old folders (or Q to return to menu): ")
        if source is None:
            print("Returning to menu.")
            return

    if len(sys.argv) > 2:
        library = Path(normalize_input_path(sys.argv[2]))
    else:
        library = source

    for path in (source, library):
        if not path.is_dir():
            print(f"Error: not a folder: {path}")
            sys.exit(1)

    run(source.resolve(), library.resolve())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] migrate_old_folders failed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
