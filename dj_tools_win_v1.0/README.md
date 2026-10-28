
# DJ Tools README

This folder contains a small menu-driven toolkit for DJ library work.

Main launcher:
`C:\dj_tools\dj_tools_menu.bat`

Open that batch file to launch the menu, then choose one of the numbered options.

## What This Toolkit Does

The menu currently includes:

1. Build / update genre folders
2. Clean / mark empty folders
3. Run crate digger
4. Dedupe audio (find duplicate MP3s)
5. Camelot converter
6. Camelot to comments
7. Encode WAV to MP3 (single file)
8. Rekordbox XML generator
9. Update command-line tools
10. Find or redownload a missing track
11. Exit

## Basic Usage

1. Run `dj_tools_menu.bat`.
2. Type the number of the tool you want.
3. Answer the prompts shown in the terminal.
4. Press Enter when prompted to return to the main menu.

If a prompt asks for a path, you can paste the folder path directly. Paths wrapped in double quotes are also accepted, e.g. `"E:\my music"`.

## Prompt Conventions

Every prompt across every tool accepts `Q` to return to the main menu without making changes. This includes:

- The main menu option prompt
- Every path-entry prompt
- Every Y/N or write/preview prompt inside the tools
- The startup prompt for crate digger and its per-source step prompts
- The optional prompts inside `Clean / mark empty folders`

If you type `Q` at any point, the tool stops, no files are modified, and you are returned to the main menu.

## Menu Option 1: Build / Update Genre Folders

Purpose:
Sets up your music library as numbered genre folders, one click from the root of the USB stick, so you can pick a genre straight from the CDJ folder browser. Also creates a notables text file for the session.

What it asks for:
`Enter your music library folder (example: E:\ for a USB stick), or Q to return to menu`

What you should enter:
The folder that holds (or will hold) your genre folders, usually the root of your USB stick.

Example:
`E:\`

Folder structure it creates:

```
00 new                   11 prog trance
01 downtempo, organic    12 trance
02 afro house            13 ukg, bass house
03 deep house            14 dubstep
04 melodic house         15 trap
05 prog house            16 hard techno
06 house                 17 hard dance
07 tech house            18 hardstyle
08 minimal, deep tech    19 dnb
09 breaks                20 happy hardcore
10 techno                21 other
```

- Genres are numbered slowest to fastest, so the list on the CDJ follows how a set builds
- Every genre folder has energy subfolders: `high`, `mid`, `low`
- `00 new` is the inbox for new tracks you haven't filed yet
- Only missing folders are created, so it is safe to run again at any time
- Folders renamed to ` (empty)` by Option 2 count as already there

Moving tracks out of old folders:
If the library still has old dated `sorted 3.22.26` folders (or genre folders from an older numbering), it previews where every track would go and asks before moving anything:

- `sorted 3.22.26/house/deep house/high` goes to `03 deep house/high`
- `uk bass` goes to `13 ukg, bass house`, `to organize` goes to `00 new`
- A track whose name is already taken at the destination is left where it is
- Tracks filed straight into `progressive/` (not `progressive house` or `progressive trance`) are left where they are for you to place
- Folders left empty by the move are removed

The same move can be run on its own, for example to move old folders from your computer onto the USB stick:
`py create_folders\migrate_old_folders.py "C:\Music\old crates" E:\`

Changing the genres:
The genre list lives in `create_folders\genre_layout.py`. Edit the `GENRES` list there and every tool picks it up. The numbers follow the order of the list, and running Option 1 again moves tracks into the renumbered folders.

What the notables file is for:
A template named like `03.22.2026 notables.txt`, created in the library folder, where you can jot down standout tracks by genre.

Good time to use this:
When setting up a new USB stick, after changing the genre list, or when starting a fresh sorting session.

## Menu Option 2: Clean / Mark Empty Folders

Purpose:
Scans a crate folder and helps you clean up empty folders.

What it asks for first:
`Enter the folder to clean, or Q to return to menu`

Use this on:
Your music library folder (the one holding the numbered genre folders).

Then it asks:
`Delete empty folders? (y/n, or Q to return to menu)`

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
`Proceed with these folder changes? (y/n, or Q to return to menu)`

Then it optionally asks:
`Create a pruned notables file with only genres that have music? (y/n, or Q to return to menu)`

What that does:
Creates a `.pruned` version of the most recently edited notables file in the library folder, keeping only sections for genres that contain music.

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

What happens when it starts:
You are asked how you want the run to behave.

Startup controls:

- `Enter` = step through each source one by one
- `A` = automatic mode, run through everything without pausing
- `Q` = return to main menu now

Connectivity checks:
Before source processing begins, the tool checks general internet reachability and SoundCloud reachability.

If a warning appears:
The checks are warnings, not hard stops. You can choose:

- `C` = continue into crate digger anyway
- `M` = return to the main menu
- `Q` = return to main menu

What this means:

- A ping warning can happen on networks that block ICMP even when downloads still work
- A SoundCloud warning means SoundCloud sources may fail, but other sources can still work

While stepping through sources:

- `Enter` = run this source
- `S` = skip this source
- `A` = switch to auto-run for the rest
- `Q` = return to main menu

While auto-running:
After each source finishes downloading, a 2-second prompt appears:
`Press Q to stop after this source (continuing in 2s)`

- If you press `Q` during that window — or during the download itself, since the keypress is buffered — the run stops cleanly after the current source completes, and you return to the main menu.
- If you press nothing, the next source begins automatically.

What it processes:

- Main sources from `sources.txt`
- Crawler seeds from `crawler.txt`
- Discovered sources from `discovered_sources.txt`

To dedupe duplicate MP3s after a crate digger run, use Menu Option 4.

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
Before downloads start, the script checks that the music output root exists and is writable.

Default output root:
`C:\Music\SoundCloud`

Optional override:
Set the environment variable `DJTOOLS_MUSIC_ROOT` before launching if you want downloads and dedupe to use a different writable folder.

Good time to use this:
When you want to pull new music from your saved source lists.

## Menu Option 4: Dedupe Audio

Purpose:
Recursively fingerprints every `.mp3` under a folder you choose and moves duplicates into a `_dupes` subfolder at the root of that folder.

What it asks for:
`Enter the folder path to scan recursively, or Q to return to menu`

What it does:

- Fingerprints every `.mp3` under the folder using `fpcalc.exe` (Chromaprint)
- The first file with a given fingerprint stays where it is
- Every subsequent file with the same fingerprint is moved to `<folder>\_dupes\`
- If a file with the same name already exists in `_dupes`, the new one gets a `__dup_N` suffix appended

What it does not do:

- It never deletes anything. You can review `_dupes` and remove or restore files manually.
- It only inspects `.mp3` files. Other formats are ignored.

When to use it:
After a crate digger run, or any time you want to find duplicate MP3s in a folder tree.

Important note:
Which copy stays in place is determined by the recursive scan order, which is roughly alphabetical by path.

## Menu Option 5: Camelot Converter

Purpose:
Reads each audio file's musical key, converts it to Camelot notation, writes the result to a tag, updates the track title, and can optionally rename files.

What file types it works with:

- MP3
- FLAC
- MP4 / M4A
- AIFF / AIF

What it asks for first:
`Enter the root music folder to scan, or Q to return to menu`

Use this on:
The top-level folder that contains the music files you want to process.

### Destination Choice

Prompt:
`Choose where to save it (1-3, default 1, or Q to return to menu)`

Options:

- `1` = save Camelot into the comment tag
- `2` = save Camelot into the grouping tag
- `3` = save Camelot into a custom tag named `CAMELOT`

If you want a custom tag with a different name, you can run the Python script directly with `--custom-name "YOURTAG"` (see `musicKeyConversion/cam_conv_readme.txt`).

### Preview vs Write

Prompt:
`Press Enter for a safe preview only, type W to write, or Q to return to menu`

What this means:

- Press `Enter` = dry run only, no file changes
- Type `W` = actually write tags

Recommended first run:
Use preview mode first.

### Rename Option

Prompt:
`Also rename the files? (Y/N, default N, or Q to return to menu)`

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
`Show detailed output? (Y/N, default Y, or Q to return to menu)`

Meaning:

- `Y` or Enter = show detailed progress
- `N` = quieter output

### Advanced Options

The menu intentionally hides the rarer options. If you need them, run the Python script directly:

- `--source-field TKEY` to force a specific key tag instead of auto-detect
- `--custom-name MYTAG` to choose the name of the custom destination tag
- `--show-map` to print the 24-key Camelot mapping table before processing

See `musicKeyConversion/cam_conv_readme.txt` for full CLI usage.

Best use case:
Use this when you want Camelot values written somewhere useful in the tags and possibly at the start of filenames.

Safer first-time recommendation:

1. Run in preview mode first
2. If the results look good, run again with `W`

## Menu Option 6: Camelot To Comments

Purpose:
Reads the musical key from each file, converts it to Camelot, reads BPM, and writes this format into the comment tag:

`Camelot | musical key | BPM`

Example comments:

- `8A | Am | 128`
- `5A | Cm | 140`
- `2B | F# | 174`

Main difference from Option 5:

- Option 5 can write Camelot to different tag destinations and can rename files
- Option 6 always writes the comment field in the combined format above and keeps filenames unchanged

What it asks for:

- Root music folder (`or Q to return to menu`)
- Preview vs write (`Enter` / `W` / `Q`)
- Verbose output (`Y/N/Q`)

Track title update:
When you write changes, this tool also updates the title tag to:
`Camelot | Musical Key - Title`

### Advanced Options

Run the Python script directly (`musicKeyConversion/camelot_to_comments.py`) to access:

- `--source-field TKEY` to force a specific key tag instead of auto-detect
- `--show-map` to print the 24-key Camelot mapping table before processing

See `musicKeyConversion/cam2comm_readme.txt` for full CLI usage.

Best use case:
Use this when you want a clean, Rekordbox-friendly comment format without changing filenames.

Safer first-time recommendation:
Run a preview first, then run again with write enabled if the output looks correct.

## Menu Option 7: Encode WAV to MP3

Purpose:
Encodes a single `.wav` file to `.mp3` using LAME V0 VBR.

Why V0 VBR:
V0 is the standard "best quality / smallest size" preset for MP3. It produces practically transparent audio while typically being 25-30% smaller than 320 CBR. Bitrate varies between roughly 220 and 260 kbps depending on the complexity of the audio at each moment.

Trade-off note:
"High bitrate" and "small file" are the same dial — they cannot both be maximized. V0 picks the best practical balance for DJ use.

What it asks for:
`Enter the .wav file path, or Q to return to menu`

What you should enter:
The full path to one `.wav` file.

What it does:

- Encodes that single file to `.mp3` using `ffmpeg -codec:a libmp3lame -q:a 0`
- Saves the `.mp3` next to the original `.wav` with the same base name
- If a matching `.mp3` already exists, appends ` (2)`, ` (3)`, etc. so nothing is overwritten
- Copies WAV metadata into the MP3 when present
- Keeps the original `.wav` file untouched

What it prints when done:

- The original WAV path and size
- The new MP3 path and size
- The size savings percentage

What it uses:
The bundled `crate-digger\ffmpeg.exe`. If that's missing, it falls back to any `ffmpeg` on your PATH.

Good time to use this:
When you have a single high-quality `.wav` (for example, exported from a stem editor or DAW) and want a small DJ-ready `.mp3` from it.

### Automatic yt-dlp updates

Crate digger automatically checks for newer `yt-dlp.exe` releases at most once per week. On the first run of each week, it runs `yt-dlp -U` before processing sources and writes a small `.last_update_check` stamp into `crate-digger\` to avoid checking again until the stamp is 7+ days old.

If the update fails (no internet, GitHub down), the stamp is still touched so the broken check doesn't repeat every run; you'll just stay on the current version until next week's check. The `--no-update` flag is also passed to every per-source `yt-dlp` invocation so the staleness warning never appears during normal use.

To force an update before the weekly window, use Menu Option 9 (Update command-line tools).

## Menu Option 8: Rekordbox XML Generator

Purpose:
Scans a structured music folder and creates a Rekordbox-compatible XML file plus a matching log file.

Expected folder structure:
`Root / Genre / (high|mid|low) / tracks`

What happens:
This launches `xml_generator\rekordbox_xml_generator.py`.

What it asks for:

1. Scan mode (`1` for your music library, `2` for a parent folder containing several libraries such as old dated `sorted` folders, or `Q` to return to menu)
2. The folder path (or `Q` to return to menu)

What it creates:

- A revisioned XML file like `rekordbox_export_windows_rev1.xml`
- A matching log file like `rekordbox_export_windows_rev1.log`

Best use case:
When you want to generate playlist XML from your folder tree, point Rekordbox to that XML in Preferences, and then import the playlists into Rekordbox.

Important note:
This tool is read-only against your music files. It does not rename, move, or modify audio files.

## Menu Option 9: Update Command-Line Tools

Purpose:
Forces a check for updates to the command-line tools the menu depends on, on demand. Useful when you've just hit a "version is older than..." warning, or before a big crate-digger session.

What it updates:

- `yt-dlp.exe` — runs `yt-dlp -U` against the bundled binary in `crate-digger\`
- `mutagen` — runs `pip install --upgrade mutagen` inside the `musicKeyConversion\.venv` if it exists, otherwise against the system `py`

What it does NOT update:

- `ffmpeg.exe` / `ffprobe.exe` / `fpcalc.exe` — these are static binaries without a built-in self-updater. To update them, replace the files in `crate-digger\` with newer downloads from the official sources.

Side effect:
After a successful yt-dlp update, the weekly auto-update stamp (`crate-digger\.last_update_check`) is refreshed so crate digger doesn't immediately re-run an update you just did.

## Menu Option 10: Find Or Redownload A Missing Track

Purpose:
Searches a folder recursively for a track by name. If nothing matches locally, scans your SoundCloud likes for matching tracks and lets you redownload the ones you pick into a `lost tracks` subfolder.

What it asks for:

1. The track name (substring, case-insensitive). For example, `love letters` will match `Artist - Love Letters (Original Mix).mp3`.
2. The folder to search recursively, or `Q` to return to menu.

What it does:

- Walks the folder you provide and inspects every audio file (`.mp3`, `.flac`, `.wav`, `.aiff`, `.aif`, `.m4a`).
- A filename is considered a match if the lowercased track name is a substring of the lowercased filename stem.
- If at least one local match is found, it prints the path(s) and exits — no download.
- If nothing matches locally, it runs `yt-dlp --flat-playlist` against your SoundCloud likes (`https://soundcloud.com/druleprivate/likes`) and filters titles by the same substring.
  - This step can take 10-30 seconds for a large likes list. yt-dlp's progress prints while it works.
- If matches are found in likes, they are printed numbered, e.g.:

      1. druleprivate - Love Letters (Original Mix)
         https://soundcloud.com/...

  You can pick a single number, a comma list (`1,3`), `all`, or `Q` to return.
- Picked tracks are downloaded with the same audio extraction / metadata embedding rules used elsewhere in the toolkit, into `<your search folder>\lost tracks\`.

What it does NOT do:

- It does not look at the rest of `sources.txt` or `crawler.txt`. Only `druleprivate/likes` is searched.
- It does not delete or overwrite anything. The download archive (`crate-digger\archive.txt`) is bypassed so even tracks you previously downloaded but lost will redownload.

When to use it:

- You know a specific track used to be in your library but cannot find it now.
- A crate-digger run finished and you suspect one track is missing — you remember the name but not where it should be.

## Menu Option 11: Exit

Purpose:
Closes the menu. You can also press `Q` at the main menu prompt instead.

## Recommended Workflows

### For a New Sorting Session

1. Use Option 1 on your library to make sure every genre folder exists
2. Sort new tracks from `00 new` into the genre and energy folders
3. Use Option 2 to clean or mark empty folders
4. Optionally create a pruned notables file

### For Key Tagging Safely

1. Use Option 5 or 6
2. Run a preview first
3. If the output looks correct, run again with write enabled

### For Pulling New Music

1. Use Option 3 to download from your source lists
2. Step through sources if you want control, or use auto mode if you want a hands-off run
3. Use Option 4 afterward to dedupe the downloaded MP3s

### For Rekordbox XML Playlist Import

1. Use Option 8
2. Enter the root folder that contains your genre folders
3. Let the tool generate the XML and log in that same root folder
4. Point Rekordbox to the generated XML in Preferences
5. Import playlists from the XML inside Rekordbox

### For Quick WAV → MP3 Conversion

1. Use Option 7
2. Enter the path to a single `.wav` file
3. The encoded `.mp3` lands next to the original; the WAV is preserved

## Tips

- If you are unsure, choose preview mode before writing or deleting anything
- Paste full folder paths when prompted; surrounding double quotes are stripped
- If a tool says a path does not exist, check for typo, quotes, or a missing drive letter
- You can always press `Q` at any prompt to return to the main menu without making changes

## Troubleshooting

### Nothing happens after choosing a tool

Make sure Python is available through `py` or through the `musicKeyConversion\.venv` environment used by the menu.

### A path is rejected

Make sure:

- The folder actually exists
- You pasted a folder path, not a file path, unless the tool explicitly asks for a file
- The path is accessible on your machine

### A script exited with a warning code

The menu now prints `[WARN] <tool> exited with code N` if a tool fails. Scroll up to see the actual error message. Press Enter to return to the menu and try again or fix the underlying issue.

### You are nervous about changing files

That is exactly when you should use preview mode first. Options 5 and 6 are designed so you can review the results before writing.
