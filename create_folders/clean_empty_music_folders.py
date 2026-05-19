from pathlib import Path
import sys
from typing import Optional

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


def normalize_input_path(raw_input: str) -> str:
    return raw_input.strip().strip('"').strip("'")


def contains_music(folder: Path) -> bool:
    for item in folder.rglob("*"):
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            return True
    return False


def build_protected_relative_paths() -> set[Path]:
    protected: set[Path] = set()

    for genre in SIMPLE_GENRES:
        g = Path(genre)
        protected.add(g)
        for lvl in ENERGY_LEVELS:
            protected.add(g / lvl)

    for parent, subs in GROUPED_GENRES.items():
        p = Path(parent)
        protected.add(p)
        for lvl in ENERGY_LEVELS:
            protected.add(p / lvl)

        for sub in subs:
            s = p / sub
            protected.add(s)
            for lvl in ENERGY_LEVELS:
                protected.add(s / lvl)

    return protected


PROTECTED = build_protected_relative_paths()


def is_protected(root: Path, folder: Path) -> bool:
    try:
        rel = folder.relative_to(root)
    except ValueError:
        return False
    return rel in PROTECTED


def analyze_actions(root: Path, delete_mode: bool) -> tuple[list[tuple[str, Path, Optional[Path]]], dict[str, int]]:
    folders = sorted(
        [p for p in root.rglob("*") if p.is_dir()],
        key=lambda x: len(x.parts),
        reverse=True,
    )

    actions: list[tuple[str, Path, Optional[Path]]] = []
    summary = {
        "delete": 0,
        "mark": 0,
        "restore": 0,
    }

    for folder in folders:
        has_music = contains_music(folder)
        name = folder.name

        if has_music and name.endswith(" (empty)"):
            new_name = name[:-8]
            new_path = folder.with_name(new_name)
            if not new_path.exists():
                actions.append(("restore", folder, new_path))
                summary["restore"] += 1
            continue

        if delete_mode:
            if not has_music:
                actions.append(("delete", folder, None))
                summary["delete"] += 1
            continue

        if is_protected(root, folder):
            if not has_music and not name.endswith(" (empty)"):
                new_path = folder.with_name(f"{name} (empty)")
                if not new_path.exists():
                    actions.append(("mark", folder, new_path))
                    summary["mark"] += 1
            continue

        if not has_music:
            actions.append(("delete", folder, None))
            summary["delete"] += 1

    return actions, summary


def print_preview(root: Path, actions: list[tuple[str, Path, Optional[Path]]], summary: dict[str, int]) -> None:
    print("\nPreview:\n")

    if not actions:
        print("No changes needed.")
        return

    for action, source, target in actions:
        try:
            rel_source = source.relative_to(root)
        except ValueError:
            rel_source = source

        if action == "delete":
            print(f"[DELETE ] {rel_source}")
        elif action == "mark" and target is not None:
            try:
                rel_target = target.relative_to(root)
            except ValueError:
                rel_target = target
            print(f"[MARK   ] {rel_source}  ->  {rel_target}")
        elif action == "restore" and target is not None:
            try:
                rel_target = target.relative_to(root)
            except ValueError:
                rel_target = target
            print(f"[RESTORE] {rel_source}  ->  {rel_target}")

    print("\nSummary:")
    print(f"Delete:  {summary['delete']}")
    print(f"Mark:    {summary['mark']}")
    print(f"Restore: {summary['restore']}")


def apply_actions(actions: list[tuple[str, Path, Optional[Path]]]) -> dict[str, int]:
    results = {
        "delete": 0,
        "mark": 0,
        "restore": 0,
        "skipped": 0,
    }

    for action, source, target in actions:
        try:
            if action == "delete":
                source.rmdir()
                print(f"Deleted: {source}")
                results["delete"] += 1

            elif action in {"mark", "restore"} and target is not None:
                if not target.exists():
                    source.rename(target)
                    if action == "mark":
                        print(f"Marked empty: {target}")
                        results["mark"] += 1
                    else:
                        print(f"Restored: {target}")
                        results["restore"] += 1
                else:
                    results["skipped"] += 1

        except OSError:
            results["skipped"] += 1

    return results


def find_notables_file(parent: Path) -> Optional[Path]:
    candidates = sorted(parent.glob("* notables.txt"))
    return candidates[0] if candidates else None


def section_to_folder_map() -> dict[str, Path]:
    mapping: dict[str, Path] = {}

    for genre in SIMPLE_GENRES:
        mapping[genre] = Path(genre)

    for parent, subs in GROUPED_GENRES.items():
        mapping[parent] = Path(parent)
        for sub in subs:
            mapping[sub] = Path(parent) / sub

    return mapping


SECTION_FOLDER_MAP = section_to_folder_map()
SECTION_NAMES = set(SECTION_FOLDER_MAP.keys())


def split_notables_sections(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """
    Returns:
      header_lines,
      [(section_name, section_lines), ...]
    """
    header: list[str] = []
    sections: list[tuple[str, list[str]]] = []

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in SECTION_NAMES:
            break
        header.append(lines[i])
        i += 1

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in SECTION_NAMES:
            section_name = stripped
            block = [lines[i]]
            i += 1

            while i < len(lines) and lines[i].strip() not in SECTION_NAMES:
                block.append(lines[i])
                i += 1

            sections.append((section_name, block))
        else:
            i += 1

    return header, sections


def genre_folder_has_music(crate_root: Path, section_name: str) -> bool:
    rel = SECTION_FOLDER_MAP.get(section_name)
    if rel is None:
        return False

    folder = crate_root / rel
    if not folder.exists() or not folder.is_dir():
        return False

    return contains_music(folder)


def prune_notables_file(parent_of_crate: Path, crate_root: Path) -> Optional[Path]:
    source_file = find_notables_file(parent_of_crate)
    if source_file is None:
        print("\nNo notables file found. Skipping notables prune.")
        return None

    text = source_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    header, sections = split_notables_sections(lines)

    kept_sections: list[str] = []
    removed_count = 0

    for section_name, block_lines in sections:
        if genre_folder_has_music(crate_root, section_name):
            kept_sections.extend(block_lines)
            kept_sections.append("")
        else:
            removed_count += 1

    output_lines = header[:]
    if output_lines and output_lines[-1] != "":
        output_lines.append("")
    output_lines.extend(kept_sections)

    while output_lines and output_lines[-1] == "":
        output_lines.pop()

    pruned_path = source_file.with_name(source_file.stem + ".pruned" + source_file.suffix)
    pruned_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    print(f"\nPruned notables file created: {pruned_path}")
    print(f"Removed genre sections with no music: {removed_count}")
    return pruned_path


def main() -> None:
    if len(sys.argv) > 1:
        root_input = sys.argv[1]
    else:
        root_input = input("Enter folder to clean (or Q to return to menu): ")

    root_input = normalize_input_path(root_input)

    if root_input.lower() == "q":
        print("Returning to menu.")
        return

    if not root_input:
        print("No path provided.")
        sys.exit(1)

    root = Path(root_input)

    if not root.exists():
        print(f"Path does not exist: {root}")
        sys.exit(1)

    if not root.is_dir():
        print(f"Not a folder: {root}")
        sys.exit(1)

    choice = input("\nDelete empty folders? (y/n, or Q to return to menu): ").strip().lower()
    if choice == "q":
        print("Returning to menu.")
        return
    delete_mode = choice == "y"

    if delete_mode:
        print("\nMode: DELETE empty folders")
    else:
        print("\nMode: SMART MARK template folders, delete non-template junk")

    actions, summary = analyze_actions(root, delete_mode)
    print_preview(root, actions, summary)

    if not actions:
        print("\nNothing to do for folders.")
    else:
        confirm = input("\nProceed with these folder changes? (y/n, or Q to return to menu): ").strip().lower()
        if confirm == "q":
            print("Returning to menu.")
            return
        if confirm == "y":
            print("\nApplying changes...\n")
            results = apply_actions(actions)

            print("\nDone.")
            print(f"Deleted:  {results['delete']}")
            print(f"Marked:   {results['mark']}")
            print(f"Restored: {results['restore']}")
            print(f"Skipped:  {results['skipped']}")
        else:
            print("\nCancelled folder changes. No folder changes were made.")

    prune_choice = input("\nCreate a pruned notables file with only genres that have music? (y/n, or Q to return to menu): ").strip().lower()
    if prune_choice == "q":
        print("Returning to menu.")
        return
    if prune_choice == "y":
        parent_of_crate = root.parent
        prune_notables_file(parent_of_crate, root)

    if len(sys.argv) == 1:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] clean_empty_music_folders failed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)