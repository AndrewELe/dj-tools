# DJ Tools Quick Start

Main launcher:
`C:\dj_tools\dj_tools_menu.bat`

Run that file, then choose a number from the menu.

## Most Common Tasks

### 1. Make a New Crate Folder

Choose:
`1. Build new dated crate tree`

Enter:
The parent folder where you want the new crate created.

Example:
`D:\`

What it makes:

- A new dated crate folder like `sorted 3.22.26`
- A matching notables file

Use this when:
You are starting a fresh sorting session.

## 2. Clean Up Empty Folders

Choose:
`2. Clean / mark empty folders`

Enter:
The crate folder you want to clean.

When asked:
`Delete empty folders? (y/n)`

Pick:

- `y` if you want empty folders removed
- `n` if you want template folders kept and marked with ` (empty)` instead

Recommended:
Use `n` first unless you know you want full deletion.

## 3. Download / Crawl New Music

Choose:
`3. Run crate digger`

At startup:

- Press `Enter` to step through sources one by one
- Type `A` to run everything automatically
- Type `Q` to quit

While stepping:

- `Enter` = run this source
- `S` = skip this source
- `A` = auto-run the rest
- `Q` = quit

Recommended:
Use step mode if you want more control.

## 4. Convert Music Keys to Camelot

Choose:
`4. Camelot converter`

Use this when:
You want to convert key tags to Camelot, update the track title, and optionally rename files.

Safest first run:

1. Enter your music folder
2. Leave destination on default unless you need something else
3. Leave key source blank unless auto-detect is failing
4. Press `Enter` for preview mode
5. Leave verbose on

If the preview looks right:
Run it again and type `W` to write changes.

Recommended write settings:

- Backups: `Y`
- Rename files: `N` unless you really want renamed filenames
- Use `6` later if you want `.bak` files removed

## 5. Write Camelot Info Into Comments

Choose:
`5. Camelot to comments`

Use this when:
You want comments like:
`8A | Am | 128`

This also updates the track title to:
`8A | Am - Song Title`

Safest first run:

1. Enter your music folder
2. Leave key source blank unless needed
3. Press `Enter` for preview mode
4. Leave verbose on

If the preview looks right:
Run it again with `W` to write changes.

Recommended write settings:

- Backups: `Y`
- Use `6` later if you want `.bak` files removed

## 6. Delete `.bak` Backup Files

Choose:
`6. Clean .bak files`

Then:
Enter the folder path you want scanned recursively.

If you just press Enter:
It defaults to `C:\dj_tools\musicKeyConversion`

Use this when:
You are sure you no longer need the `.bak` backup files.

## 7. Generate Rekordbox XML

Choose:
`7. Rekordbox XML generator`

Use this when:
You want to turn a folder tree like `Root / Genre / high|mid|low / tracks` into a Rekordbox-importable XML playlist structure.

What it does:

- Prompts for your music root folder
- Scans the folder tree
- Creates a revisioned XML file in that root folder
- Creates a matching log file in that root folder

Typical workflow:

1. Run Option `7`
2. Enter your music root folder
3. Let it generate the XML
4. Point Rekordbox to that XML in Preferences
5. Import the playlists inside Rekordbox

## Safe Defaults

If you are unsure:

- Preview before writing
- Keep backups on
- Use Option `6` later if you want backups removed
- Use step mode in crate digger if you want control

## Which Tool Should I Use?

Use `1` if you need a new sorting folder.

Use `2` if you want to clean empty folders after sorting.

Use `3` if you want to pull music from your crate-digger sources.

Use `4` if you want Camelot written to tags and maybe filenames.

Use `5` if you want Camelot plus key plus BPM written to comments only.

Use `6` if you want leftover `.bak` files removed.

Use `7` if you want a Rekordbox XML generated from your folder structure.

## Need More Detail?

Read the full guide here:
[README.md](c:\dj_tools\README.md)
