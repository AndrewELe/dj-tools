#Requires -Version 5.1
<#
    grab-url.ps1  --  Standalone single-URL grabber for DJ Tools.

    Point it at ONE url (a SoundCloud/YouTube playlist, likes page, artist
    tracks page, album, channel, etc.) and it downloads EVERY available track
    that url resolves to as an MP3. All files land flat in a single folder that
    you name -- no per-artist subfolders.

    Usage:
        # Interactive (prompts for url + folder name):
        powershell -NoProfile -ExecutionPolicy Bypass -File grab-url.ps1

        # Non-interactive:
        powershell -NoProfile -ExecutionPolicy Bypass -File grab-url.ps1 -Url "<url>" -FolderName "My Crate"

    Where files go:
        <base>\<FolderName>\<Artist> - <Title>.mp3
        The base defaults to C:\Music\SoundCloud and can be overridden with the
        DJTOOLS_MUSIC_ROOT environment variable. If FolderName is an absolute
        path it is used as-is.

    SoundCloud login cookies (raises the rate-limit ceiling): same rules as the
    main crate digger -- DJTOOLS_SC_COOKIES_FILE, or sc_cookies.txt next to this
    script, or DJTOOLS_SC_COOKIES_BROWSER. Set the browser to "none" with no
    cookies file to run anonymously.
#>

[CmdletBinding()]
param(
    [string]$Url,
    [string]$FolderName,
    # Grab everything by default. Pass a number to cap how many tracks are pulled.
    [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
$base = $PSScriptRoot
Set-Location $base

$ytDlp = Join-Path $base "yt-dlp.exe"
if (-not (Test-Path $ytDlp)) {
    Write-Host "ERROR: yt-dlp.exe not found at $ytDlp" -ForegroundColor Red
    exit 1
}

# --- Gather inputs --------------------------------------------------------
if (-not $Url) {
    $Url = Read-Host "Paste the URL to grab all tracks from"
}
$Url = $Url.Trim().Trim('"')
if (-not $Url) {
    Write-Host "ERROR: No URL provided." -ForegroundColor Red
    exit 1
}
if ($Url -notmatch '^https?://') {
    Write-Host "ERROR: That does not look like a URL: $Url" -ForegroundColor Red
    exit 1
}

if (-not $FolderName) {
    $FolderName = Read-Host "Name the folder to save all tracks into"
}
$FolderName = $FolderName.Trim().Trim('"')
if (-not $FolderName) {
    Write-Host "ERROR: No folder name provided." -ForegroundColor Red
    exit 1
}

# --- Resolve the destination folder --------------------------------------
if ([System.IO.Path]::IsPathRooted($FolderName)) {
    $destFolder = $FolderName
}
else {
    # Strip characters that are illegal in a Windows folder name so a pasted
    # title can be used verbatim without blowing up.
    $safeName = ($FolderName -replace '[<>:"/\\|?*]', '_').Trim().TrimEnd('.')
    if (-not $safeName) { $safeName = "grab" }

    $musicRoot = $env:DJTOOLS_MUSIC_ROOT
    if (-not $musicRoot) { $musicRoot = "C:\Music\SoundCloud" }
    $destFolder = Join-Path $musicRoot $safeName
}

if (-not (Test-Path $destFolder)) {
    try {
        New-Item -ItemType Directory -Path $destFolder -Force | Out-Null
    }
    catch {
        Write-Host "ERROR: Could not create destination folder: $destFolder" -ForegroundColor Red
        exit 1
    }
}

# Quick writability check.
$writeTest = Join-Path $destFolder ".djtools_write_test.tmp"
try {
    [System.IO.File]::WriteAllText($writeTest, "")
    Remove-Item $writeTest -Force
}
catch {
    Write-Host "ERROR: Destination folder is not writable: $destFolder" -ForegroundColor Red
    exit 1
}

# --- SoundCloud login cookies (same precedence as the main digger) --------
$cookieFile = $env:DJTOOLS_SC_COOKIES_FILE
if (-not $cookieFile) {
    $defaultCookieFile = Join-Path $base "sc_cookies.txt"
    if (Test-Path $defaultCookieFile) { $cookieFile = $defaultCookieFile }
}
$cookieBrowser = $env:DJTOOLS_SC_COOKIES_BROWSER
if (-not $cookieBrowser) { $cookieBrowser = "none" }

$cookieArgs = @()
if ($cookieFile) {
    $cookieArgs = @("--cookies", $cookieFile)
    Write-Host "[OK] Using SoundCloud login cookies from: $cookieFile"
}
elseif ($cookieBrowser -and $cookieBrowser -ne "none") {
    $cookieArgs = @("--cookies-from-browser", $cookieBrowser)
}
else {
    Write-Host "[WARN] No sc_cookies.txt found - downloading ANONYMOUSLY (no Go+ 256kbps streams)." -ForegroundColor Yellow
}

# --- Optional local tools -------------------------------------------------
# Use the bundled ffmpeg/ffprobe if present so audio extraction just works.
$ffmpegArgs = @()
if (Test-Path (Join-Path $base "ffmpeg.exe")) {
    $ffmpegArgs = @("--ffmpeg-location", $base)
}

# A per-folder archive so re-running the same URL resumes instead of
# re-downloading, while a brand new folder always starts from scratch and
# pulls everything.
$archiveFile = Join-Path $destFolder ".download-archive.txt"

# Flat output template: every file lands directly in the destination folder.
$outputTemplate = Join-Path $destFolder "%(artist,creator,uploader)s - %(title)s.%(ext)s"

# --- Build the yt-dlp argument list --------------------------------------
# --ignore-config: don't inherit the crate digger's portable yt-dlp.conf
# (its shared archive.txt and 13-minute filter would silently skip tracks).
$ytArgs = @("--ignore-config")
$ytArgs += $cookieArgs
$ytArgs += $ffmpegArgs

$ytArgs += @(
    "--no-update",
    "--ignore-errors",
    "--no-abort-on-error",

    # Grab the best audio and transcode to a high-quality MP3.
    "--format", "bestaudio/best",
    "--extract-audio",
    "--audio-format", "mp3",
    "--audio-quality", "0",

    # Embed artwork + tags.
    "--embed-thumbnail",
    "--embed-metadata",
    "--add-metadata",

    # Be gentle so large playlists don't trip SoundCloud throttling.
    "--sleep-interval", "5",
    "--max-sleep-interval", "10",
    "--sleep-requests", "1.5",

    # Resume support for this folder.
    "--download-archive", $archiveFile,

    "-o", $outputTemplate
)

if ($Limit -gt 0) {
    $ytArgs += @("--playlist-end", "$Limit")
}

$ytArgs += $Url

# --- Go -------------------------------------------------------------------
Write-Host ""
Write-Host "========================================"
Write-Host "  GRABBING ALL TRACKS FROM ONE URL"
Write-Host "========================================"
Write-Host "URL:          $Url"
Write-Host "Destination:  $destFolder"
if ($Limit -gt 0) {
    Write-Host "Track cap:    $Limit"
}
else {
    Write-Host "Track cap:    none (all available)"
}
Write-Host ""

& $ytDlp @ytArgs
$exit = $LASTEXITCODE

Write-Host ""
$mp3Count = (Get-ChildItem -Path $destFolder -Filter *.mp3 -File -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "========================================"
Write-Host "  DONE"
Write-Host "========================================"
Write-Host "MP3s in folder: $mp3Count"
Write-Host "Folder:         $destFolder"
Write-Host ""

exit $exit
