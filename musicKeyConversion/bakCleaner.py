from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete .bak files from the musicKeyConversion folder."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="Folder to scan for .bak files. Defaults to this script's folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which .bak files would be deleted without removing them.",
    )
    return parser.parse_args()


def prompt_for_target(default_target: Path) -> Path:
    response = input(
        f"Enter the folder path to clean .bak files recursively "
        f"(press Enter for {default_target}): "
    ).strip().strip('"')
    if not response:
        return default_target
    return Path(response)


def main() -> int:
    args = parse_args()
    default_target = Path(__file__).resolve().parent
    target = args.target if "target" in args and args.target != default_target else prompt_for_target(default_target)
    target = target.resolve()

    if not target.exists():
        print(f"Target does not exist: {target}")
        return 1

    if not target.is_dir():
        print(f"Target is not a directory: {target}")
        return 1

    bak_files = sorted(path for path in target.rglob("*.bak") if path.is_file())

    if not bak_files:
        print(f"No .bak files found in {target}")
        return 0

    action = "Would delete" if args.dry_run else "Deleted"

    for bak_file in bak_files:
        if not args.dry_run:
            bak_file.unlink()
        print(f"{action}: {bak_file}")

    print(f"{action} {len(bak_files)} .bak file(s) in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
