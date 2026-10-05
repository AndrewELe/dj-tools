#!/usr/bin/env bash
#
# Discovery crawler (macOS) -- the Mac equivalent of discover.ps1.
#
# Reads seed URLs from crawler.txt and sources.txt, asks yt-dlp for each
# seed's "<uploader_url>/reposts" page (inspecting the first 5 items), then
# cleans, de-duplicates and writes the results to discovered_sources.txt.

set -u

BASE="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$BASE" || exit 1

if [ -x "$BASE/yt-dlp" ]; then
    YTDLP="$BASE/yt-dlp"
elif command -v yt-dlp >/dev/null 2>&1; then
    YTDLP="$(command -v yt-dlp)"
else
    echo "ERROR: yt-dlp not found. Install it with 'brew install yt-dlp'." >&2
    exit 1
fi

CRAWLER_FILE="$BASE/crawler.txt"
SOURCES_FILE="$BASE/sources.txt"
TEMP_FILE="$BASE/discovered_raw.txt"
FINAL_FILE="$BASE/discovered_sources.txt"

# SoundCloud login cookies, same precedence as digcrate.sh:
# DJTOOLS_SC_COOKIES_FILE > sc_cookies.txt next to this script >
# DJTOOLS_SC_COOKIES_BROWSER (unset = anonymous).
COOKIE_FILE="${DJTOOLS_SC_COOKIES_FILE:-}"
if [ -z "$COOKIE_FILE" ] && [ -f "$BASE/sc_cookies.txt" ]; then
    COOKIE_FILE="$BASE/sc_cookies.txt"
fi
COOKIE_BROWSER="${DJTOOLS_SC_COOKIES_BROWSER:-none}"
COOKIE_ARGS=()
if [ -n "$COOKIE_FILE" ]; then
    COOKIE_ARGS=(--cookies "$COOKIE_FILE")
elif [ "$(printf '%s' "$COOKIE_BROWSER" | tr '[:upper:]' '[:lower:]')" != "none" ]; then
    COOKIE_ARGS=(--cookies-from-browser "$COOKIE_BROWSER")
fi

if [ ! -f "$CRAWLER_FILE" ] && [ ! -f "$SOURCES_FILE" ]; then
    echo "ERROR: No seed files found. Expected crawler.txt and/or sources.txt in $BASE" >&2
    exit 1
fi

rm -f "$TEMP_FILE" 2>/dev/null

# Gather seed URLs (non-blank, non-comment) from both files.
ALL_URLS=()
for file in "$CRAWLER_FILE" "$SOURCES_FILE"; do
    [ -f "$file" ] || continue
    while IFS= read -r line || [ -n "$line" ]; do
        trimmed="$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        [ -z "$trimmed" ] && continue
        case "$trimmed" in \#*) continue ;; esac
        ALL_URLS+=("$trimmed")
    done < "$file"
done

total="${#ALL_URLS[@]}"
index=0

echo
echo "=== DISCOVERY CRAWLER START ==="
echo "Working folder: $BASE"
echo "Seed URLs to inspect: $total"
echo

for url in "${ALL_URLS[@]}"; do
    index=$((index + 1))
    echo "[DISCOVER] ($index/$total) $url"
    # --ignore-config: yt-dlp otherwise auto-loads ./yt-dlp.conf (we cd'd into
    # this folder), whose --download-archive makes it skip -- and print nothing
    # for -- every track already downloaded, starving discovery.
    "$YTDLP" \
        --ignore-config \
        ${COOKIE_ARGS[@]+"${COOKIE_ARGS[@]}"} \
        --sleep-requests 1 \
        --skip-download \
        --ignore-errors \
        --no-abort-on-error \
        --no-update \
        --playlist-end 5 \
        --print "%(uploader_url)s/reposts" \
        "$url" 2>/dev/null >> "$TEMP_FILE" || echo "[DISCOVER] Failed: $url"
done

echo
echo "[DISCOVER] Cleaning discovered sources..."

if [ -f "$TEMP_FILE" ]; then
    # Keep only http(s) URLs, drop yt-dlp's "NA" placeholders, sort unique.
    grep -E '^https?://' "$TEMP_FILE" 2>/dev/null \
        | grep -v -E '^NA' \
        | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
        | sort -u > "$FINAL_FILE"
fi

final_count=0
[ -f "$FINAL_FILE" ] && final_count="$(grep -c '' "$FINAL_FILE" 2>/dev/null || echo 0)"

echo "[DISCOVER] Finished. Sources saved: $final_count"
echo "[DISCOVER] Output file: $FINAL_FILE"
echo "=== DISCOVERY CRAWLER END ==="
echo
