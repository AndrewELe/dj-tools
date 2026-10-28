#!/usr/bin/env python3
"""
Rekordbox XML Generator (genre folders)
---------------------------------------

Purpose:
    Scan a genre-sorted music folder and generate a Rekordbox-compatible XML
    file that recreates the folder structure as playlists.

    This is the companion to xml_generator/rekordbox_xml_generator.py. That one
    expects the dated crate tree, where every track lives in an energy folder:

        sorted 3.25.26/
            techno/
                high/  mid/  low/

    This one expects the layout sort_by_genre.py produces, where tracks live
    directly in their genre folder and energy sorting hasn't happened yet:

        All Music/
            dnb/                        <- 137 tracks
            techno/                     <- 42 tracks
            house/                      <- 72 tracks of its own, AND:
                deep house/             <- 22 tracks
                tech house/             <- 11 tracks
                melodic house, techno/  <- 68 tracks
            to organize/

Rules:
    - Any folder holding audio files becomes a playlist.
    - Any folder holding subfolders becomes a playlist folder.
    - A folder that has both (like house/ above) becomes a folder containing a
      playlist of its own tracks, named after itself, plus its subfolders.
      Rekordbox folders can't hold tracks directly, so those 72 house tracks
      would otherwise be dropped.
    - Nesting is unlimited, so pointing this at a parent folder holding several
      sorted libraries works without a separate mode.
    - high/mid/low folders are ordered by energy rather than alphabetically, so
      a part-sorted library still reads correctly.
    - Folders with no audio anywhere beneath them are skipped.
    - Hidden files/folders and unsupported formats are ignored.
    - The script is read-only with respect to music files.

Output:
    Writes into the selected root folder:
        rekordbox_genre_export_<os>_revN.xml
        rekordbox_genre_export_<os>_revN.log

    The filename prefix differs from rekordbox_xml_generator.py so the two
    tools never overwrite each other's exports or share a revision counter.

Supported audio formats:
    .mp3, .flac, .wav, .aiff, .aif, .m4a
"""

from __future__ import annotations

import platform
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote
import xml.etree.ElementTree as ET


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a"}

# Energy folders sort in DJ order rather than alphabetically, so a genre that
# has been part-sorted reads high, mid, low instead of high, low, mid.
ENERGY_ORDER = {"high": 0, "mid": 1, "low": 2}


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
class FolderNode:
    """
    One folder in the library, mirrored as a Rekordbox playlist or folder.

    tracks   - audio files sitting directly in this folder
    children - subfolders that contain audio somewhere beneath them
    """
    name: str
    path: Path
    genre_path: List[str]
    tracks: List[TrackEntry] = field(default_factory=list)
    children: List["FolderNode"] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def total_tracks(self) -> int:
        return len(self.tracks) + sum(child.total_tracks for child in self.children)

    @property
    def display_path(self) -> str:
        return "/".join(self.genre_path) if self.genre_path else self.name


@dataclass
class ScanResult:
    root_path: Path
    tree: Optional[FolderNode] = None
    all_tracks: List[TrackEntry] = field(default_factory=list)
    log_lines: List[str] = field(default_factory=list)

    @property
    def playlist_count(self) -> int:
        """Number of NODE Type=1 playlists the XML will contain."""
        if self.tree is None:
            return 0
        return count_playlists(self.tree)


def count_playlists(node: FolderNode) -> int:
    # A leaf with tracks is one playlist. A folder with its own tracks emits an
    # extra playlist for them alongside its children.
    total = 1 if node.tracks else 0
    for child in node.children:
        total += count_playlists(child)
    return total


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
    return system_name


def prompt_for_root_folder() -> Optional[Path]:
    while True:
        user_input = input(
            "Enter the folder path (or Q to return to menu): "
        ).strip().strip('"').strip("'")

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
        rekordbox_genre_export_<os>_revN.xml
        rekordbox_genre_export_<os>_revN.log
    """
    pattern = re.compile(
        rf"^rekordbox_genre_export_{re.escape(os_label)}_rev(\d+)\.(xml|log)$",
        re.IGNORECASE,
    )

    max_rev = 0
    for item in root_path.iterdir():
        if not item.is_file():
            continue
        match = pattern.match(item.name)
        if match:
            max_rev = max(max_rev, int(match.group(1)))

    next_rev = max_rev + 1
    xml_path = root_path / f"rekordbox_genre_export_{os_label}_rev{next_rev}.xml"
    log_path = root_path / f"rekordbox_genre_export_{os_label}_rev{next_rev}.log"
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


def child_sort_key(path: Path) -> tuple[int, str]:
    return (ENERGY_ORDER.get(path.name.lower(), 99), path.name.lower())


# -----------------------------
# Folder scanning
# -----------------------------

def build_track(
    item: Path,
    genre_path: List[str],
    track_id: int,
) -> TrackEntry:
    """
    Build a minimal, read-only track entry.

    Metadata is deliberately sparse, matching rekordbox_xml_generator.py:
    Rekordbox reads the real tags off the file during import and analysis, so
    anything guessed here would just be overwritten or, worse, wrong.
    """
    return TrackEntry(
        track_id=track_id,
        name=item.stem,
        location=path_to_file_url(item),
        absolute_path=item.resolve(),
        size=item.stat().st_size,
        kind=item.suffix.lower().lstrip("."),
        artist="",
        composer="",
        album="",
        grouping="",
        genre="/".join(genre_path),
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


def scan_folder(
    folder: Path,
    genre_path: List[str],
    display_root: Path,
    log_lines: List[str],
    track_id_counter: int,
) -> tuple[Optional[FolderNode], int]:
    """
    Recursively mirror a folder into a FolderNode.

    Returns (node, updated_track_id_counter). node is None when the folder holds
    no audio anywhere beneath it, so empty branches never reach the XML.
    """
    tracks: List[TrackEntry] = []
    children: List[FolderNode] = []

    entries = sorted(folder.iterdir(), key=child_sort_key)

    for item in entries:
        if is_hidden(item):
            kind = "folder" if item.is_dir() else "file"
            log_skip(log_lines, f"Hidden {kind}: {relative_display(display_root, item)}")
            continue

        if item.is_file():
            if item.suffix.lower() not in SUPPORTED_EXTENSIONS:
                log_skip(log_lines, f"Unsupported file: {relative_display(display_root, item)}")
                continue

            tracks.append(build_track(item, genre_path, track_id_counter))
            track_id_counter += 1
            continue

        if not item.is_dir():
            continue

        child_node, track_id_counter = scan_folder(
            folder=item,
            genre_path=genre_path + [item.name],
            display_root=display_root,
            log_lines=log_lines,
            track_id_counter=track_id_counter,
        )

        if child_node is None:
            log_warn(log_lines, f"Empty folder: {relative_display(display_root, item)}")
            continue

        children.append(child_node)

    if not tracks and not children:
        return None, track_id_counter

    node = FolderNode(
        name=folder.name,
        path=folder,
        genre_path=list(genre_path),
        tracks=tracks,
        children=children,
    )

    if tracks:
        log_ok(
            log_lines,
            f"Playlist created: {node.display_path or folder.name} ({len(tracks)} tracks)",
        )

    return node, track_id_counter


def collect_tracks(node: FolderNode, out: List[TrackEntry]) -> None:
    out.extend(node.tracks)
    for child in node.children:
        collect_tracks(child, out)


def scan_music_root(root_path: Path) -> ScanResult:
    result = ScanResult(root_path=root_path)

    log_info(result.log_lines, f"Scanning root: {root_path}")

    tree, _ = scan_folder(
        folder=root_path,
        genre_path=[],
        display_root=root_path,
        log_lines=result.log_lines,
        track_id_counter=1,
    )

    result.tree = tree

    if tree is None:
        log_warn(result.log_lines, "No audio files found anywhere under this folder.")
    else:
        collect_tracks(tree, result.all_tracks)

    log_info(result.log_lines, f"Total playlists created: {result.playlist_count}")
    log_info(result.log_lines, f"Total tracks indexed: {len(result.all_tracks)}")
    return result


# -----------------------------
# XML generation
# -----------------------------

def add_playlist_node(parent_xml_node: ET.Element, name: str, tracks: List[TrackEntry]) -> None:
    playlist_node = ET.SubElement(
        parent_xml_node,
        "NODE",
        Type="1",  # playlist
        Name=name,
        KeyType="0",
        Entries=str(len(tracks)),
    )
    for track in tracks:
        ET.SubElement(playlist_node, "TRACK", Key=str(track.track_id))


def emit_node(node: FolderNode, parent_xml_node: ET.Element) -> None:
    """
    Write one folder into the playlist tree.

    A folder with no subfolders becomes a plain playlist. A folder with
    subfolders becomes a folder node; if it also holds tracks of its own, those
    go into a playlist named after the folder, because a Rekordbox folder node
    cannot contain tracks directly.
    """
    if node.is_leaf:
        add_playlist_node(parent_xml_node, node.name, node.tracks)
        return

    child_count = len(node.children) + (1 if node.tracks else 0)
    folder_node = ET.SubElement(
        parent_xml_node,
        "NODE",
        Type="0",  # folder
        Name=node.name,
        Count=str(child_count),
    )

    if node.tracks:
        add_playlist_node(folder_node, node.name, node.tracks)

    for child in node.children:
        emit_node(child, folder_node)


def build_rekordbox_xml(scan_result: ScanResult) -> ET.Element:
    """
    Build a Rekordbox-compatible XML structure.

    Layout:
    - PRODUCT
    - COLLECTION
    - PLAYLISTS / NODE tree mirroring Root -> Genre[/SubGenre...]
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

    playlists_elem = ET.SubElement(root, "PLAYLISTS")
    rekordbox_root_node = ET.SubElement(
        playlists_elem,
        "NODE",
        Type="0",  # folder
        Name="ROOT",
        Count="1",
    )

    tree = scan_result.tree
    if tree is None:
        ET.SubElement(
            rekordbox_root_node,
            "NODE",
            Type="0",
            Name=scan_result.root_path.name,
            Count="0",
        )
        return root

    # The selected folder becomes the top node, so its own name is preserved in
    # Rekordbox rather than dumping genres at the root of the playlist tree.
    child_count = len(tree.children) + (1 if tree.tracks else 0)
    library_node = ET.SubElement(
        rekordbox_root_node,
        "NODE",
        Type="0",  # folder
        Name=scan_result.root_path.name,
        Count=str(child_count),
    )

    # Loose tracks sitting in the root, e.g. a library that hasn't been fully
    # sorted yet, still get a playlist instead of vanishing.
    if tree.tracks:
        add_playlist_node(library_node, scan_result.root_path.name, tree.tracks)

    for child in tree.children:
        emit_node(child, library_node)

    return root


def prettify_xml(element: ET.Element) -> str:
    tree = ET.ElementTree(element)
    ET.indent(tree, space="  ")
    xml_body = ET.tostring(element, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}\n'


# -----------------------------
# Console preview
# -----------------------------

def print_tree(node: FolderNode, indent: str = "", is_root: bool = False) -> None:
    if is_root:
        own = f"  [{len(node.tracks)} tracks]" if node.tracks else ""
        print(f"{node.name}/{own}")
    for child in node.children:
        if child.is_leaf:
            print(f"{indent}    {child.name}  [{len(child.tracks)} tracks]")
        else:
            own = f"  [+{len(child.tracks)} of its own]" if child.tracks else ""
            print(f"{indent}    {child.name}/  ({child.total_tracks} tracks){own}")
            print_tree(child, indent + "    ")


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
    print("Rekordbox XML Generator (genre folders)")
    print("---------------------------------------")
    print("For libraries where tracks live directly in their genre folder,")
    print("the layout sort_by_genre.py creates. Every folder holding audio")
    print("becomes a playlist, and nesting is mirrored as playlist folders.")
    print()
    print("For the dated crate tree with high/mid/low energy folders, use")
    print("xml_generator/rekordbox_xml_generator.py instead.")
    print()

    if len(sys.argv) > 1:
        raw = sys.argv[1].strip().strip('"').strip("'")
        root_path = Path(raw).expanduser()
        if not root_path.exists() or not root_path.is_dir():
            print(f"Error: not a folder: {root_path}", file=sys.stderr)
            return 2
        root_path = root_path.resolve()
    else:
        prompted = prompt_for_root_folder()
        if prompted is None:
            print("Quit.")
            return 0
        root_path = prompted

    os_label = detect_os_label()
    xml_path, log_path, revision = next_revision_paths(root_path, os_label)

    scan_result = scan_music_root(root_path)

    if scan_result.tree is None:
        print()
        print(f"No audio files found anywhere under {root_path}.")
        print("Nothing to export.")
        return 1

    xml_root = build_rekordbox_xml(scan_result)
    xml_text = prettify_xml(xml_root)
    log_text = build_log_text(scan_result, xml_path, log_path)

    write_text_file(xml_path, xml_text)
    write_text_file(log_path, log_text)

    print()
    print("Playlist tree:")
    print_tree(scan_result.tree, is_root=True)

    print()
    print("Done.")
    print(f"Root folder:      {root_path}")
    print(f"Detected OS:      {os_label}")
    print(f"Revision:         rev{revision}")
    print(f"Playlists made:   {scan_result.playlist_count}")
    print(f"Tracks indexed:   {len(scan_result.all_tracks)}")
    print(f"XML file:         {xml_path.name}")
    print(f"Log file:         {log_path.name}")
    print()
    print("In Rekordbox: File > Import Playlist / Import Collection, then")
    print("pick the XML above. Tracks import with their real tags intact.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(
            f"\n[ERROR] Rekordbox genre XML generator failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        import traceback
        traceback.print_exc()
        sys.exit(1)
