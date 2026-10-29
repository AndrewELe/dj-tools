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

# Main sources grab their newest SOURCE_CAP tracks. Crawler seeds and
# discovered sources instead dig down the list, skipping anything already in
# the archive, until NEW_TRACK_TARGET new tracks have downloaded successfully
# or the newest DIG_LOOKBACK tracks have been worked through. Tracks that fail
# partway don't count and are retried on the next run (see dig_source);
# DIG_MAX_PASSES caps the re-digs after failures.
SOURCE_CAP=15
NEW_TRACK_TARGET=15
DIG_LOOKBACK=200
DIG_MAX_PASSES=5

# Default music root on Mac; override with DJTOOLS_MUSIC_ROOT.
DOWNLOAD_ROOT="${DJTOOLS_MUSIC_ROOT:-$HOME/Music/SoundCloud}"
YTDLP_OUTPUT_TEMPLATE="$DOWNLOAD_ROOT/%(artist,creator,uploader)s - %(title)s.%(ext)s"

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# --- SoundCloud login cookies ---------------------------------------------
# Logging in as your account unlocks Go+/SoundCloud+ 256kbps AAC streams and
# makes SoundCloud throttle far less aggressively than anonymous traffic.
#
#   1. Cookies file (recommended): drop an exported cookies.txt named
#      "sc_cookies.txt" next to this script, or point DJTOOLS_SC_COOKIES_FILE
#      at any path.
#   2. Live from a browser: set DJTOOLS_SC_COOKIES_BROWSER (firefox, chrome,
#      brave, safari). Chrome/Brave pop a Keychain prompt; Safari needs Full
#      Disk Access for Terminal.
#
# Precedence: explicit file > sc_cookies.txt next to the script > browser.
# With neither set, runs anonymously (with a warning).
COOKIE_FILE="${DJTOOLS_SC_COOKIES_FILE:-}"
if [ -z "$COOKIE_FILE" ] && [ -f "$SCRIPT_DIR/sc_cookies.txt" ]; then
    COOKIE_FILE="$SCRIPT_DIR/sc_cookies.txt"
fi
COOKIE_BROWSER="${DJTOOLS_SC_COOKIES_BROWSER:-none}"
COOKIE_ARGS=()
if [ -n "$COOKIE_FILE" ]; then
    COOKIE_ARGS=(--cookies "$COOKIE_FILE")
    echo "[OK] Using SoundCloud login cookies from: $COOKIE_FILE"
    if ! grep -q 'oauth_token' "$COOKIE_FILE" 2>/dev/null; then
        echo "[WARN] No oauth_token in that cookies file - you are NOT logged in."
        echo "       Re-export sc_cookies.txt while signed in to soundcloud.com."
    else
        # Warn a month before the login runs out, so sc_cookies.txt only needs
        # re-exporting when it matters. Column 5 is expiry, column 6 the name.
        OAUTH_EXPIRES="$(awk -F'\t' '$6 == "oauth_token" { print $5; exit }' "$COOKIE_FILE")"
        if [[ "$OAUTH_EXPIRES" =~ ^[0-9]+$ ]] && [ "$OAUTH_EXPIRES" -gt 0 ]; then
            NOW="$(date +%s)"
            EXPIRY_DATE="$(date -r "$OAUTH_EXPIRES" +%Y-%m-%d)"
            DAYS_LEFT=$(( (OAUTH_EXPIRES - NOW) / 86400 ))
            if [ "$OAUTH_EXPIRES" -le "$NOW" ]; then
                echo "[WARN] Your SoundCloud login in sc_cookies.txt expired on $EXPIRY_DATE."
            elif [ "$DAYS_LEFT" -lt 30 ]; then
                echo "[WARN] Your SoundCloud login in sc_cookies.txt expires in $DAYS_LEFT day(s), on $EXPIRY_DATE."
            fi
            if [ "$DAYS_LEFT" -lt 30 ]; then
                echo "       Sign out and back in on soundcloud.com, then re-export"
                echo "       sc_cookies.txt with the Get cookies.txt LOCALLY extension."
            fi
        fi
    fi
elif [ "$(lower "$COOKIE_BROWSER")" != "none" ]; then
    COOKIE_ARGS=(--cookies-from-browser "$COOKIE_BROWSER")
    echo "[OK] Using SoundCloud login cookies from browser: $COOKIE_BROWSER"
else
    echo "[WARN] No sc_cookies.txt found - downloading ANONYMOUSLY."
    echo "       No Go+ 256kbps streams and heavier throttling."
fi

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

is_full_download() {
    [ "$1" = "$FULL_DOWNLOAD_URL" ] || [ "$1" = "$FULL_DOWNLOAD_URL/" ]
}

# Echoes the playlist args for a non-DIG source. $1 = url.
# The full-download likes are always uncapped.
playlist_args_for() {
    if is_full_download "$1"; then
        echo ""
    else
        echo "--playlist-end $SOURCE_CAP"
    fi
}

archive_count() {
    if [ -f "$ARCHIVE_FILE" ]; then
        wc -l < "$ARCHIVE_FILE" | tr -d '[:space:]'
    else
        echo 0
    fi
}

# Prints the non-blank lines of stdin that are not lines of file $1. (awk, not
# grep -vxFf, which misbehaves on an empty pattern file in some grep builds.)
lines_not_in() {
    awk 'FILENAME == ARGV[1] { seen[$0] = 1; next } NF && !($0 in seen)' "$1" -
}

# Digs into a crawler/discovered source until NEW_TRACK_TARGET tracks have
# downloaded successfully. $1 = url. Returns 0 when the target is reached,
# 1 if the source ran out (or DIG_MAX_PASSES was hit) first.
#
# yt-dlp's --max-downloads counts a track as soon as its download starts, so a
# track that fails partway (HTTP error, ffmpeg error...) would use up one of
# the slots. Instead this runs yt-dlp in passes: after each pass, tracks that
# made it into the archive count as downloaded, and tracks that were attempted
# but did not make it are skipped for the rest of this run (via a temporary
# copy of the archive) while the next pass digs for the remainder. Failed
# tracks never reach the real archive, so the next run tries them again.
dig_source() {
    local url="$1" tmpdir failed pass=0 downloaded=0 remaining rc result=1
    local pass_archive attempted before_file new_file new_count failed_count
    tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/crate-digger.XXXXXX")" || return 1
    # Archive ids ("soundcloud 123...") of tracks that failed partway this run.
    failed="$tmpdir/failed.txt"
    : > "$failed"

    while :; do
        pass=$((pass + 1))
        remaining=$((NEW_TRACK_TARGET - downloaded))
        attempted="$tmpdir/attempted_$pass.txt"
        before_file="$tmpdir/before_$pass.txt"
        new_file="$tmpdir/new_$pass.txt"

        if [ -s "$failed" ]; then
            # Real archive + this run's failures, so yt-dlp skips the failures.
            pass_archive="$tmpdir/archive_$pass.txt"
            { [ -f "$ARCHIVE_FILE" ] && tr -d '\r' < "$ARCHIVE_FILE" | awk 1; cat "$failed"; } > "$pass_archive"
        else
            pass_archive="$ARCHIVE_FILE"
        fi
        if [ -f "$pass_archive" ]; then
            tr -d '\r' < "$pass_archive" > "$before_file"
        else
            : > "$before_file"
        fi

        # --no-playlist-reverse overrides yt-dlp.conf so digging starts at the
        # newest track. before_dl fires for exactly the tracks yt-dlp counts
        # toward --max-downloads, i.e. every real download attempt.
        "$YTDLP" --config-location "$YTDLPCONF" ${COOKIE_ARGS[@]+"${COOKIE_ARGS[@]}"} \
            --download-archive "$pass_archive" --no-update \
            -o "$YTDLP_OUTPUT_TEMPLATE" --ignore-errors --no-abort-on-error \
            --max-downloads "$remaining" --playlist-end "$DIG_LOOKBACK" --no-playlist-reverse \
            --print-to-file "before_dl:%(extractor_key)s %(id)s" "$attempted" \
            "$url"
        rc=$?

        # New archive lines = tracks that downloaded successfully this pass.
        if [ -f "$pass_archive" ]; then
            tr -d '\r' < "$pass_archive" | lines_not_in "$before_file" > "$new_file"
        else
            : > "$new_file"
        fi
        new_count="$(grep -c . "$new_file")"
        if [ "$pass_archive" != "$ARCHIVE_FILE" ] && [ "$new_count" -gt 0 ]; then
            # Make sure the real archive ends with a newline before appending.
            if [ -s "$ARCHIVE_FILE" ] && [ -n "$(tail -c 1 "$ARCHIVE_FILE")" ]; then
                echo >> "$ARCHIVE_FILE"
            fi
            cat "$new_file" >> "$ARCHIVE_FILE"
        fi
        downloaded=$((downloaded + new_count))

        # Attempted but not archived = failed partway.
        if [ -s "$attempted" ]; then
            tr -d '\r' < "$pass_archive" > "$tmpdir/after_$pass.txt"
            tr -d '\r' < "$attempted" | awk 'NF >= 2 { $1 = tolower($1); print }' \
                | lines_not_in "$tmpdir/after_$pass.txt" >> "$failed"
        fi

        if [ "$downloaded" -ge "$NEW_TRACK_TARGET" ]; then
            result=0
            break
        fi
        # Any exit other than 101 (--max-downloads hit) means the list ran out.
        [ "$rc" -ne 101 ] && break
        if [ "$pass" -ge "$DIG_MAX_PASSES" ]; then
            echo "[DIG] Giving up on this source after $pass passes."
            break
        fi
        failed_count="$(grep -c . "$failed")"
        echo
        echo "[DIG] $downloaded of $NEW_TRACK_TARGET new tracks downloaded, $failed_count failed partway (not counted)."
        echo "[DIG] Digging for $((NEW_TRACK_TARGET - downloaded)) more, skipping the failed tracks..."
        echo
    done

    failed_count="$(grep -c . "$failed")"
    if [ "$failed_count" -gt 0 ]; then
        echo "[DIG] $failed_count track(s) failed partway - not counted, will retry next run."
    fi
    rm -rf "$tmpdir"
    return "$result"
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

# $1 = label, $2 = url, $3 = CAP (newest N tracks) or DIG (next N new tracks)
run_source() {
    local label="$1" url="$2" runmode="$3" stepinput=""
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
    if [ "$runmode" != "DIG" ] || is_full_download "$url"; then
        local pargs
        pargs="$(playlist_args_for "$url")"
        # ${arr[@]+...} form: macOS ships bash 3.2, where expanding an empty
        # array under `set -u` is an "unbound variable" error.
        "$YTDLP" --config-location "$YTDLPCONF" ${COOKIE_ARGS[@]+"${COOKIE_ARGS[@]}"} \
            --download-archive "$ARCHIVE_FILE" --no-update \
            -o "$YTDLP_OUTPUT_TEMPLATE" --ignore-errors --no-abort-on-error $pargs "$url"
    else
        local before
        before="$(archive_count)"
        # dig_source fails when the list ran out before reaching the target, so
        # pause 5 seconds for the user (even in AUTO mode).
        if ! dig_source "$url"; then
            local new_tracks exhaustinput=""
            new_tracks=$(( $(archive_count) - before ))
            echo
            echo "========================================"
            echo "  SOURCE EXHAUSTED"
            echo "========================================"
            echo "$label: $url"
            echo "Only $new_tracks of $NEW_TRACK_TARGET new tracks downloaded (newest $DIG_LOOKBACK checked)."
            echo "The rest are already in the archive, DRM protected or filtered out - or"
            echo "yt-dlp hit errors. Tracks that failed partway were not counted and will"
            echo "be retried next run. If you saw \"HTTP Error 429\" above, SoundCloud is"
            echo "rate limiting: wait ~10 minutes before continuing."
            echo
            read -r -t 5 -n 1 -p "ENTER = continue to next source, Q = return to main menu (continuing in 5s) " exhaustinput
            echo
            [ "$(lower "$exhaustinput")" = "q" ] && return 1
            return 0
        fi
    fi

    check_quit || return 1
    return 0
}

# Reads a source list file, running run_source for each non-blank, non-# line.
# $1 = file, $2 = label prefix, $3 = CAP or DIG (see run_source)
#
# The file is read on FD 3 (not stdin) so the interactive `read` prompts inside
# run_source / check_quit still read from the keyboard, not from the list file.
process_file() {
    local file="$1" prefix="$2" runmode="$3" count=0 line trimmed
    while IFS= read -r line <&3 || [ -n "$line" ]; do
        # Trim leading/trailing whitespace.
        trimmed="$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        [ -z "$trimmed" ] && continue
        case "$trimmed" in \#*) continue ;; esac
        count=$((count + 1))
        run_source "$prefix $count" "$trimmed" "$runmode" || return 1
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
process_file "$SOURCES_FILE" "Source" CAP || { print_summary; exit 0; }

echo
echo "Checking crawler seeds..."
echo
process_file "$CRAWLER_FILE" "Crawler" DIG || { print_summary; exit 0; }

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
    process_file "$DISCOVERED_FILE" "Discovered" DIG || { print_summary; exit 0; }
else
    echo "No discovered_sources.txt found, skipping discovered sources."
fi

print_summary
exit 0
