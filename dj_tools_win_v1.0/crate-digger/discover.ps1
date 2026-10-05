$base = $PSScriptRoot
Set-Location $base

$ytDlp = Join-Path $base "yt-dlp.exe"
$crawlerFile = Join-Path $base "crawler.txt"
$sourcesFile = Join-Path $base "sources.txt"
$seedFiles = @($crawlerFile, $sourcesFile)

$tempFile = Join-Path $base "discovered_raw.txt"
$finalFile = Join-Path $base "discovered_sources.txt"

# SoundCloud login cookies (raises the rate-limit ceiling). Precedence:
# explicit DJTOOLS_SC_COOKIES_FILE > sc_cookies.txt next to this script >
# live from DJTOOLS_SC_COOKIES_BROWSER (unset = anonymous; Chrome
# live-extraction usually fails on Windows, so a cookies file is the reliable
# option).
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
}
elseif ($cookieBrowser -and $cookieBrowser -ne "none") {
    $cookieArgs = @("--cookies-from-browser", $cookieBrowser)
}

if (-not (Test-Path $ytDlp)) {
    Write-Host "ERROR: yt-dlp.exe not found at $ytDlp" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $crawlerFile) -and -not (Test-Path $sourcesFile)) {
    Write-Host "ERROR: No seed files found. Expected crawler.txt and/or sources.txt in $base" -ForegroundColor Red
    exit 1
}

if (Test-Path $tempFile) {
    Remove-Item $tempFile -Force
}

$allUrls = @()

foreach ($file in $seedFiles) {
    if (Test-Path $file) {
        $allUrls += Get-Content $file | Where-Object {
            $line = $_.Trim()
            $line -ne "" -and -not $line.StartsWith("#")
        }
    }
}

$total = $allUrls.Count
$index = 0

Write-Host ""
Write-Host "=== DISCOVERY CRAWLER START ==="
Write-Host "Working folder: $base"
Write-Host "Seed URLs to inspect: $total"
Write-Host ""

foreach ($url in $allUrls) {
    $index++
    $cleanUrl = $url.Trim()

    Write-Progress -Activity "Discovery crawler" -Status "Inspecting $index of $total" -PercentComplete (($index / $total) * 100)
    Write-Host "[DISCOVER] ($index/$total) $cleanUrl"

    try {
        # --ignore-config: otherwise yt-dlp auto-loads the portable yt-dlp.conf
        # next to the exe, whose --download-archive makes it skip (and print
        # nothing for) every track already downloaded, starving discovery.
        & $ytDlp `
            --ignore-config `
            --no-update `
            @cookieArgs `
            --sleep-requests 1 `
            --skip-download `
            --ignore-errors `
            --no-abort-on-error `
            --playlist-end 5 `
            --print "%(uploader_url)s/reposts" `
            "$cleanUrl" 2>$null | Add-Content $tempFile
    }
    catch {
        Write-Host "[DISCOVER] Failed: $cleanUrl" -ForegroundColor Yellow
    }
}

Write-Progress -Activity "Discovery crawler" -Completed
Write-Host ""
Write-Host "[DISCOVER] Cleaning discovered sources..."

if (Test-Path $tempFile) {
    $cleanedUrls = Get-Content $tempFile |
        Where-Object { $_ -and $_ -notmatch "^NA" } |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -match '^https?://' } |
        Sort-Object -Unique

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllLines($finalFile, $cleanedUrls, $utf8NoBom)
}

$finalCount = 0
if (Test-Path $finalFile) {
    $finalCount = (Get-Content $finalFile | Measure-Object).Count
}

Write-Host "[DISCOVER] Finished. Sources saved: $finalCount"
Write-Host "[DISCOVER] Output file: $finalFile"
Write-Host "=== DISCOVERY CRAWLER END ==="
Write-Host ""
