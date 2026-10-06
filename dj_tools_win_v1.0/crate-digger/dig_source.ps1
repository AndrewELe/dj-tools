# Digs into one crawler/discovered source until $Target tracks have downloaded
# successfully. Called by digcrate.bat for DIG-mode sources.
#
# yt-dlp's --max-downloads counts a track as soon as its download starts, so a
# track that fails partway (HTTP error, ffmpeg error...) would use up one of
# the slots. Instead this runs yt-dlp in passes: after each pass, tracks that
# made it into the archive count as downloaded, and tracks that were attempted
# but did not make it are skipped for the rest of this run (via a temporary
# copy of the archive) while the next pass digs for the remainder. Failed
# tracks never reach the real archive, so the next run tries them again.
#
# Exit code: 0 = target reached, 1 = source ran out (or pass limit hit) first.

param(
    [Parameter(Mandatory = $true)][string]$YtDlp,
    [Parameter(Mandatory = $true)][string]$Config,
    [Parameter(Mandatory = $true)][string]$ArchiveFile,
    [Parameter(Mandatory = $true)][string]$OutputTemplate,
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$Target = 15,
    [int]$Lookback = 200,
    [int]$MaxPasses = 5,
    [string]$CookiesFile,
    [string]$CookiesBrowser
)

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Read-Lines([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return @() }
    return @([System.IO.File]::ReadAllLines($path) | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function New-IdSet([string[]]$lines) {
    $set = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($line in $lines) { [void]$set.Add($line) }
    return , $set
}

$cookieArgs = @()
if ($CookiesFile) {
    $cookieArgs = @("--cookies", $CookiesFile)
}
elseif ($CookiesBrowser -and $CookiesBrowser -ne "none") {
    $cookieArgs = @("--cookies-from-browser", $CookiesBrowser)
}

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("crate-digger-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Archive ids ("soundcloud 123...") of tracks that failed partway this run.
$failed = New-Object System.Collections.Generic.List[string]
$downloaded = 0
$pass = 0
$exitCode = 1

try {
    while ($true) {
        $pass++
        $remaining = $Target - $downloaded
        $attemptedFile = Join-Path $tempDir "attempted_$pass.txt"

        if ($failed.Count -gt 0) {
            # Real archive + this run's failures, so yt-dlp skips the failures.
            $passArchive = Join-Path $tempDir "archive_$pass.txt"
            [System.IO.File]::WriteAllLines($passArchive, [string[]](@(Read-Lines $ArchiveFile) + $failed), $utf8NoBom)
        }
        else {
            $passArchive = $ArchiveFile
        }
        $archiveBefore = New-IdSet (Read-Lines $passArchive)

        # --no-playlist-reverse overrides yt-dlp.conf so digging starts at the
        # newest track. before_dl fires for exactly the tracks yt-dlp counts
        # toward --max-downloads, i.e. every real download attempt.
        $ytArgs = @("--config-location", $Config) + $cookieArgs + @(
            "--download-archive", $passArchive,
            "--no-update",
            "-o", $OutputTemplate,
            "--ignore-errors", "--no-abort-on-error",
            "--max-downloads", $remaining,
            "--playlist-end", $Lookback,
            "--no-playlist-reverse",
            "--print-to-file", "before_dl:%(extractor_key)s %(id)s", $attemptedFile,
            $Url
        )
        & $YtDlp @ytArgs
        $rc = $LASTEXITCODE

        # New archive lines = tracks that downloaded successfully this pass.
        $archiveAfter = @(Read-Lines $passArchive)
        $newEntries = @($archiveAfter | Where-Object { -not $archiveBefore.Contains($_) })
        if ($passArchive -ne $ArchiveFile -and $newEntries.Count -gt 0) {
            $prefix = ""
            if ((Test-Path -LiteralPath $ArchiveFile) -and (Get-Item -LiteralPath $ArchiveFile).Length -gt 0) {
                $existing = [System.IO.File]::ReadAllText($ArchiveFile)
                if (-not $existing.EndsWith("`n")) { $prefix = "`r`n" }
            }
            [System.IO.File]::AppendAllText($ArchiveFile, $prefix + ($newEntries -join "`r`n") + "`r`n", $utf8NoBom)
        }
        $downloaded += $newEntries.Count

        # Attempted but not archived = failed partway.
        $archivedNow = New-IdSet $archiveAfter
        foreach ($line in (Read-Lines $attemptedFile)) {
            $parts = $line.Split(" ", 2)
            if ($parts.Count -lt 2) { continue }
            $archiveId = $parts[0].ToLowerInvariant() + " " + $parts[1]
            if (-not $archivedNow.Contains($archiveId) -and -not $failed.Contains($archiveId)) {
                $failed.Add($archiveId)
            }
        }

        if ($downloaded -ge $Target) { $exitCode = 0; break }
        # Any exit other than 101 (--max-downloads hit) means the list ran out.
        if ($rc -ne 101) { break }
        if ($pass -ge $MaxPasses) {
            Write-Host "[DIG] Giving up on this source after $pass passes."
            break
        }
        Write-Host ""
        Write-Host "[DIG] $downloaded of $Target new tracks downloaded, $($failed.Count) failed partway (not counted)."
        Write-Host "[DIG] Digging for $($Target - $downloaded) more, skipping the failed tracks..."
        Write-Host ""
    }
}
finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failed.Count -gt 0) {
    Write-Host "[DIG] $($failed.Count) track(s) failed partway - not counted, will retry next run."
}
exit $exitCode
