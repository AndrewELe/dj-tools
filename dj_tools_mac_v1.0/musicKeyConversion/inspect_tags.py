from mutagen import File
from pathlib import Path
import sys


def main():
    if len(sys.argv) < 2:
        print(r'Usage: python inspect_tags.py "D:\Music\file.mp3"')
        return 2

    path = Path(sys.argv[1]).expanduser()
    if not path.exists() or not path.is_file():
        print(f"File does not exist or is not a regular file: {path}")
        return 2

    audio = File(path)

    print("\n==============================")
    print(f"FILE: {path}")
    print("==============================")

    if audio is None:
        print("❌ Mutagen could not read this file at all.")
        return 1

    print(f"Audio type: {type(audio).__name__}")

    # Raw object
    print("\n--- RAW AUDIO OBJECT ---")
    print(audio)

    # Tags object
    print("\n--- TAGS OBJECT ---")
    print(audio.tags)

    # Keys (if possible)
    print("\n--- TAG KEYS ---")
    try:
        if audio.tags and hasattr(audio.tags, "keys"):
            for k in audio.tags.keys():
                print(k)
        else:
            print("No tag keys found.")
    except Exception as e:
        print(f"Error reading keys: {e}")

    # Info block (IMPORTANT)
    print("\n--- AUDIO INFO (VERY IMPORTANT) ---")
    try:
        info = getattr(audio, "info", None)
        if info:
            for attr in dir(info):
                if not attr.startswith("_"):
                    try:
                        value = getattr(info, attr)
                        print(f"{attr}: {value}")
                    except Exception:
                        pass
        else:
            print("No audio.info found.")
    except Exception as e:
        print(f"Error reading info: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
