#!/usr/bin/env python3
"""
Camelot converter for DJ tracks.

Features:
- Recursively scans a music folder
- Supports MP3, FLAC, MP4/M4A, AIFF/AIF
- Reads common key metadata fields
- Converts standard musical keys to Camelot notation
- Pulls BPM from metadata for optional filename rewriting
- Dry-run by default
- Optionally writes Camelot into comments, grouping, or a custom field
- Handles enharmonic spellings (C# / Db, etc.)
- Skips missing/invalid keys
- Prints summary report
- Optional file renaming with Camelot + key first, and BPM only when available
- Updates the track title tag so Camelot + key appear before the title in DJ software

Default rename behavior:
- With BPM:
    9A | Em | 174 - Artist - Title
- Without BPM:
    9A | Em - Artist - Title

Recommended first use:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --verbose

Actually write changes:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --write --verbose

Write + rename:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --write --rename --verbose
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from mutagen import File
from mutagen import MutagenError
from mutagen.aiff import AIFF
from mutagen.flac import FLAC
from mutagen.id3 import COMM, ID3, TIT1, TIT2, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4FreeForm


SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".mp4",
    ".m4a",
    ".aif",
    ".aiff",
}

INVALID_FILENAME_CHARS = r'<>:"/\\|?*'

# Canonical pitch classes with enharmonics
NOTE_ALIASES = {
    "C": "C",
    "B#": "C",
    "C#": "C#",
    "DB": "C#",
    "D♭": "C#",
    "D": "D",
    "D#": "D#",
    "EB": "D#",
    "E♭": "D#",
    "E": "E",
    "FB": "E",
    "F": "F",
    "E#": "F",
    "F#": "F#",
    "GB": "F#",
    "G♭": "F#",
    "G": "G",
    "G#": "G#",
    "AB": "G#",
    "A♭": "G#",
    "A": "A",
    "A#": "A#",
    "BB": "A#",
    "B♭": "A#",
    "B": "B",
    "CB": "B",
}

# 24-key Camelot map using canonical sharps internally
CAMELOT_MAP = {
    ("G#", "minor"): "1A",
    ("B", "major"): "1B",
    ("D#", "minor"): "2A",
    ("F#", "major"): "2B",
    ("A#", "minor"): "3A",
    ("C#", "major"): "3B",
    ("F", "minor"): "4A",
    ("G#", "major"): "4B",
    ("C", "minor"): "5A",
    ("D#", "major"): "5B",
    ("G", "minor"): "6A",
    ("A#", "major"): "6B",
    ("D", "minor"): "7A",
    ("F", "major"): "7B",
    ("A", "minor"): "8A",
    ("C", "major"): "8B",
    ("E", "minor"): "9A",
    ("G", "major"): "9B",
    ("B", "minor"): "10A",
    ("D", "major"): "10B",
    ("F#", "minor"): "11A",
    ("A", "major"): "11B",
    ("C#", "minor"): "12A",
    ("E", "major"): "12B",
}

DISPLAY_EQUIVALENTS = {
    ("G#", "minor"): "G#m / Abm",
    ("B", "major"): "B",
    ("D#", "minor"): "D#m / Ebm",
    ("F#", "major"): "F# / Gb",
    ("A#", "minor"): "A#m / Bbm",
    ("C#", "major"): "C# / Db",
    ("F", "minor"): "Fm",
    ("G#", "major"): "G# / Ab",
    ("C", "minor"): "Cm",
    ("D#", "major"): "D# / Eb",
    ("G", "minor"): "Gm",
    ("A#", "major"): "A# / Bb",
    ("D", "minor"): "Dm",
    ("F", "major"): "F",
    ("A", "minor"): "Am",
    ("C", "major"): "C",
    ("E", "minor"): "Em",
    ("G", "major"): "G",
    ("B", "minor"): "Bm",
    ("D", "major"): "D",
    ("F#", "minor"): "F#m / Gbm",
    ("A", "major"): "A",
    ("C#", "minor"): "C#m / Dbm",
    ("E", "major"): "E",
}


@dataclass
class Stats:
    scanned: int = 0
    supported: int = 0
    missing_key: int = 0
    invalid_key: int = 0
    unchanged: int = 0
    would_write: int = 0
    written: int = 0
    renamed: int = 0
    errors: int = 0


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def clean_key_string(raw: str) -> str:
    s = raw.strip()
    s = s.replace("♯", "#").replace("♭", "b")
    s = s.replace("-", " ").replace("_", " ")
    s = normalize_whitespace(s)
    return s


def normalize_note(note: str) -> Optional[str]:
    note = note.strip().replace("♯", "#").replace("♭", "b").upper()
    return NOTE_ALIASES.get(note)


def normalize_field_name(name: str) -> str:
    return re.sub(r"[\s_\-:]+", "", name.strip().upper())


def strip_key_label(raw: str) -> str:
    return re.sub(r"^(INITIAL\s+KEY|INITIALKEY|KEY)\s*:?\s*", "", raw.strip(), flags=re.IGNORECASE)


def parse_key(raw: str) -> Optional[tuple[str, str]]:
    """
    Convert raw text like:
      Am, A minor, C#m, Db, Ebm, F#, G major
    into canonical tuple:
      ("A", "minor"), ("C#", "minor"), ("D#", "major"), etc.
    """
    if not raw:
        return None

    normalized_raw = strip_key_label(raw)
    s = clean_key_string(normalized_raw)
    upper = s.upper()
    upper = normalize_whitespace(upper).strip()

    m = re.fullmatch(r"([A-G])([#B]?)(M)?", upper)
    if m:
        note = m.group(1) + (m.group(2) or "")
        suffix = m.group(3)

        orig = clean_key_string(normalized_raw).strip()
        if orig.lower().endswith("m") and not orig.lower().endswith("maj"):
            mode = "minor"
        else:
            mode = "major"

        note = normalize_note(note)
        return (note, mode) if note else None

    m = re.fullmatch(r"([A-G])([#B]?)[ ]*(MINOR|MIN|M)", upper)
    if m:
        note = normalize_note(m.group(1) + (m.group(2) or ""))
        return (note, "minor") if note else None

    m = re.fullmatch(r"([A-G])([#B]?)[ ]*(MAJOR|MAJ)", upper)
    if m:
        note = normalize_note(m.group(1) + (m.group(2) or ""))
        return (note, "major") if note else None

    orig = clean_key_string(normalized_raw)
    orig_lower = orig.lower()

    m = re.fullmatch(r"([A-Ga-g])([#b♭♯]?)(m)", orig.strip())
    if m:
        note = normalize_note((m.group(1) + (m.group(2) or "")).upper())
        return (note, "minor") if note else None

    m = re.fullmatch(r"([A-Ga-g])([#b♭♯]?)", orig.strip())
    if m:
        note = normalize_note((m.group(1) + (m.group(2) or "")).upper())
        return (note, "major") if note else None

    m = re.fullmatch(r"([A-Ga-g])([#b♭♯]?)[ ]*(minor|min)", orig_lower)
    if m:
        note = normalize_note((m.group(1) + (m.group(2) or "")).upper())
        return (note, "minor") if note else None

    m = re.fullmatch(r"([A-Ga-g])([#b♭♯]?)[ ]*(major|maj)", orig_lower)
    if m:
        note = normalize_note((m.group(1) + (m.group(2) or "")).upper())
        return (note, "major") if note else None

    return None


def to_camelot(key_tuple: tuple[str, str]) -> Optional[str]:
    return CAMELOT_MAP.get(key_tuple)


def decode_value(v: Any) -> list[str]:
    out: list[str] = []
    if v is None:
        return out

    if isinstance(v, list):
        for item in v:
            out.extend(decode_value(item))
        return out

    if isinstance(v, tuple):
        for item in v:
            out.extend(decode_value(item))
        return out

    if isinstance(v, bytes):
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                out.append(v.decode(encoding).strip("\x00").strip())
                return out
            except Exception:
                continue
        out.append(repr(v))
        return out

    if hasattr(v, "text"):
        try:
            text_value = v.text
            if isinstance(text_value, (str, bytes)):
                return decode_value(text_value)
            return [str(x).strip() for x in text_value if str(x).strip()]
        except Exception:
            pass

    s = str(v).strip()
    if s:
        out.append(s)
    return out


def extract_key_info(candidates: Iterable[str]) -> tuple[Optional[str], Optional[tuple[str, str]]]:
    first_candidate: Optional[str] = None
    for raw in candidates:
        if first_candidate is None:
            first_candidate = raw
        parsed = parse_key(raw)
        if parsed:
            return raw, parsed
    return first_candidate, None


def get_id3_candidates(tags: ID3, source_field: Optional[str]) -> list[str]:
    values: list[str] = []

    if source_field:
        wanted = normalize_field_name(source_field)

        if wanted == "TKEY" and "TKEY" in tags:
            values.extend(decode_value(tags.get("TKEY")))

        for frame in tags.getall("TXXX"):
            if normalize_field_name(frame.desc) == wanted:
                values.extend(decode_value(frame))

        return values

    if "TKEY" in tags:
        values.extend(decode_value(tags.get("TKEY")))

    wanted_names = {"INITIALKEY", "KEY", "MUSICALKEY"}
    for frame in tags.getall("TXXX"):
        if normalize_field_name(frame.desc) in wanted_names:
            values.extend(decode_value(frame))

    return values


def get_flac_candidates(audio: FLAC, source_field: Optional[str]) -> list[str]:
    values: list[str] = []
    if not audio.tags:
        return values

    if source_field:
        wanted = normalize_field_name(source_field)
        for k, v in audio.tags.items():
            if normalize_field_name(k) == wanted:
                values.extend(decode_value(v))
        return values

    for k, v in audio.tags.items():
        if normalize_field_name(k) in {"INITIALKEY", "KEY", "MUSICALKEY"}:
            values.extend(decode_value(v))

    return values


def get_mp4_candidates(audio: MP4, source_field: Optional[str]) -> list[str]:
    values: list[str] = []
    if not audio.tags:
        return values

    tags = audio.tags

    if source_field:
        wanted = normalize_field_name(source_field)

        if source_field in tags:
            values.extend(decode_value(tags[source_field]))

        for k, v in tags.items():
            if normalize_field_name(str(k)) == wanted:
                values.extend(decode_value(v))
                return values

        custom_key = f"----:com.apple.iTunes:{source_field}"
        if custom_key in tags:
            values.extend(decode_value(tags[custom_key]))
        return values

    candidate_names = {"INITIALKEY", "KEY", "MUSICALKEY"}
    for k, v in tags.items():
        if normalize_field_name(str(k)) in candidate_names:
            values.extend(decode_value(v))

    return values


def get_source_key(audio: Any, source_field: Optional[str]) -> tuple[Optional[str], Optional[tuple[str, str]]]:
    if isinstance(audio, (MP3, AIFF)):
        tags = audio.tags
        if tags is None:
            return None, None
        return extract_key_info(get_id3_candidates(tags, source_field))

    if isinstance(audio, FLAC):
        return extract_key_info(get_flac_candidates(audio, source_field))

    if isinstance(audio, MP4):
        return extract_key_info(get_mp4_candidates(audio, source_field))

    return None, None


def get_existing_destination_value(audio: Any, dest: str, custom_name: Optional[str]) -> Optional[str]:
    try:
        if isinstance(audio, (MP3, AIFF)):
            tags = audio.tags
            if tags is None:
                return None

            if dest == "comment":
                comms = tags.getall("COMM")
                if comms:
                    vals = decode_value(comms[0])
                    return vals[0] if vals else None

            elif dest == "grouping":
                if "TIT1" in tags:
                    vals = decode_value(tags.get("TIT1"))
                    return vals[0] if vals else None

            elif dest == "custom":
                if not custom_name:
                    return None
                for frame in tags.getall("TXXX"):
                    if frame.desc == custom_name:
                        vals = decode_value(frame)
                        return vals[0] if vals else None

        elif isinstance(audio, FLAC):
            if not audio.tags:
                return None

            key = {
                "comment": "COMMENT",
                "grouping": "GROUPING",
                "custom": custom_name or "",
            }[dest]

            for k, v in audio.tags.items():
                if k.upper() == key.upper():
                    vals = decode_value(v)
                    return vals[0] if vals else None

        elif isinstance(audio, MP4):
            if not audio.tags:
                return None

            if dest == "comment":
                vals = decode_value(audio.tags.get("\xa9cmt"))
                return vals[0] if vals else None
            elif dest == "grouping":
                vals = decode_value(audio.tags.get("\xa9grp"))
                return vals[0] if vals else None
            elif dest == "custom" and custom_name:
                key = f"----:com.apple.iTunes:{custom_name}"
                vals = decode_value(audio.tags.get(key))
                return vals[0] if vals else None
    except Exception:
        return None

    return None


def set_destination_value(audio: Any, dest: str, value: str, custom_name: Optional[str]) -> None:
    if isinstance(audio, (MP3, AIFF)):
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags

        if dest == "comment":
            tags.delall("COMM")
            tags.add(COMM(encoding=3, lang="eng", desc="", text=[value]))
        elif dest == "grouping":
            tags.delall("TIT1")
            tags.add(TIT1(encoding=3, text=[value]))
        elif dest == "custom":
            if not custom_name:
                raise ValueError("custom_name is required when dest=custom")
            keep = [f for f in tags.getall("TXXX") if f.desc != custom_name]
            tags.delall("TXXX")
            for frame in keep:
                tags.add(frame)
            tags.add(TXXX(encoding=3, desc=custom_name, text=[value]))
        else:
            raise ValueError(f"Unsupported destination: {dest}")

    elif isinstance(audio, FLAC):
        if audio.tags is None:
            audio.add_tags()

        if dest == "comment":
            audio["COMMENT"] = [value]
        elif dest == "grouping":
            audio["GROUPING"] = [value]
        elif dest == "custom":
            if not custom_name:
                raise ValueError("custom_name is required when dest=custom")
            audio[custom_name] = [value]
        else:
            raise ValueError(f"Unsupported destination: {dest}")

    elif isinstance(audio, MP4):
        if audio.tags is None:
            audio.add_tags()

        if dest == "comment":
            audio.tags["\xa9cmt"] = [value]
        elif dest == "grouping":
            audio.tags["\xa9grp"] = [value]
        elif dest == "custom":
            if not custom_name:
                raise ValueError("custom_name is required when dest=custom")
            key = f"----:com.apple.iTunes:{custom_name}"
            audio.tags[key] = [MP4FreeForm(value.encode("utf-8"))]
        else:
            raise ValueError(f"Unsupported destination: {dest}")

    else:
        raise ValueError(f"Unsupported file type object: {type(audio).__name__}")


def sanitize_filename_component(value: str) -> str:
    value = value.strip()
    value = re.sub(f"[{re.escape(INVALID_FILENAME_CHARS)}]", "_", value)
    value = re.sub(r"\s+", " ", value)
    value = value.rstrip(". ")
    return value or "Unknown"


def get_tag_text(audio: Any, keys: list[str]) -> str:
    """
    Get a simple text value from common tag locations.
    """
    try:
        if isinstance(audio, (MP3, AIFF)):
            tags = audio.tags
            if not tags:
                return ""
            for key in keys:
                if key in tags:
                    vals = decode_value(tags.get(key))
                    if vals:
                        return vals[0]

        elif isinstance(audio, FLAC):
            if not audio.tags:
                return ""
            for wanted in keys:
                for k, v in audio.tags.items():
                    if k.upper() == wanted.upper():
                        vals = decode_value(v)
                        if vals:
                            return vals[0]

        elif isinstance(audio, MP4):
            if not audio.tags:
                return ""
            for key in keys:
                if key in audio.tags:
                    vals = decode_value(audio.tags.get(key))
                    if vals:
                        return vals[0]
    except Exception:
        return ""

    return ""


def format_key_display(parsed_key: tuple[str, str]) -> str:
    note, mode = parsed_key
    return f"{note}m" if mode == "minor" else note


def strip_title_prefix(title: str) -> str:
    return re.sub(r"^\s*\d{1,2}[AB]\s+\|\s+.+?\s+-\s+", "", title.strip(), count=1)


def build_title_value(camelot: str, key_display: str, title: str) -> str:
    base_title = strip_title_prefix(title) or title.strip() or "Unknown Title"
    return f"{camelot} | {key_display} - {base_title}"


def format_bpm_display(raw_bpm: str) -> str:
    """
    Normalizes BPM strings for filenames.
    Examples:
      '174.0' -> '174'
      '128'   -> '128'
      '128.5' -> '128.5'
    Returns empty string when BPM is missing.
    """
    raw_bpm = normalize_whitespace(str(raw_bpm or ""))
    if not raw_bpm:
        return ""

    m = re.search(r"\d+(?:\.\d+)?", raw_bpm)
    if not m:
        return ""

    number = m.group(0)
    try:
        bpm_float = float(number)
        if bpm_float.is_integer():
            return str(int(bpm_float))
        return f"{bpm_float:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return ""


def get_bpm_text(audio: Any) -> str:
    """
    Pull BPM from common metadata locations across formats.
    """
    try:
        if isinstance(audio, (MP3, AIFF)):
            tags = audio.tags
            if not tags:
                return ""

            if "TBPM" in tags:
                vals = decode_value(tags.get("TBPM"))
                if vals:
                    return vals[0]

            for frame in tags.getall("TXXX"):
                if normalize_field_name(frame.desc) in {"BPM", "TEMPO"}:
                    vals = decode_value(frame)
                    if vals:
                        return vals[0]

        elif isinstance(audio, FLAC):
            if not audio.tags:
                return ""

            for k, v in audio.tags.items():
                if normalize_field_name(k) in {"BPM", "TEMPO"}:
                    vals = decode_value(v)
                    if vals:
                        return vals[0]

        elif isinstance(audio, MP4):
            if not audio.tags:
                return ""

            if "tmpo" in audio.tags:
                vals = decode_value(audio.tags.get("tmpo"))
                if vals:
                    return vals[0]

            for k, v in audio.tags.items():
                if normalize_field_name(str(k)) in {"BPM", "TEMPO", "TMPO"}:
                    vals = decode_value(v)
                    if vals:
                        return vals[0]

    except Exception:
        return ""

    return ""


def get_existing_title(audio: Any) -> str:
    return get_tag_text(audio, ["TIT2", "TITLE", "\xa9nam"])


def set_title(audio: Any, value: str) -> None:
    if isinstance(audio, (MP3, AIFF)):
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
        tags.delall("TIT2")
        tags.add(TIT2(encoding=3, text=[value]))

    elif isinstance(audio, FLAC):
        if audio.tags is None:
            audio.add_tags()
        audio["TITLE"] = [value]

    elif isinstance(audio, MP4):
        if audio.tags is None:
            audio.add_tags()
        audio.tags["\xa9nam"] = [value]

    else:
        raise ValueError(f"Unsupported file type object: {type(audio).__name__}")


def build_default_filename_stem(
    camelot: str,
    key_display: str,
    bpm_display: str,
    artist: str,
    title: str,
) -> str:
    """
    Builds the default filename stem with optional BPM.
    """
    if bpm_display:
        return f"{camelot} | {key_display} | {bpm_display} - {artist} - {title}"
    return f"{camelot} | {key_display} - {artist} - {title}"


def build_new_filename(
    path: Path,
    audio: Any,
    camelot: str,
    parsed_key: tuple[str, str],
) -> Path:
    key_display = format_key_display(parsed_key)

    artist = get_tag_text(audio, ["TPE1", "ARTIST", "\xa9ART"])
    title = get_tag_text(audio, ["TIT2", "TITLE", "\xa9nam"])
    track = get_tag_text(audio, ["TRCK", "TRACKNUMBER", "trkn"])
    year = get_tag_text(audio, ["TDRC", "DATE", "\xa9day"])
    genre = get_tag_text(audio, ["TCON", "GENRE", "\xa9gen"])
    bpm_raw = get_bpm_text(audio)
    bpm_display = format_bpm_display(bpm_raw)

    artist_clean = sanitize_filename_component(artist or path.stem)
    title_clean = sanitize_filename_component(title or path.stem)

    parts = {
        "artist": artist_clean,
        "title": title_clean,
        "camelot": sanitize_filename_component(camelot),
        "key": sanitize_filename_component(key_display),
        "bpm": sanitize_filename_component(bpm_display) if bpm_display else "",
        "track": sanitize_filename_component(track),
        "year": sanitize_filename_component(year),
        "genre": sanitize_filename_component(genre),
    }

    new_stem = build_default_filename_stem(
        camelot=parts["camelot"],
        key_display=parts["key"],
        bpm_display=parts["bpm"],
        artist=parts["artist"],
        title=parts["title"],
    )

    new_stem = sanitize_filename_component(new_stem)

    return path.with_name(new_stem + path.suffix)


def safe_rename(path: Path, new_path: Path) -> Path:
    if path == new_path:
        return path

    candidate = new_path
    counter = 2

    while candidate.exists():
        candidate = new_path.with_name(f"{new_path.stem} ({counter}){new_path.suffix}")
        counter += 1

    path.rename(candidate)
    return candidate


def iter_audio_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def process_file(
    path: Path,
    dest: str,
    custom_name: Optional[str],
    source_field: Optional[str],
    write: bool,
    rename: bool,
    verbose: bool,
    stats: Stats,
) -> None:
    stats.scanned += 1

    try:
        audio = File(path)
        if audio is None:
            if verbose:
                print(f"[SKIP] Unsupported/unreadable: {path}")
            return

        if not isinstance(audio, (MP3, FLAC, MP4, AIFF)):
            if verbose:
                print(f"[SKIP] Unsupported type object: {path} ({type(audio).__name__})")
            return

        stats.supported += 1

        raw_key, parsed_key = get_source_key(audio, source_field)
        if raw_key is None:
            stats.missing_key += 1
            if verbose:
                print(f"[SKIP] No key metadata found: {path}")
            return

        if parsed_key is None:
            stats.invalid_key += 1
            if verbose:
                print(f"[SKIP] Invalid key metadata: {path} -> {raw_key!r}")
            return

        camelot = to_camelot(parsed_key)
        if camelot is None:
            stats.invalid_key += 1
            if verbose:
                print(f"[SKIP] Could not map key: {path} -> {raw_key!r}")
            return

        key_display = format_key_display(parsed_key)
        existing = get_existing_destination_value(audio, dest, custom_name)
        existing_title = get_existing_title(audio)
        title_source = existing_title or path.stem
        desired_title = build_title_value(camelot, key_display, title_source)

        if existing == camelot and existing_title == desired_title and not rename:
            stats.unchanged += 1
            if verbose:
                print(f"[UNCHANGED] {path} | {raw_key} -> {camelot} | title={desired_title}")
            return

        if not write:
            stats.would_write += 1
            preview_path = path
            if rename:
                preview_path = build_new_filename(
                    path=path,
                    audio=audio,
                    camelot=camelot,
                    parsed_key=parsed_key,
                )
                print(f"[DRY-RUN] {path} | source={raw_key!r} -> camelot={camelot} | title={desired_title}")
                print(f"          OLD: {path.name}")
                print(f"          NEW: {preview_path.name}")
            else:
                print(f"[DRY-RUN] {path} | source={raw_key!r} -> camelot={camelot} | title={desired_title}")
            return

        if existing != camelot:
            set_destination_value(audio, dest, camelot, custom_name)

        if existing_title != desired_title:
            set_title(audio, desired_title)

        audio.save()

        final_path = path

        if rename:
            new_path = build_new_filename(
                path=path,
                audio=audio,
                camelot=camelot,
                parsed_key=parsed_key,
            )
            print(f"[RENAME] {path}")
            print(f"         OLD: {path.name}")
            print(f"         NEW: {new_path.name}")
            renamed_path = safe_rename(path, new_path)
            if renamed_path != path:
                stats.renamed += 1
            final_path = renamed_path

        stats.written += 1
        print(f"[WROTE] {final_path} | source={raw_key!r} -> camelot={camelot} | title={desired_title}")

    except MutagenError as e:
        stats.errors += 1
        print(f"[ERROR] {path} | MutagenError: {e}", file=sys.stderr)
    except Exception as e:
        stats.errors += 1
        print(f"[ERROR] {path} | {type(e).__name__}: {e}", file=sys.stderr)


def print_mapping_table() -> None:
    print("\nCamelot mapping table")
    print("-" * 44)
    rows = sorted(CAMELOT_MAP.items(), key=lambda kv: (int(kv[1][:-1]), kv[1][-1]))
    for (note, mode), camelot in rows:
        display = DISPLAY_EQUIVALENTS[(note, mode)]
        print(f"{camelot:>3}  =  {display}")


def print_summary(stats: Stats, write: bool) -> None:
    print("\nSummary")
    print("-" * 44)
    print(f"Files scanned:                {stats.scanned}")
    print(f"Supported audio files:        {stats.supported}")
    print(f"Missing key metadata:         {stats.missing_key}")
    print(f"Invalid/unmapped keys:        {stats.invalid_key}")
    print(f"Destination already correct:  {stats.unchanged}")
    if write:
        print(f"Files written:                {stats.written}")
        print(f"Files renamed:                {stats.renamed}")
    else:
        print(f"Files that would be written:  {stats.would_write}")
    print(f"Errors:                       {stats.errors}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert musical key metadata to Camelot notation and write it to audio tags."
    )
    parser.add_argument("folder", type=Path, help="Root music folder to scan recursively")
    parser.add_argument(
        "--dest",
        choices=["comment", "grouping", "custom"],
        default="comment",
        help="Destination field to write Camelot into (default: comment)",
    )
    parser.add_argument(
        "--custom-name",
        default="CAMELOT",
        help="Custom field name when --dest custom (default: CAMELOT)",
    )
    parser.add_argument(
        "--source-field",
        default=None,
        help=(
            "Optional source key field override. "
            "Examples: TKEY, INITIALKEY, KEY, or an MP4 freeform field name."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually write changes. Without this flag, the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="Rename files after tag processing using the built-in Camelot | Musical Key | BPM - Artist - Title format.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print skip reasons and unchanged files too.",
    )
    parser.add_argument(
        "--show-map",
        action="store_true",
        help="Print the 24-key Camelot mapping table before processing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    root = args.folder.expanduser().resolve()
    source_field = normalize_whitespace(args.source_field) if args.source_field else None
    if not root.exists() or not root.is_dir():
        print(f"Folder does not exist or is not a directory: {root}", file=sys.stderr)
        return 2

    if args.dest == "custom" and not args.custom_name:
        print("--custom-name is required when --dest custom", file=sys.stderr)
        return 2

    if args.show_map:
        print_mapping_table()

    stats = Stats()

    for path in iter_audio_files(root):
        process_file(
            path=path,
            dest=args.dest,
            custom_name=args.custom_name,
            source_field=source_field,
            write=args.write,
            rename=args.rename,
            verbose=args.verbose,
            stats=stats,
        )

    print_summary(stats, write=args.write)
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
        print(f"\n[ERROR] camelot_converter failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
