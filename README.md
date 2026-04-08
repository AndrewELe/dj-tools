
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
7. Rekordbox XML generator
8. Exit

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

Connectivity checks:
Before source processing begins, the tool checks general internet reachability and SoundCloud reachability.

If a warning appears:
The checks are warnings, not hard stops. You can choose:

- `C` = continue into crate digger anyway
- `M` = return to the main menu

What this means:

- A ping warning can happen on networks that block ICMP even when downloads still work
- A SoundCloud warning means SoundCloud sources may fail, but other sources can still work

While stepping through sources:

- `Enter` = run this source
- `S` = skip this source
- `A` = switch to auto-run for the rest
- `Q` = quit the session

What it processes:

- Main sources from `sources.txt`
- Crawler seeds from `crawler.txt`
- Discovered sources from `discovered_sources.txt`

### Crate Digger File Map

These are the main files you may want to edit:

- `C:\dj_tools\crate-digger\sources.txt`
  Main download list. Every non-empty line that does not start with `#` is processed as a source URL.
- `C:\dj_tools\crate-digger\crawler.txt`
  Extra source list that is also downloaded directly, and is also used as a seed list for discovery.
- `C:\dj_tools\crate-digger\discover.ps1`
  Discovery script. It reads `sources.txt` and `crawler.txt`, asks `yt-dlp` for related repost URLs, and writes the cleaned results into `discovered_sources.txt`.
- `C:\dj_tools\crate-digger\discovered_sources.txt`
  Auto-generated list of discovered sources created by `discover.ps1`. After discovery runs, `digcrate.bat` also downloads from this file.
- `C:\dj_tools\crate-digger\digcrate.bat`
  Main controller for crate digger. This is where the per-source download cap is currently set.
- `C:\dj_tools\crate-digger\yt-dlp.conf`
  Shared `yt-dlp` rules such as audio extraction, metadata embedding, playlist order, and the 10-minute / title filters.

Important detail:
The crate digger keeps the 5-track limit for normal sources and discovered sources, but `https://soundcloud.com/druleprivate/likes` is treated as a full-download source and is not capped at 5 tracks.

### How To Change How Many Songs Download Per Source

Right now, the number of tracks per source is controlled in:

- `C:\dj_tools\crate-digger\digcrate.bat`
- `C:\dj_tools\crate-digger\discover.ps1`

What to change in `digcrate.bat`:

- Find:
  `set "PLAYLIST_ARGS=--playlist-end 5"`
- Change `5` to the number you want for normal sources.

Example:

- `set "PLAYLIST_ARGS=--playlist-end 10"`

What that changes:

- `sources.txt` entries will download up to that many tracks
- `crawler.txt` entries will download up to that many tracks
- `discovered_sources.txt` entries will download up to that many tracks

Special case in `digcrate.bat`:

- The URL `https://soundcloud.com/druleprivate/likes` is defined as:
  `set "FULL_DOWNLOAD_URL=https://soundcloud.com/druleprivate/likes"`
- That one source ignores the per-source cap because the batch file clears `PLAYLIST_ARGS` for it.

If you want that source capped too:

- Edit `C:\dj_tools\crate-digger\digcrate.bat`
- In the `:GET_PLAYLIST_ARGS` section, remove or change these lines:
  `if /I "%TARGET_URL%"=="%FULL_DOWNLOAD_URL%" set "PLAYLIST_ARGS="`
  `if /I "%TARGET_URL%"=="%FULL_DOWNLOAD_URL%/" set "PLAYLIST_ARGS="`

What to change in `discover.ps1`:

- Find:
  `--playlist-end 5`
- Change `5` to the same number you want discovery to inspect per seed source.

Why this second edit matters:

- `discover.ps1` only inspects the first 5 items from each seed source when building `discovered_sources.txt`
- If you raise the limit in `digcrate.bat` but not in `discover.ps1`, discovery still only looks at 5 items per seed

Recommendation:

- Keep the number the same in both files unless you specifically want different behavior for discovery vs downloads

### How To Add Or Delete Sources

To add or remove your normal source list:

- Edit `C:\dj_tools\crate-digger\sources.txt`
- Put one source URL on each line
- Blank lines are ignored
- Lines starting with `#` are treated as comments

Example:

```txt
# Main sources
https://soundcloud.com/examplelabel
https://soundcloud.com/exampledj/likes
```

To add or remove crawler seed sources:

- Edit `C:\dj_tools\crate-digger\crawler.txt`
- Use the same one-URL-per-line format

What `crawler.txt` does differently:

- Its URLs are downloaded directly during the crate digger run
- Those same URLs are also fed into `discover.ps1` as discovery seeds

To remove a source:

- Delete its line from `sources.txt` or `crawler.txt`
- Or put `#` at the start of the line to disable it without deleting it

Example:

```txt
# https://soundcloud.com/exampledj/likes
```

About `discovered_sources.txt`:

- This file is rebuilt by `discover.ps1`
- You usually should not treat it as your master source list
- If you want to stop seeing a discovered source long-term, remove or change the parent sources in `sources.txt` and `crawler.txt`, or adjust the discovery logic in `discover.ps1`

Download root:
Before downloads start, the script now checks that the music output root exists and is writable.

Default output root:
`C:\Music\SoundCloud`

Optional override:
Set the environment variable `DJTOOLS_MUSIC_ROOT` before launching if you want downloads and dedupe to use a different writable folder.

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
Reads each audio file's musical key, converts it to Camelot notation, writes the result to a tag, updates the track title, and can optionally rename files.

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

Track title update:
When you write changes, the title tag is also updated to:
`Camelot | Musical Key - Title`

Example:
`9A | Em - Sunday Sunrise`

Rename preview:
In both preview mode and write mode, the tool shows the current filename and the built-in target filename before the rename happens.

Example:
- `OLD: Artist - Title.mp3`
- `NEW: 8A | Am | 128 - Artist - Title.mp3`

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
- Verbose output
- Show Camelot map

What the prompts mean:
They work the same way as in Option 4, except there is no rename section.

Track title update:
When you write changes, this tool also updates the title tag to:
`Camelot | Musical Key - Title`

Best use case:
Use this when you want a clean, Rekordbox-friendly comment format without changing filenames.

Safer first-time recommendation:
Run a preview first, then run again with write enabled if the output looks correct.

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

## Menu Option 7: Rekordbox XML Generator

Purpose:
Scans a structured music folder and creates a Rekordbox-compatible XML file plus a matching log file.

Expected folder structure:
`Root / Genre / (high|mid|low) / tracks`

What happens:
This launches `xml_generator\rekordbox_xml_generator.py`.

What it asks for:
`Enter the music root folder path (or 'q' to quit)`

What to enter:
The top-level folder that contains your genre folders.

What it creates:

- A revisioned XML file like `rekordbox_export_windows_rev1.xml`
- A matching log file like `rekordbox_export_windows_rev1.log`

Best use case:
Use this when you want to generate playlist XML from your folder tree, point Rekordbox to that XML in Preferences, and then import the playlists into Rekordbox.

Important note:
This tool is read-only against your music files. It does not rename, move, or modify audio files.

## Menu Option 8: Exit

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

### For Pulling New Music

1. Use Option 3
2. Step through sources if you want control
3. Use auto mode if you want a hands-off run
4. Run dedupe at the end if needed

### For Rekordbox XML Playlist Import

1. Use Option 7
2. Enter the root folder that contains your genre folders
3. Let the tool generate the XML and log in that same root folder
4. Point Rekordbox to the generated XML in Preferences
5. Import playlists from the XML inside Rekordbox

## Tips

- If you are unsure, choose preview mode before writing or deleting anything
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

=======
### You are nervous about changing files

That is exactly when you should use preview mode first. Options 4 and 5 are designed so you can review the results before writing.
