#!/usr/bin/env bash
#
# DJ Tools menu (macOS).
#
# This is the Mac equivalent of dj_tools_menu.bat. Double-click it in Finder
# (it has a .command extension so Terminal runs it) or run it from a shell:
#   ./dj_tools_menu.command
#
# It dispatches to the same Python tools used on Windows, plus Mac-native
# shell helpers for crate digger, discovery and dedupe.

set -u

# --- Resolve the directory this script lives in (handles symlinks/double-click).
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
cd "$ROOT_DIR" || exit 1

VENV_PY="$ROOT_DIR/musicKeyConversion/.venv/bin/python"

# --- Pick a system Python 3 interpreter.
pick_system_python() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        echo "python"
    else
        echo ""
    fi
}
SYS_PY="$(pick_system_python)"

# Python for tools that need mutagen (camelot tools). Prefer the venv.
musickey_python() {
    if [ -x "$VENV_PY" ]; then
        echo "$VENV_PY"
    else
        echo "$SYS_PY"
    fi
}

# --- Helpers ---------------------------------------------------------------

strip_quotes() {
    # Trim surrounding single/double quotes a user may have pasted in.
    local s="$1"
    s="${s%\"}"; s="${s#\"}"
    s="${s%\'}"; s="${s#\'}"
    echo "$s"
}

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

report_exit() {
    # $1 = label, $2 = exit code
    if [ "$2" != "0" ]; then
        echo
        echo "[WARN] $1 exited with code $2."
        echo "       Scroll up to see any error messages above."
    fi
}

return_to_menu() {
    echo
    read -r -p "Press Enter to return to the menu..." _
}

require_python() {
    if [ -z "$SYS_PY" ]; then
        echo
        echo "[ERROR] No 'python3' found on PATH."
        echo "        Install it (e.g. 'brew install python') or run ./setup.command first."
        return 1
    fi
    return 0
}

# --- Menu ------------------------------------------------------------------

while true; do
    clear
    echo "=========================================="
    echo "DJ Tools Menu (macOS)"
    echo "=========================================="
    echo
    echo "1. Build / update genre folders"
    echo "2. Clean / mark empty folders"
    echo "3. Run crate digger"
    echo "4. Dedupe audio (find duplicate MP3s)"
    echo "5. Camelot converter"
    echo "6. Camelot to comments"
    echo "7. Encode WAV to MP3 (single file)"
    echo "8. Rekordbox XML generator"
    echo "9. Update command-line tools"
    echo "10. Find or redownload a missing track"
    echo "11. Exit"
    echo
    read -r -p "Choose an option (1-11, or Q to quit): " CHOICE
    CHOICE_L="$(lower "$CHOICE")"

    case "$CHOICE_L" in
        q|11) exit 0 ;;

        1)  # Build / update genre folders
            clear
            echo "=========================================="
            echo "Build / Update Genre Folders"
            echo "=========================================="
            echo
            echo "Creates any missing genre folders in your music library and offers"
            echo "to move tracks out of old dated \"sorted\" folders into them."
            echo
            read -r -p "Enter your music library folder (example: /Volumes/USB), or Q to return to menu: " P
            P="$(strip_quotes "$P")"
            [ "$(lower "$P")" = "q" ] && continue
            if [ -z "$P" ]; then echo; echo "No path entered."; return_to_menu; continue; fi
            require_python || { return_to_menu; continue; }
            echo
            "$SYS_PY" "$ROOT_DIR/create_folders/make_music_paths.py" "$P"
            report_exit "Build genre folders" $?
            return_to_menu
            ;;

        2)  # Clean / mark empty folders
            clear
            echo "=========================================="
            echo "Clean / Mark Empty Folders"
            echo "=========================================="
            echo
            read -r -p "Enter the folder to clean, or Q to return to menu: " P
            P="$(strip_quotes "$P")"
            [ "$(lower "$P")" = "q" ] && continue
            if [ -z "$P" ]; then echo; echo "No path entered."; return_to_menu; continue; fi
            require_python || { return_to_menu; continue; }
            echo
            "$SYS_PY" "$ROOT_DIR/create_folders/clean_empty_music_folders.py" "$P"
            report_exit "Clean folders" $?
            return_to_menu
            ;;

        3)  # Crate digger
            clear
            echo "=========================================="
            echo "Crate Digger"
            echo "=========================================="
            echo
            bash "$ROOT_DIR/crate-digger/digcrate.sh"
            report_exit "Crate digger" $?
            ;;

        4)  # Dedupe audio
            clear
            echo "=========================================="
            echo "Dedupe Audio"
            echo "=========================================="
            echo
            echo "Recursively fingerprints every .mp3 under the folder you provide"
            echo "and moves duplicates into a _dupes subfolder next to your music."
            echo
            read -r -p "Enter the folder path to scan recursively, or Q to return to menu: " P
            P="$(strip_quotes "$P")"
            [ "$(lower "$P")" = "q" ] && continue
            if [ -z "$P" ]; then echo; echo "No path entered."; return_to_menu; continue; fi
            require_python || { return_to_menu; continue; }
            echo
            "$SYS_PY" "$ROOT_DIR/crate-digger/dedupe_audio.py" "$P"
            report_exit "Dedupe audio" $?
            return_to_menu
            ;;

        5)  # Camelot converter
            clear
            echo "=========================================="
            echo "Camelot Converter"
            echo "=========================================="
            echo
            echo "This tool reads the musical key from your files, converts it to Camelot,"
            echo "and can save that value into a tag, update the track title, and optionally rename the filename."
            echo
            read -r -p "Enter the root music folder to scan, or Q to return to menu: " MUSIC
            MUSIC="$(strip_quotes "$MUSIC")"
            [ "$(lower "$MUSIC")" = "q" ] && continue
            if [ -z "$MUSIC" ]; then echo; echo "No folder entered."; return_to_menu; continue; fi

            DEST_ARG="--dest comment"
            WRITE_ARGS=""
            RENAME_ARGS=""
            VERBOSE_ARG="--verbose"

            echo
            echo "Where should the Camelot value be saved?"
            echo "  1. Comment tag (best default for most users)"
            echo "  2. Grouping tag"
            echo "  3. Custom CAMELOT tag"
            read -r -p "Choose where to save it (1-3, default 1, or Q to return to menu): " DEST_CHOICE
            [ "$(lower "$DEST_CHOICE")" = "q" ] && continue
            [ "$DEST_CHOICE" = "2" ] && DEST_ARG="--dest grouping"
            [ "$DEST_CHOICE" = "3" ] && DEST_ARG="--dest custom"

            echo
            read -r -p "Press Enter for a safe preview only, type W to write, or Q to return to menu: " WRITE_CHOICE
            [ "$(lower "$WRITE_CHOICE")" = "q" ] && continue
            [ "$(lower "$WRITE_CHOICE")" = "w" ] && WRITE_ARGS="--write"

            echo
            echo "Filename rename format: Camelot | Key | BPM - Artist - Title"
            echo "The track title tag is also updated to: Camelot | Key - Title"
            read -r -p "Also rename the files? (Y/N, default N, or Q to return to menu): " RENAME_CHOICE
            [ "$(lower "$RENAME_CHOICE")" = "q" ] && continue
            [ "$(lower "$RENAME_CHOICE")" = "y" ] && RENAME_ARGS="--rename"

            read -r -p "Show detailed output? (Y/N, default Y, or Q to return to menu): " VERBOSE_CHOICE
            [ "$(lower "$VERBOSE_CHOICE")" = "q" ] && continue
            [ "$(lower "$VERBOSE_CHOICE")" = "n" ] && VERBOSE_ARG=""

            echo
            PY="$(musickey_python)"
            if [ -z "$PY" ]; then echo "[ERROR] No Python found. Run ./setup.command first."; return_to_menu; continue; fi
            "$PY" "$ROOT_DIR/musicKeyConversion/camelot_converter.py" "$MUSIC" $DEST_ARG $WRITE_ARGS $RENAME_ARGS $VERBOSE_ARG
            report_exit "Camelot converter" $?
            return_to_menu
            ;;

        6)  # Camelot to comments
            clear
            echo "=========================================="
            echo "Camelot To Comments"
            echo "=========================================="
            echo
            echo "This tool reads each file's musical key, converts it to Camelot,"
            echo "writes Camelot | musical key | BPM into the comment tag,"
            echo "and updates the track title to Camelot | musical key - Title."
            echo
            read -r -p "Enter the root music folder to scan, or Q to return to menu: " MUSIC
            MUSIC="$(strip_quotes "$MUSIC")"
            [ "$(lower "$MUSIC")" = "q" ] && continue
            if [ -z "$MUSIC" ]; then echo; echo "No folder entered."; return_to_menu; continue; fi

            WRITE_ARGS=""
            VERBOSE_ARG="--verbose"

            echo
            read -r -p "Press Enter for a safe preview only, type W to write, or Q to return to menu: " WRITE_CHOICE
            [ "$(lower "$WRITE_CHOICE")" = "q" ] && continue
            [ "$(lower "$WRITE_CHOICE")" = "w" ] && WRITE_ARGS="--write"

            read -r -p "Show detailed output? (Y/N, default Y, or Q to return to menu): " VERBOSE_CHOICE
            [ "$(lower "$VERBOSE_CHOICE")" = "q" ] && continue
            [ "$(lower "$VERBOSE_CHOICE")" = "n" ] && VERBOSE_ARG=""

            echo
            PY="$(musickey_python)"
            if [ -z "$PY" ]; then echo "[ERROR] No Python found. Run ./setup.command first."; return_to_menu; continue; fi
            "$PY" "$ROOT_DIR/musicKeyConversion/camelot_to_comments.py" "$MUSIC" $WRITE_ARGS $VERBOSE_ARG
            report_exit "Camelot to comments" $?
            return_to_menu
            ;;

        7)  # Encode WAV to MP3
            clear
            echo "=========================================="
            echo "Encode WAV to MP3 (single file)"
            echo "=========================================="
            echo
            echo "Encodes one .wav file to .mp3 using LAME V0 VBR."
            echo "V0 is the best quality/size trade-off: practically transparent"
            echo "audio at roughly 25-30% smaller than 320 CBR."
            echo
            read -r -p "Enter the .wav file path, or Q to return to menu: " WAV
            WAV="$(strip_quotes "$WAV")"
            [ "$(lower "$WAV")" = "q" ] && continue
            if [ -z "$WAV" ]; then echo; echo "No file entered."; return_to_menu; continue; fi
            require_python || { return_to_menu; continue; }
            echo
            "$SYS_PY" "$ROOT_DIR/encoder/wav_to_mp3.py" "$WAV"
            report_exit "WAV to MP3" $?
            return_to_menu
            ;;

        8)  # Rekordbox XML generator
            clear
            echo "=========================================="
            echo "Rekordbox XML Generator"
            echo "=========================================="
            echo
            echo "This tool scans a Root/Genre/Energy/tracks folder structure"
            echo "and creates a Rekordbox-compatible XML plus a matching log file."
            echo
            require_python || { return_to_menu; continue; }
            "$SYS_PY" "$ROOT_DIR/xml_generator/rekordbox_xml_generator.py"
            report_exit "Rekordbox XML generator" $?
            return_to_menu
            ;;

        9)  # Update command-line tools
            clear
            echo "=========================================="
            echo "Update Command-Line Tools"
            echo "=========================================="
            echo
            echo "Checks for newer versions of yt-dlp and mutagen."
            echo "(ffmpeg, ffprobe, and fpcalc are managed by Homebrew:"
            echo "  brew upgrade ffmpeg chromaprint)"
            echo
            echo "--- yt-dlp ---"
            if command -v brew >/dev/null 2>&1 && brew list yt-dlp >/dev/null 2>&1; then
                brew upgrade yt-dlp
            elif command -v yt-dlp >/dev/null 2>&1; then
                yt-dlp -U || echo "[SKIP] yt-dlp self-update not available for this install."
            else
                echo "[SKIP] yt-dlp not found. Install with 'brew install yt-dlp'."
            fi
            echo
            echo "--- mutagen (Python package) ---"
            if [ -x "$VENV_PY" ]; then
                "$VENV_PY" -m pip install --upgrade mutagen
            elif [ -n "$SYS_PY" ]; then
                "$SYS_PY" -m pip install --upgrade mutagen
            else
                echo "[SKIP] No Python found to upgrade mutagen."
            fi
            echo
            report_exit "Update tools" $?
            return_to_menu
            ;;

        10) # Find or redownload a missing track
            clear
            echo "=========================================="
            echo "Find Or Redownload A Missing Track"
            echo "=========================================="
            echo
            echo "Searches the folder you provide recursively for a track whose"
            echo "filename contains the name you type (case-insensitive). If no"
            echo "match is found locally, lists matching tracks from your SoundCloud"
            echo "likes and lets you redownload them into a 'lost tracks' subfolder."
            echo
            read -r -p "Enter the track name to find, or Q to return to menu: " TRACK
            TRACK="$(strip_quotes "$TRACK")"
            [ "$(lower "$TRACK")" = "q" ] && continue
            if [ -z "$TRACK" ]; then echo; echo "No track name entered."; return_to_menu; continue; fi
            read -r -p "Enter the folder to search recursively, or Q to return to menu: " FOLDER
            FOLDER="$(strip_quotes "$FOLDER")"
            [ "$(lower "$FOLDER")" = "q" ] && continue
            if [ -z "$FOLDER" ]; then echo; echo "No folder entered."; return_to_menu; continue; fi
            require_python || { return_to_menu; continue; }
            echo
            "$SYS_PY" "$ROOT_DIR/crate-digger/find_or_redownload.py" --track-name "$TRACK" --search-folder "$FOLDER"
            report_exit "Find or redownload track" $?
            return_to_menu
            ;;

        *)
            echo
            echo "Invalid choice."
            return_to_menu
            ;;
    esac
done
