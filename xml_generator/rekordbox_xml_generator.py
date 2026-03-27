#!/usr/bin/env python3
"""
Rekordbox XML Generator
-----------------------

Purpose:
    Scan a structured DJ music folder and generate a Rekordbox-compatible XML
    file that recreates the folder structure as playlists.

Expected source structure:
    Root/
        Genre/
            high/
                track1.mp3
                track2.flac
            mid/
            low/

Important rules:
    - Energy folders (high/mid/low) must always be children of genre folders
    - Tracks are only processed inside energy folders
    - Files outside energy folders are ignored
    - Hidden files/folders are ignored
    - Unsupported formats are ignored
    - Nested folders inside energy folders are ignored and logged
    - Empty energy folders do not become playlists
    - The script is read-only with respect to music files

Output:
    Writes into selected root folder:
        rekordbox_export_<os>_revN.xml
        rekordbox_export_<os>_revN.log

Supported audio formats:
    .mp3, .flac, .wav, .aiff, .aif, .m4a
"""

from __future__ import annotations

import os
import platform
import re
import sys
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from urllib.parse import quote
import xml.etree.ElementTree as ET


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a"}
VALID_ENERGY_FOLDERS = {"high", "mid", "low"}


# -----------------------------
# Data models
# -----------------------------

@dataclass
class TrackEntry:
    track_id: int
    name: str
    location: str
    absolute_path: Path
    size: int
    kind: str
    artist: str
    composer: str
    album: str
    grouping: str
    genre: str
    total_time: str
    disc_number: str
    track_number: str
    year: str
    average_bpm: str
    date_added: str
    bit_rate: str
    sample_rate: str
    comments: str
    play_count: str
    rating: str
    remixer: str
    tonality: str
    label: str
    mix: str


@dataclass
class PlaylistEntry:
    library_root_name: str
    genre: str
    energy: str
    tracks: List[TrackEntry] = field(default_factory=list)

    @property
    def display_path(self) -> str:
        return f"{self.library_root_name}/{self.genre}/{self.energy}"


@dataclass
class ScanResult:
    root_path: Path
    scan_mode: str
    playlists: List[PlaylistEntry] = field(default_factory=list)
    all_tracks: List[TrackEntry] = field(default_factory=list)
    log_lines: List[str] = field(default_factory=list)


# -----------------------------
# Logging helpers
# -----------------------------

def log_info(log_lines: List[str], message: str) -> None:
    log_lines.append(f"[INFO] {message}")


def log_ok(log_lines: List[str], message: str) -> None:
    log_lines.append(f"[OK] {message}")


def log_warn(log_lines: List[str], message: str) -> None:
    log_lines.append(f"[WARN] {message}")


def log_skip(log_lines: List[str], message: str) -> None:
    log_lines.append(f"[SKIP] {message}")


# -----------------------------
# Path and environment helpers
# -----------------------------

def is_hidden(path: Path) -> bool:
    """
    Cross-platform hidden detection.
    For this tool, any path part beginning with '.' is treated as hidden.
    """
    return any(part.startswith(".") for part in path.parts)


def detect_os_label() -> str:
    system_name = platform.system().lower()
    if system_name == "windows":
        return "windows"
    if system_name == "darwin":
        return "mac"
    # Fallback for anything else; not expected for v1, but safe.
    return system_name


def prompt_for_scan_mode() -> str | None:
    while True:
        print("Choose scan mode:")
        print("1) Single sorted folder")
        print("   Example: sorted 3.25.26")
        print("2) Parent folder containing multiple sorted folders")
        print("   Example: sorted/")
        user_input = input("Enter 1 or 2 (or 'q' to quit): ").strip().lower()

        if user_input == "q":
            return None

        if user_input == "1":
            return "single"

        if user_input == "2":
            return "parent"

        print("Error: please enter 1, 2, or q.")
        print()


def prompt_for_root_folder() -> Path | None:
    while True:
        user_input = input("Enter the folder path (or 'q' to quit): ").strip()

        if user_input.lower() == "q":
            return None

        if not user_input:
            print("Error: path cannot be empty.")
            continue

        try:
            root = Path(user_input).expanduser().resolve()
        except Exception as exc:
            print(f"Error: could not resolve path. {exc}")
            continue

        if not root.exists():
            print("Error: path does not exist.")
            continue

        if not root.is_dir():
            print("Error: path is not a folder.")
            continue

        return root


def next_revision_paths(root_path: Path, os_label: str) -> tuple[Path, Path, int]:
    """
    Determine the next available revision number for:
        rekordbox_export_<os>_revN.xml
        rekordbox_export_<os>_revN.log
    """
    pattern = re.compile(
        rf"^rekordbox_export_{re.escape(os_label)}_rev(\d+)\.(xml|log)$",
        re.IGNORECASE,
    )

    max_rev = 0
    for item in root_path.iterdir():
        if not item.is_file():
            continue
        match = pattern.match(item.name)
        if match:
            rev = int(match.group(1))
            max_rev = max(max_rev, rev)

    next_rev = max_rev + 1
    xml_path = root_path / f"rekordbox_export_{os_label}_rev{next_rev}.xml"
    log_path = root_path / f"rekordbox_export_{os_label}_rev{next_rev}.log"
    return xml_path, log_path, next_rev


def path_to_file_url(path: Path) -> str:
    """
    Convert an absolute local path into a Rekordbox-friendly file URL:
        file://localhost/...

    Path must be absolute and URL-encoded.
    """
    absolute = path.resolve()
    quoted_path = quote(absolute.as_posix(), safe="/:")
    return f"file://localhost/{quoted_path.lstrip('/')}"


def build_date_added(path: Path) -> str:
    timestamp = path.stat().st_mtime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def relative_display(root_path: Path, target: Path) -> str:
    try:
        return str(target.relative_to(root_path)).replace("\\", "/")
    except ValueError:
        return str(target).replace("\\", "/")


# -----------------------------
# Folder scanning
# -----------------------------

def scan_library_root(
    library_root: Path,
    display_root: Path,
    log_lines: List[str],
    track_id_start: int,
) -> tuple[List[PlaylistEntry], List[TrackEntry], int]:
    playlists: List[PlaylistEntry] = []
    all_tracks: List[TrackEntry] = []
    track_id_counter = track_id_start

    log_info(log_lines, f"Scanning root: {library_root.name}")

    # Check for invalid root-level energy folders
    for child in sorted(library_root.iterdir(), key=lambda p: p.name.lower()):
        if is_hidden(child):
            if child.is_dir():
                log_skip(log_lines, f"Hidden folder: {child.name}")
            else:
                log_skip(log_lines, f"Hidden file: {child.name}")
            continue

        if child.is_dir() and child.name.lower() in VALID_ENERGY_FOLDERS:
            log_warn(
                log_lines,
                f"Invalid root-level energy folder ignored: {child.name}"
            )

    # Process only root-level genre folders
    for genre_dir in sorted(library_root.iterdir(), key=lambda p: p.name.lower()):
        if is_hidden(genre_dir):
            continue

        if genre_dir.is_file():
            if genre_dir.suffix.lower() in SUPPORTED_EXTENSIONS:
                log_skip(
                    log_lines,
                    f"File outside energy folder ignored: {genre_dir.name}"
                )
            else:
                log_skip(
                    log_lines,
                    f"Unsupported file at root ignored: {genre_dir.name}"
                )
            continue

        if not genre_dir.is_dir():
            continue

        if genre_dir.name.lower() in VALID_ENERGY_FOLDERS:
            # Already warned above
            continue

        genre_name = genre_dir.name

        # Warn for supported files directly inside genre folder
        for genre_child in sorted(genre_dir.iterdir(), key=lambda p: p.name.lower()):
            if is_hidden(genre_child):
                if genre_child.is_file():
                    log_skip(
                        log_lines,
                        f"Hidden file: {relative_display(display_root, genre_child)}"
                    )
                elif genre_child.is_dir():
                    log_skip(
                        log_lines,
                        f"Hidden folder: {relative_display(display_root, genre_child)}"
                    )
                continue

            if genre_child.is_file():
                if genre_child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    log_skip(
                        log_lines,
                        f"File outside energy folder ignored: {relative_display(display_root, genre_child)}"
                    )
                else:
                    log_skip(
                        log_lines,
                        f"Unsupported file: {relative_display(display_root, genre_child)}"
                    )

        # Only process high/mid/low if they exist
        for energy_name in ("high", "mid", "low"):
            energy_dir = genre_dir / energy_name
            if not energy_dir.exists():
                continue

            if is_hidden(energy_dir):
                log_skip(
                    log_lines,
                    f"Hidden folder: {relative_display(display_root, energy_dir)}"
                )
                continue

            if not energy_dir.is_dir():
                log_warn(
                    log_lines,
                    f"Expected folder but found non-folder: {relative_display(display_root, energy_dir)}"
                )
                continue

            playlist_tracks: List[TrackEntry] = []

            for item in sorted(energy_dir.iterdir(), key=lambda p: p.name.lower()):
                if is_hidden(item):
                    if item.is_file():
                        log_skip(
                            log_lines,
                            f"Hidden file: {relative_display(display_root, item)}"
                        )
                    elif item.is_dir():
                        log_skip(
                            log_lines,
                            f"Hidden folder: {relative_display(display_root, item)}"
                        )
                    continue

                if item.is_dir():
                    log_warn(
                        log_lines,
                        f"Ignored nested folder: {relative_display(display_root, item)}"
                    )
                    continue

                if not item.is_file():
                    continue

                ext = item.suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    log_skip(
                        log_lines,
                        f"Unsupported file: {relative_display(display_root, item)}"
                    )
                    continue

                track = TrackEntry(
                    track_id=track_id_counter,
                    name=item.stem,
                    location=path_to_file_url(item),
                    absolute_path=item.resolve(),
                    size=item.stat().st_size,
                    kind=item.suffix.lower().lstrip("."),
                    artist="",
                    composer="",
                    album="",
                    grouping="",
                    genre=genre_name,
                    total_time="0",
                    disc_number="0",
                    track_number="0",
                    year="0",
                    average_bpm="0",
                    date_added=build_date_added(item),
                    bit_rate="0",
                    sample_rate="0",
                    comments="",
                    play_count="0",
                    rating="0",
                    remixer="",
                    tonality="",
                    label="",
                    mix="",
                )
                track_id_counter += 1

                playlist_tracks.append(track)
                all_tracks.append(track)

            if not playlist_tracks:
                log_warn(
                    log_lines,
                    f"Empty folder: {genre_name}/{energy_name}"
                )
                continue

            playlist = PlaylistEntry(
                library_root_name=library_root.name,
                genre=genre_name,
                energy=energy_name,
                tracks=playlist_tracks,
            )
            playlists.append(playlist)
            log_ok(
                log_lines,
                f"Playlist created: {playlist.display_path} ({len(playlist.tracks)} tracks)"
            )

        # Warn about unexpected subfolders inside genre
        for genre_child in sorted(genre_dir.iterdir(), key=lambda p: p.name.lower()):
            if is_hidden(genre_child):
                continue
            if genre_child.is_dir() and genre_child.name.lower() not in VALID_ENERGY_FOLDERS:
                log_warn(
                    log_lines,
                    f"Unexpected folder inside genre ignored: {relative_display(display_root, genre_child)}"
                )

    return playlists, all_tracks, track_id_counter


def scan_music_root(root_path: Path, scan_mode: str) -> ScanResult:
    result = ScanResult(root_path=root_path, scan_mode=scan_mode)

    if scan_mode == "single":
        log_info(result.log_lines, "Scan mode: single sorted folder")
        playlists, tracks, _ = scan_library_root(
            library_root=root_path,
            display_root=root_path,
            log_lines=result.log_lines,
            track_id_start=1,
        )
        result.playlists.extend(playlists)
        result.all_tracks.extend(tracks)

    else:
        log_info(result.log_lines, "Scan mode: parent folder")
        track_id_counter = 1

        for child in sorted(root_path.iterdir(), key=lambda p: p.name.lower()):
            if is_hidden(child):
                if child.is_dir():
                    log_skip(result.log_lines, f"Hidden child folder ignored: {child.name}")
                else:
                    log_skip(result.log_lines, f"Hidden child file ignored: {child.name}")
                continue

            if child.is_file():
                log_skip(result.log_lines, f"Child file ignored: {child.name}")
                continue

            if not child.is_dir():
                continue

            log_info(result.log_lines, f"Child library root detected: {child.name}")
            child_playlists, child_tracks, track_id_counter = scan_library_root(
                library_root=child,
                display_root=child,
                log_lines=result.log_lines,
                track_id_start=track_id_counter,
            )

            if not child_playlists:
                log_warn(
                    result.log_lines,
                    f"Child folder skipped, no valid genre/energy structure: {child.name}"
                )
                continue

            result.playlists.extend(child_playlists)
            result.all_tracks.extend(child_tracks)

    log_info(result.log_lines, f"Total playlists created: {len(result.playlists)}")
    log_info(result.log_lines, f"Total tracks indexed: {len(result.all_tracks)}")
    return result


# -----------------------------
# XML generation
# -----------------------------

def build_rekordbox_xml(scan_result: ScanResult) -> ET.Element:
    """
    Build a Rekordbox-compatible XML structure.

    This uses the common Rekordbox XML layout:
    - PRODUCT
    - COLLECTION
    - PLAYLISTS / NODE tree

    Notes:
    - Track metadata is intentionally minimal and read-only.
    - Playlist folders mirror Root -> Genre -> Energy.
    """
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")

    ET.SubElement(
        root,
        "PRODUCT",
        Name="rekordbox",
        Version="7.2.11",
        Company="AlphaTheta",
    )

    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(scan_result.all_tracks)))

    for track in scan_result.all_tracks:
        ET.SubElement(
            collection,
            "TRACK",
            TrackID=str(track.track_id),
            Name=track.name,
            Artist=track.artist,
            Composer=track.composer,
            Album=track.album,
            Grouping=track.grouping,
            Genre=track.genre,
            Kind=track.kind,
            Size=str(track.size),
            TotalTime=track.total_time,
            DiscNumber=track.disc_number,
            TrackNumber=track.track_number,
            Year=track.year,
            AverageBpm=track.average_bpm,
            DateAdded=track.date_added,
            BitRate=track.bit_rate,
            SampleRate=track.sample_rate,
            Comments=track.comments,
            PlayCount=track.play_count,
            Rating=track.rating,
            Location=track.location,
            Remixer=track.remixer,
            Tonality=track.tonality,
            Label=track.label,
            Mix=track.mix,
        )

    playlists = ET.SubElement(root, "PLAYLISTS")
    rekordbox_root_node = ET.SubElement(
        playlists,
        "NODE",
        Type="0",  # folder
        Name="ROOT",
        Count="1",
    )
    selected_root_node = ET.SubElement(
        rekordbox_root_node,
        "NODE",
        Type="0",  # folder
        Name=scan_result.root_path.name,
        Count=str(
            len({playlist.library_root_name for playlist in scan_result.playlists})
            if scan_result.scan_mode == "parent"
            else len({playlist.genre for playlist in scan_result.playlists})
        ),
    )

    if scan_result.scan_mode == "single":
        library_groups = [(scan_result.root_path.name, scan_result.playlists)]
    else:
        grouped_by_library_root: dict[str, List[PlaylistEntry]] = {}
        for playlist in scan_result.playlists:
            grouped_by_library_root.setdefault(playlist.library_root_name, []).append(playlist)
        library_groups = sorted(grouped_by_library_root.items(), key=lambda item: item[0].lower())

    for library_root_name, library_playlists in library_groups:
        parent_node = selected_root_node
        if scan_result.scan_mode == "parent":
            parent_node = ET.SubElement(
                selected_root_node,
                "NODE",
                Type="0",
                Name=library_root_name,
                Count=str(len({playlist.genre for playlist in library_playlists})),
            )

        playlists_by_genre: dict[str, List[PlaylistEntry]] = {}
        for playlist in library_playlists:
            playlists_by_genre.setdefault(playlist.genre, []).append(playlist)

        for genre_name in sorted(playlists_by_genre.keys(), key=str.lower):
            genre_playlists = sorted(
                playlists_by_genre[genre_name],
                key=lambda p: ("high", "mid", "low").index(p.energy)
                if p.energy in ("high", "mid", "low")
                else 999
            )

            genre_node = ET.SubElement(
                parent_node,
                "NODE",
                Type="0",  # folder
                Name=genre_name,
                Count=str(len(genre_playlists)),
            )

            for playlist in genre_playlists:
                playlist_node = ET.SubElement(
                    genre_node,
                    "NODE",
                    Type="1",  # playlist
                    Name=playlist.energy,
                    KeyType="0",
                    Entries=str(len(playlist.tracks)),
                )

                for track in playlist.tracks:
                    ET.SubElement(
                        playlist_node,
                        "TRACK",
                        Key=str(track.track_id),
                    )

    return root


def prettify_xml(element: ET.Element) -> str:
    tree = ET.ElementTree(element)
    ET.indent(tree, space="  ")
    xml_body = ET.tostring(element, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}\n'


# -----------------------------
# File writing
# -----------------------------

def write_text_file(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def build_log_text(scan_result: ScanResult, xml_path: Path, log_path: Path) -> str:
    lines: List[str] = []
    lines.extend(scan_result.log_lines)
    lines.append("")
    lines.append(f"[INFO] XML written: {xml_path.name}")
    lines.append(f"[INFO] Log written: {log_path.name}")
    return "\n".join(lines) + "\n"


# -----------------------------
# Main program
# -----------------------------

def main() -> int:
    print("Rekordbox XML Generator")
    print("-----------------------")
    print("Supports:")
    print("  1. Single sorted folder")
    print("  2. Parent folder containing multiple sorted folders")
    print()

    scan_mode = prompt_for_scan_mode()
    if scan_mode is None:
        print("Quit.")
        return 0

    print()
    root_path = prompt_for_root_folder()
    if root_path is None:
        print("Quit.")
        return 0

    os_label = detect_os_label()
    xml_path, log_path, revision = next_revision_paths(root_path, os_label)

    scan_result = scan_music_root(root_path, scan_mode=scan_mode)
    xml_root = build_rekordbox_xml(scan_result)
    xml_text = prettify_xml(xml_root)
    log_text = build_log_text(scan_result, xml_path, log_path)

    # Write outputs
    write_text_file(xml_path, xml_text)
    write_text_file(log_path, log_text)

    print()
    print("Done.")
    print(f"Scan mode:        {scan_mode}")
    print(f"Root folder:      {root_path}")
    print(f"Detected OS:      {os_label}")
    print(f"Revision:         rev{revision}")
    print(f"Playlists made:   {len(scan_result.playlists)}")
    print(f"Tracks indexed:   {len(scan_result.all_tracks)}")
    print(f"XML file:         {xml_path.name}")
    print(f"Log file:         {log_path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
