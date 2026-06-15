from pathlib import Path
from datetime import datetime
import sys
import subprocess
import platform


ENERGY_LEVELS = ["high", "mid", "low"]

SIMPLE_GENRES = [
    "afro house",
    "breaks",
    "dnb",
    "dubstep",
    "happy hardcore, jumpcore",
    "minimal, deep tech",
    "organic house, downtempo",
    "techno",
    "trance",
    "trap",
    "uk bass",
    "other",
]

GROUPED_GENRES = {
    "house": [
        "deep house",
        "tech house",
        "melodic house, techno",
    ],
    "hardstyle": [
        "hard dance",
        "hard techno",
    ],
    "progressive": [
        "progressive house",
        "progressive trance",
    ],
}


def get_today_folder_name() -> str:
    now = datetime.now()
    if platform.system() == "Windows":
        date_str = now.strftime("%#m.%#d.%y")
    else:
        date_str = now.strftime("%-m.%-d.%y")
    return f"sorted {date_str}"


def get_notables_filename() -> str:
    date_str = datetime.now().strftime("%m.%d.%Y")
    return f"{date_str} notables.txt"


def create_folder_with_energy(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for level in ENERGY_LEVELS:
        (path / level).mkdir(exist_ok=True)


def unique_dated_folder(parent: Path) -> Path:
    base_name = get_today_folder_name()
    candidate = parent / base_name

    counter = 1
    while candidate.exists():
        candidate = parent / f"{base_name} ({counter})"
        counter += 1

    return candidate


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


def get_notables_sections() -> list[str]:
    sections: list[str] = []
    sections.extend(SIMPLE_GENRES)

    for parent_genre, subgenres in GROUPED_GENRES.items():
        sections.append(parent_genre)
        sections.extend(subgenres)

    return sections


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

    for genre in get_notables_sections():
        lines.append("")
        lines.append(genre)
        lines.append("")
        lines.append("- ")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def create_notables_file(parent_path: Path) -> Path:
    notables_path = unique_notables_file(parent_path)
    content = build_notables_content()
    notables_path.write_text(content, encoding="utf-8")
    return notables_path


def build_structure(parent_path: Path) -> tuple[Path, Path]:
    final_base_path = unique_dated_folder(parent_path)
    final_base_path.mkdir(parents=True, exist_ok=False)

    for genre in SIMPLE_GENRES:
        create_folder_with_energy(final_base_path / genre)

    for parent_genre, subgenres in GROUPED_GENRES.items():
        parent_folder = final_base_path / parent_genre
        create_folder_with_energy(parent_folder)

        for subgenre in subgenres:
            create_folder_with_energy(parent_folder / subgenre)

    notables_file = create_notables_file(parent_path)
    return final_base_path, notables_file


def main() -> None:
    if len(sys.argv) > 1:
        parent_input = sys.argv[1]
    else:
        parent_input = input("Enter the parent folder path (or Q to return to menu): ")

    parent_input = normalize_input_path(parent_input)

    if parent_input.lower() == "q":
        print("Returning to menu.")
        return

    if not parent_input:
        print("Error: no parent folder path entered.")
        sys.exit(1)

    parent_path = Path(parent_input)

    if not parent_path.exists():
        print(f"Error: path does not exist: {parent_path}")
        sys.exit(1)

    if not parent_path.is_dir():
        print(f"Error: path is not a folder: {parent_path}")
        sys.exit(1)

    try:
        created_path, notables_file = build_structure(parent_path)
        print("\nDone. Folder tree created successfully:")
        print(created_path)
        print("\nNotables file created:")
        print(notables_file)
        open_folder(created_path)
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