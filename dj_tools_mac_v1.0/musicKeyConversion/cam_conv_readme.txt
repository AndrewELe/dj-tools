Camelot converter for DJ tracks.

Features:
- Recursively scans a music folder
- Supports MP3, FLAC, MP4/M4A, AIFF/AIF
- Reads common key metadata fields
- Converts standard musical keys to Camelot notation
- Pulls BPM from metadata for filename rewriting
- Dry-run by default
- Optionally writes Camelot into comments, grouping, or a custom field
- Handles enharmonic spellings (C# / Db, etc.)
- Skips missing/invalid keys
- Prints summary report
- Optional file renaming with Camelot + key first, and BPM only when available
- Updates the track title so Camelot + key appear before the title in DJ software

Built-in rename format:
    Camelot | Musical Key | BPM - Artist - Title
    BPM is skipped automatically if it is missing.
    The track title tag is also updated to:
    Camelot | Musical Key - Title

Recommended first use:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --verbose

Actually write changes:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --write --verbose

Write + rename:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --write --rename --verbose
