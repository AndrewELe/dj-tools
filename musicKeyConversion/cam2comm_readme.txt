Camelot-to-comments converter for DJ tracks.

Purpose:
- Read existing musical key metadata from files
- Convert that key to Camelot notation
- Read BPM from metadata
- Write "Camelot | musical key | BPM" into the COMMENT field
- Keep the original filename unchanged for Rekordbox file integrity

Examples of written comments:
- 8A | Am | 128
- 5A | Cm | 140
- 2B | F# | 174
- 3A | A#m | 150

Features:
- Recursively scans a music folder
- Supports MP3, FLAC, MP4/M4A, AIFF/AIF
- Reads common key metadata fields
- Converts standard musical keys to Camelot notation
- Pulls BPM from metadata
- Dry-run by default
- Optional backup before write
- Optional cleanup of .bak files after successful write
- Skips missing/invalid keys
- Prints summary report

Recommended first use:
    python camelot_to_comments.py "D:\Music\camelot_test" --verbose

Actually write changes:
    python camelot_to_comments.py "D:\Music\camelot_test" --write --backup --verbose

Write + cleanup backups:
    python camelot_to_comments.py "D:\Music\camelot_test" --write --backup --cleanup-backups --verbose