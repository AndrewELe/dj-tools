# DJ Tools README

This folder contains a small menu-driven toolkit for DJ library work.

Main launcher:
`C:\dj_tools\dj_tools_menu.bat`

Open that batch file to launch the menu, then choose one of the numbered options.

## What This Toolkit Does

The menu currently includes:

1. Build new dated crate tree
2. Clean / mark empty folders
3. Run crate digger
4. Camelot converter
5. Camelot to comments
6. Clean `.bak` files
7. Exit

## Basic Usage

1. Run `dj_tools_menu.bat`.
2. Type the number of the tool you want.
3. Answer the prompts shown in the terminal.
4. Press Enter when prompted to return to the main menu.

If a prompt asks for a path, you can usually paste the folder path directly into the terminal.

## Menu Option 1: Build New Dated Crate Tree

Purpose:
Creates a new dated music-crate folder structure and a matching notables text file.

What it asks for:
`Enter the parent folder path`

What you should enter:
The folder where you want the new dated crate folder to be created.

Example:
`D:\`

What it creates:

- A folder named like `sorted 3.22.26`
- If that name already exists, it creates `sorted 3.22.26 (1)` and so on
- A notables file in the parent folder named like `03.22.2026 notables.txt`

Folder structure it creates:

- Genre folders
- Energy subfolders inside those genres: `high`, `mid`, `low`
- Grouped genres such as `house`, `hardstyle`, and `progressive` with their own subgenres

What the notables file is for:
It gives you a template where you can jot down standout tracks by genre.

Good time to use this:
Use it when starting a fresh sorting session for a new batch of music.

## Menu Option 2: Clean / Mark Empty Folders

Purpose:
Scans a crate folder and helps you clean up empty folders.

What it asks for first:
`Enter the folder to clean`

Use this on:
The dated crate folder you want to clean up.

Then it asks:
`Delete empty folders? (y/n)`

What this means:

- `y` = delete all empty folders it can remove
- `n` = use smart mode

Smart mode behavior:

- Protected template folders are not deleted
- Empty protected folders get renamed with ` (empty)` at the end
- Empty non-template folders are deleted
- If a folder was marked ` (empty)` before and now contains music, it gets restored to its normal name

Preview step:
Before making changes, it shows a preview of what it plans to do:

- `[DELETE]` means the folder will be removed
- `[MARK]` means the folder will be renamed to include ` (empty)`
- `[RESTORE]` means an ` (empty)` folder will be renamed back

Confirmation step:
It asks:
`Proceed with these folder changes? (y/n)`

Then it optionally asks:
`Create a pruned notables file with only genres that have music? (y/n)`

What that does:
Creates a `.pruned` version of the notables file that keeps only sections for genres that still contain music.

Good time to use this:
After sorting a crate, when you want to clean out unused folders and tidy the notes file.

## Menu Option 3: Run Crate Digger

Purpose:
Runs the download/discovery workflow in `crate-digger`.

What it uses:

- `sources.txt`
- `crawler.txt`
- `discovered_sources.txt`
- `yt-dlp.exe`
- `yt-dlp.conf`
- `discover.ps1`
- `dedupe_audio.ps1`

What happens when it starts:
You are asked how you want the run to behave.

Startup controls:

- `Enter` = step through each source one by one
- `A` = automatic mode, run through everything without pausing
- `Q` = quit immediately

While stepping through sources:

- `Enter` = run this source
- `S` = skip this source
- `A` = switch to auto-run for the rest
- `Q` = quit the session

What it processes:

- Main sources from `sources.txt`
- Crawler seeds from `crawler.txt`
- Discovered sources from `discovered_sources.txt`

Important detail:
Discovered sources are limited with `--playlist-end 5`, so only the first 5 entries of each discovered playlist/source are processed.

At the end:
It asks:
`Run audio dedupe now? (Y/N)`

What that means:

- `Y` = run the dedupe PowerShell script
- `N` = finish without deduping

Good time to use this:
When you want to pull new music from your saved source lists and optionally dedupe the results afterward.

## Menu Option 4: Camelot Converter

Purpose:
Reads each audio file's musical key, converts it to Camelot notation, writes the result to a tag, and can optionally rename files.

What file types it works with:

- MP3
- FLAC
- MP4 / M4A
- AIFF / AIF

What it asks for first:
`Enter the root music folder to scan`

Use this on:
The top-level folder that contains the music files you want to process.

### Destination Choice

Prompt:
`Choose where to save it (1-3, default 1)`

Options:

- `1` = save Camelot into the comment tag
- `2` = save Camelot into the grouping tag
- `3` = save Camelot into a custom tag name

If you choose `3`:
It asks for a custom tag name.

Default custom tag name behavior:
If you press Enter there, the script uses `CAMELOT`.

### Key Source Tag Override

Prompt:
`Key source tag override (press Enter to auto-detect)`

What this means:
If your files store musical key in a known field like `TKEY`, `INITIALKEY`, or `KEY`, you can type that field name here.

Recommended:
Press Enter unless you already know auto-detection is missing the correct field.

### Preview vs Write

Prompt:
`Press Enter for a safe preview only, or type W to actually write tag changes`

What this means:

- Press `Enter` = dry run only, no file changes
- Type `W` = actually write tags

Recommended first run:
Use preview mode first.

### Backup Options

These only appear if you chose `W`.

Prompt:
`Create .bak backup files before writing? (Y/N, default Y)`

Meaning:

- `Y` or Enter = make a backup copy before editing each file
- `N` = do not create backups

Next prompt:
`Delete backup files after a successful write? (Y/N, default N)`

Meaning:

- `Y` = remove `.bak` files after successful writes
- `N` or Enter = keep `.bak` files

### Rename Option

Prompt:
`Also rename the files using that format? (Y/N, default N)`

Meaning:

- `Y` = rename files
- `N` or Enter = keep filenames unchanged

Default rename format:
`Camelot | Musical Key | BPM - Artist - Title`

If BPM is missing:
The script skips BPM automatically.

Custom rename pattern prompt:
`Optional custom filename pattern (press Enter to use the format above)`

Use this only if you already know exactly how you want your filenames formatted.

### Verbose Output

Prompt:
`Show detailed output while processing? (Y/N, default Y)`

Meaning:

- `Y` or Enter = show detailed progress
- `N` = quieter output

### Show Map

Prompt:
`Show the Camelot key map before processing? (Y/N, default N)`

Meaning:

- `Y` = print the key conversion map first
- `N` or Enter = skip it

Best use case:
Use this when you want Camelot values written somewhere useful in the tags and possibly at the start of filenames.

Safer first-time recommendation:

1. Run in preview mode first
2. If the results look good, run again with `W`
3. Keep backups on for the first write pass

## Menu Option 5: Camelot To Comments

Purpose:
Reads the musical key from each file, converts it to Camelot, reads BPM, and writes this format into the comment tag:

`Camelot | musical key | BPM`

Example comments:

- `8A | Am | 128`
- `5A | Cm | 140`
- `2B | F# | 174`

Main difference from Option 4:

- Option 4 can write Camelot to different tag destinations and can rename files
- Option 5 always writes the comment field in the combined format above and keeps filenames unchanged

What it asks for:

- Root music folder
- Optional key source tag override
- Preview or write mode
- Backup creation
- Backup cleanup
- Verbose output
- Show Camelot map

What the prompts mean:
They work the same way as in Option 4, except there is no rename section.

Best use case:
Use this when you want a clean, Rekordbox-friendly comment format without changing filenames.

Safer first-time recommendation:
Run a preview first, then run again with write enabled and backups on.

## Menu Option 6: Clean `.bak` Files

Purpose:
Deletes backup files ending in `.bak`.

What happens:
This launches `bakCleaner.py`, which prompts for a folder path and then scans that folder recursively.

Prompt:
`Enter the folder path to clean .bak files recursively`

What to enter:
The folder you want scanned for backup files.

If you press Enter:
It defaults to:
`C:\dj_tools\musicKeyConversion`

What it does:

- Finds all files ending in `.bak`
- Searches through subfolders too
- Deletes the `.bak` files it finds

When to use it:

- After a successful write pass if you no longer want backup files
- Any time you want to clean leftover `.bak` files from a folder tree

Important note:
This deletes the `.bak` files it finds. Make sure you no longer need those backups first.

## Menu Option 7: Exit

Purpose:
Closes the menu.

## Recommended Workflows

### For a New Sorting Session

1. Use Option 1 to build a new dated crate tree
2. Sort your music into the created folders
3. Use Option 2 to clean or mark empty folders
4. Optionally create a pruned notables file

### For Key Tagging Safely

1. Use Option 4 or 5
2. Run a preview first
3. If the output looks correct, run again with write enabled
4. Leave backups on during the first real write
5. Use Option 6 later if you want to remove backup files

### For Pulling New Music

1. Use Option 3
2. Step through sources if you want control
3. Use auto mode if you want a hands-off run
4. Run dedupe at the end if needed

## Tips

- If you are unsure, choose preview mode before writing or deleting anything
- Keep `.bak` backups on during first-time testing
- Paste full folder paths when prompted
- If a tool says a path does not exist, check for typo, quotes, or a missing drive letter

## Troubleshooting

### Nothing happens after choosing a tool

Make sure Python is available through `py` or through the `musicKeyConversion\.venv` environment used by the menu.

### A path is rejected

Make sure:

- The folder actually exists
- You pasted a folder path, not a file path, unless the tool explicitly asks for a file
- The path is accessible on your machine

### You are nervous about changing files

That is exactly when you should use preview mode first. Options 4 and 5 are designed so you can review the results before writing.
