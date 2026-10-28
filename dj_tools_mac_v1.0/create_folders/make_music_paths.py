from pathlib import Path
from datetime import datetime
import sys
import subprocess
import platform

from genre_layout import (
    EMPTY_SUFFIX,
    ENERGY_LEVELS,
    GENRE_FOLDERS,
    GENRES,
    NEW_FOLDER,
)
import migrate_old_folders


def get_notables_filename() -> str:
    date_str = datetime.now().strftime("%m.%d.%Y")
    return f"{date_str} notables.txt"


def ensure_folder(path: Path) -> bool:
    """
    Create path unless it, or a copy marked " (empty)" by
    clean_empty_music_folders.py, already exists. Returns True if created.
    """
    if path.exists() or path.with_name(path.name + EMPTY_SUFFIX).exists():
        return False
    path.mkdir(parents=True)
    return True


def existing_folder(path: Path) -> Path:
    marked = path.with_name(path.name + EMPTY_SUFFIX)
    return marked if not path.exists() and marked.exists() else path


def create_folder_with_energy(path: Path) -> int:
    created = int(ensure_folder(path))
    path = existing_folder(path)
    for level in ENERGY_LEVELS:
        created += ensure_folder(path / level)
    return created


def unique_notables_file(parent: Path) -> Path:
    base_name = get_notables_filename()
    candidate = parent / base_name

    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix

    counter = 1
    while True:
        alt = parent / f"{stem} ({counter}){suffix}"
        if not alt.exists():
            return alt
        counter += 1


def open_folder(path: Path) -> None:
    try:
        system_name = platform.system()

        if system_name == "Windows":
            subprocess.run(["explorer", str(path)], check=False)
        elif system_name == "Darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


def normalize_input_path(raw_input: str) -> str:
    return raw_input.strip().strip('"').strip("'")


def build_notables_content() -> str:
    today_display = datetime.now().strftime("%m.%d.%Y")

    lines: list[str] = [
        f"{today_display}",
        "    notables",
        "",
        "==============================================",
        "** -> really good track",
        "%% -> buy/get on beatport",
        "==============================================",
        "",
    ]

    for genre in GENRES:
        lines.append("")
        lines.append(genre)
        lines.append("")
        lines.append("- ")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def create_notables_file(library_path: Path) -> Path:
    notables_path = unique_notables_file(library_path)
    content = build_notables_content()
    notables_path.write_text(content, encoding="utf-8")
    return notables_path


def build_structure(library_path: Path) -> int:
    """Create whichever genre and energy folders are missing. Returns how many."""
    created = int(ensure_folder(library_path / NEW_FOLDER))

    for genre in GENRES:
        created += create_folder_with_energy(library_path / GENRE_FOLDERS[genre])

    return created


def main() -> None:
    if len(sys.argv) > 1:
        library_input = sys.argv[1]
    else:
        library_input = input("Enter your music library folder (or Q to return to menu): ")

    library_input = normalize_input_path(library_input)

    if library_input.lower() == "q":
        print("Returning to menu.")
        return

    if not library_input:
        print("Error: no library folder path entered.")
        sys.exit(1)

    library_path = Path(library_input)

    if not library_path.exists():
        print(f"Error: path does not exist: {library_path}")
        sys.exit(1)

    if not library_path.is_dir():
        print(f"Error: path is not a folder: {library_path}")
        sys.exit(1)

    library_path = library_path.resolve()

    try:
        created = build_structure(library_path)
        print("\nDone. Genre folders are ready in:")
        print(library_path)
        print(f"Folders created: {created}")

        # Old dated crate trees and folders from an older numbering, sitting
        # in the same library. Previews and asks before moving anything.
        migrate_old_folders.run(library_path, library_path)

        notables_file = create_notables_file(library_path)
        print("\nNotables file created:")
        print(notables_file)
        open_folder(library_path)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] make_music_paths failed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
