#!/usr/bin/env bash
#
# Crate digger (macOS) -- the Mac equivalent of digcrate.bat.
#
# Downloads tracks from sources.txt, crawler.txt and discovered_sources.txt
# using yt-dlp, runs the discovery crawler, and respects a per-source cap.
#
# Requires yt-dlp on PATH (brew install yt-dlp). ffmpeg is needed by yt-dlp
# for audio extraction (brew install ffmpeg).

set -u

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR" || exit 1

MODE="STEP"
STARTTIME="$(date '+%H:%M:%S')"

# yt-dlp: prefer a bundled binary next to this script, else use PATH.
if [ -x "$SCRIPT_DIR/yt-dlp" ]; then
    YTDLP="$SCRIPT_DIR/yt-dlp"
elif command -v yt-dlp >/dev/null 2>&1; then
    YTDLP="$(command -v yt-dlp)"
else
    YTDLP=""
fi

YTDLPCONF="$SCRIPT_DIR/yt-dlp.conf"
DISCOVER_SH="$SCRIPT_DIR/discover.sh"
SOURCES_FILE="$SCRIPT_DIR/sources.txt"
CRAWLER_FILE="$SCRIPT_DIR/crawler.txt"
DISCOVERED_FILE="$SCRIPT_DIR/discovered_sources.txt"
ARCHIVE_FILE="$SCRIPT_DIR/archive.txt"
STAMP_FILE="$SCRIPT_DIR/.last_update_check"
FULL_DOWNLOAD_URL="https://soundcloud.com/druleprivate/likes"

# Default music root on Mac; override with DJTOOLS_MUSIC_ROOT.
DOWNLOAD_ROOT="${DJTOOLS_MUSIC_ROOT:-$HOME/Music/SoundCloud}"
YTDLP_OUTPUT_TEMPLATE="$DOWNLOAD_ROOT/%(artist,creator,uploader)s/%(artist,creator,uploader)s - %(title)s.%(ext)s"

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

echo
echo "========================================"
echo "  LETS FUCKING GOOOOOOOOOOOOOOOOOO"
echo "========================================"
echo
echo "Controls at startup:"
echo "  ENTER = step through each source"
echo "  A     = run everything automatically (press Q during the wait"
echo "          to stop after the current source finishes)"
echo "  Q     = return to main menu now"
echo
read -r -p "Press ENTER, A, or Q to return to main menu: " USERINPUT
case "$(lower "$USERINPUT")" in
    a) MODE="AUTO" ;;
    q) exit 0 ;;
esac

echo
echo "Working folder: $SCRIPT_DIR"
echo

# --- Pre-flight checks -----------------------------------------------------

PRECHECK_WARNING=0

check_internet() {
    echo "Checking internet connectivity..."
    if ping -c 1 -t 2 1.1.1.1 >/dev/null 2>&1; then
        echo "[OK] Internet connectivity looks good."
        return 0
    fi
    echo "[WARN] No general internet connection detected by ping."
    echo "       Some networks block ICMP even when downloads still work."
    return 1
}

check_soundcloud() {
    echo "Checking SoundCloud reachability..."
    if command -v curl >/dev/null 2>&1; then
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 'https://soundcloud.com/' 2>/dev/null)"
        if [ -n "$code" ] && [ "$code" -ge 200 ] && [ "$code" -lt 400 ]; then
            echo "[OK] SoundCloud is reachable."
            return 0
        fi
    fi
    echo "[WARN] SoundCloud appears unreachable right now."
    echo "       SoundCloud sources may fail, but other sources can still work."
    return 1
}

check_internet || PRECHECK_WARNING=1
check_soundcloud || PRECHECK_WARNING=1

if [ "$PRECHECK_WARNING" = "1" ]; then
    echo
    echo "One or more connectivity checks raised warnings."
    echo "  C = continue into crate digger anyway"
    echo "  M = return to the main menu"
    read -r -p "Choose C, M, or Q to return to main menu (default C): " WARN_CHOICE
    case "$(lower "$WARN_CHOICE")" in
        m|q) exit 0 ;;
    esac
fi

# --- Required files --------------------------------------------------------

if [ -z "$YTDLP" ]; then
    echo "ERROR: yt-dlp not found. Install it with 'brew install yt-dlp'."
    exit 1
fi
if [ ! -f "$SOURCES_FILE" ]; then echo "ERROR: sources.txt not found in $SCRIPT_DIR"; exit 1; fi
if [ ! -f "$CRAWLER_FILE" ]; then echo "ERROR: crawler.txt not found in $SCRIPT_DIR"; exit 1; fi
if [ ! -f "$YTDLPCONF" ]; then echo "ERROR: yt-dlp.conf not found in $SCRIPT_DIR"; exit 1; fi

# --- Prepare output root ---------------------------------------------------

echo "Checking download root..."
mkdir -p "$DOWNLOAD_ROOT" 2>/dev/null
if [ ! -d "$DOWNLOAD_ROOT" ]; then
    echo "ERROR: Could not create download root: $DOWNLOAD_ROOT"
    echo "       Set DJTOOLS_MUSIC_ROOT to a writable folder and try again."
    exit 1
fi
WRITE_TEST="$DOWNLOAD_ROOT/.djtools_write_test.tmp"
if ! : > "$WRITE_TEST" 2>/dev/null; then
    echo "ERROR: Download root is not writable: $DOWNLOAD_ROOT"
    echo "       Set DJTOOLS_MUSIC_ROOT to a writable folder and try again."
    exit 1
fi
rm -f "$WRITE_TEST" 2>/dev/null
echo "[OK] Download root is ready: $DOWNLOAD_ROOT"

# --- Weekly yt-dlp update --------------------------------------------------

update_ytdlp_if_stale() {
    local needs_update=0
    if [ ! -f "$STAMP_FILE" ]; then
        needs_update=1
    else
        # Stamp older than 7 days (604800 s)?
        local now stamp age
        now="$(date +%s)"
        # macOS stat -f, GNU stat -c -- try both.
        stamp="$(stat -f %m "$STAMP_FILE" 2>/dev/null || stat -c %Y "$STAMP_FILE" 2>/dev/null)"
        if [ -n "$stamp" ]; then
            age=$(( now - stamp ))
            [ "$age" -ge 604800 ] && needs_update=1
        fi
    fi
    [ "$needs_update" = "0" ] && return 0
    echo
    echo "----------------------------------------"
    echo "Checking for yt-dlp updates (weekly)..."
    echo "----------------------------------------"
    if command -v brew >/dev/null 2>&1 && brew list yt-dlp >/dev/null 2>&1; then
        brew upgrade yt-dlp 2>/dev/null || true
    else
        "$YTDLP" -U 2>/dev/null || true
    fi
    : > "$STAMP_FILE"
    echo
}
update_ytdlp_if_stale

# --- Helpers for running a source -----------------------------------------

# Echoes the playlist args for a URL (uncapped for the full-download likes).
playlist_args_for() {
    local url="$1"
    if [ "$url" = "$FULL_DOWNLOAD_URL" ] || [ "$url" = "$FULL_DOWNLOAD_URL/" ]; then
        echo ""
    else
        echo "--playlist-end 5"
    fi
}

# Returns 1 if the user wants to stop (in AUTO mode), else 0.
check_quit() {
    [ "$MODE" != "AUTO" ] && return 0
    echo
    # 2-second window to press Q.
    local key=""
    read -r -t 2 -n 1 -p "Press Q to stop after this source (continuing in 2s) " key
    echo
    case "$(lower "$key")" in
        q)
            echo "[USER] Q detected. Returning to main menu after this source."
            return 1
            ;;
    esac
    return 0
}

# $1 = label, $2 = url
run_source() {
    local label="$1" url="$2" stepinput=""
    if [ "$MODE" = "STEP" ]; then
        echo "----------------------------------------"
        echo "$label: $url"
        echo "----------------------------------------"
        read -r -p "ENTER = continue, S = skip, A = auto-run rest, Q = return to main menu: " stepinput
        case "$(lower "$stepinput")" in
            a) MODE="AUTO" ;;
            q) return 1 ;;
            s) return 0 ;;
        esac
    fi
    echo "----------------------------------------"
    echo "$label: $url"
    echo "----------------------------------------"
    local pargs
    pargs="$(playlist_args_for "$url")"
    "$YTDLP" --config-location "$YTDLPCONF" --download-archive "$ARCHIVE_FILE" --no-update \
        -o "$YTDLP_OUTPUT_TEMPLATE" --ignore-errors --no-abort-on-error $pargs "$url"
    check_quit || return 1
    return 0
}

# Reads a source list file, running run_source for each non-blank, non-# line.
# $1 = file, $2 = label prefix
#
# The file is read on FD 3 (not stdin) so the interactive `read` prompts inside
# run_source / check_quit still read from the keyboard, not from the list file.
process_file() {
    local file="$1" prefix="$2" count=0 line trimmed
    while IFS= read -r line <&3 || [ -n "$line" ]; do
        # Trim leading/trailing whitespace.
        trimmed="$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        [ -z "$trimmed" ] && continue
        case "$trimmed" in \#*) continue ;; esac
        count=$((count + 1))
        run_source "$prefix $count" "$trimmed" || return 1
    done 3< "$file"
    return 0
}

# --- Run the lists ---------------------------------------------------------

print_summary() {
    echo
    echo "========================================"
    echo "  CRATE UPDATE COMPLETE"
    echo "========================================"
    echo
    echo "Started at:  $STARTTIME"
    echo "Finished at: $(date '+%H:%M:%S')"
    echo
    echo "To dedupe duplicate MP3s, use option 4 in the main DJ Tools menu."
    echo
}

echo
echo "Checking main sources..."
echo
process_file "$SOURCES_FILE" "Source" || { print_summary; exit 0; }

echo
echo "Checking crawler seeds..."
echo
process_file "$CRAWLER_FILE" "Crawler" || { print_summary; exit 0; }

echo
echo "Running discovery crawler..."
echo
if [ -f "$DISCOVER_SH" ]; then
    bash "$DISCOVER_SH"
else
    echo "WARNING: discover.sh not found, skipping discovery crawler."
fi

echo
echo "Crawling discovered sources..."
echo
if [ -f "$DISCOVERED_FILE" ]; then
    process_file "$DISCOVERED_FILE" "Discovered" || { print_summary; exit 0; }
else
    echo "No discovered_sources.txt found, skipping discovered sources."
fi

print_summary
exit 0
