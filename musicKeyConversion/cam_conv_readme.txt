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
- Optional backup before write
- Optional file renaming with Camelot + key + BPM first
- Updates the track title so Camelot + key appear before the title in DJ software

Default rename pattern:
    {camelot} | {key} | {bpm} - {artist} - {title}

Recommended first use:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --verbose

Actually write changes:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --write --backup --verbose

Write + rename:
    python camelot_converter.py "D:\\Music\\camelot_test" --dest comment --write --backup --rename --verbose
