# DJ Tools (macOS)

This is the macOS port of the DJ Tools toolkit. It provides the same
menu-driven tools as the Windows version, rebuilt to run natively on a Mac
using `bash`/`zsh`, Python 3, and Homebrew-installed command-line tools.

The Windows version lives in `../dj_tools_win_v1.0`. The tools and behavior
are intentionally kept the same; only the launchers and the way external
binaries are located differ.

## What's different from the Windows version

| Windows | macOS |
|---|---|
| `dj_tools_menu.bat` | `dj_tools_menu.command` (double-clickable in Finder) |
| `crate-digger/digcrate.bat` | `crate-digger/digcrate.sh` |
| `crate-digger/discover.ps1` | `crate-digger/discover.sh` |
| `crate-digger/dedupe_audio.ps1` | `crate-digger/dedupe_audio.py` |
| Bundled `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe`, `fpcalc.exe` | Installed via Homebrew, found on `PATH` |
| Default music root `C:\Music\SoundCloud` | Default music root `~/Music/SoundCloud` |

The Python tools (folder builder, cleaner, Camelot converters, Rekordbox XML
generator, WAV→MP3 encoder, find/redownload) are the **same code** as Windows,
with only the bundled-binary filenames made platform-aware.

## Requirements

- macOS with [Homebrew](https://brew.sh)
- Python 3 (`brew install python` if you don't have it)
- Command-line tools, installed via Homebrew:
  - `yt-dlp` — downloading (crate digger, find/redownload)
  - `ffmpeg` — audio extraction and WAV→MP3 (also pulls in `ffprobe`)
  - `chromaprint` — provides `fpcalc` for audio dedupe

## First-time setup

From this folder, run the setup helper. It checks for the Homebrew tools,
offers to install any that are missing, and creates a Python virtual
environment with `mutagen` for the key-tagging tools:

```bash
cd dj_tools_mac_v1.0
chmod +x setup.command dj_tools_menu.command crate-digger/digcrate.sh crate-digger/discover.sh   # first time only
./setup.command
```

Or install the tools manually:

```bash
brew install yt-dlp ffmpeg chromaprint python
python3 -m venv musicKeyConversion/.venv
musicKeyConversion/.venv/bin/python -m pip install mutagen
```

> **Gatekeeper note:** the first time you double-click a `.command` file,
> macOS may warn it's from an unidentified developer. Right-click the file →
> **Open** → **Open**, or run it from Terminal as shown above.

## Running

```bash
./dj_tools_menu.command
```

or double-click `dj_tools_menu.command` in Finder.

Then choose a numbered option. As on Windows, you can type `Q` at (almost) any
prompt to back out to the main menu without making changes.

## Menu options

1. Build new dated crate tree
2. Clean / mark empty folders
3. Run crate digger
4. Dedupe audio (find duplicate MP3s)
5. Camelot converter
6. Camelot to comments
7. Encode WAV to MP3 (single file)
8. Rekordbox XML generator
9. Update command-line tools (`brew upgrade yt-dlp`, upgrade `mutagen`)
10. Find or redownload a missing track
11. Exit

For full per-tool documentation, see the Windows `README.md` in
`../dj_tools_win_v1.0/README.md` — the tool behavior is identical. The only
practical differences are the launch method and the paths you type (use
macOS-style paths like `~/Music` or `/Volumes/USB Drive` instead of `D:\`).

## Music download location

Crate digger and dedupe default to `~/Music/SoundCloud`. To use a different
folder, set `DJTOOLS_MUSIC_ROOT` before launching:

```bash
export DJTOOLS_MUSIC_ROOT="/Volumes/DJ SSD/SoundCloud"
./dj_tools_menu.command
```

## Updating the tools

- `yt-dlp`: `brew upgrade yt-dlp` (or menu option 9). Crate digger also runs a
  weekly check automatically.
- `ffmpeg` / `chromaprint`: `brew upgrade ffmpeg chromaprint`.
- `mutagen`: menu option 9, or
  `musicKeyConversion/.venv/bin/python -m pip install --upgrade mutagen`.
