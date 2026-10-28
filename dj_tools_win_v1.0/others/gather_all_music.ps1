param(
    [string]$MusicRoot
)

$ErrorActionPreference = "Stop"

function Write-Err($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
}

# Audio types crate-digger can produce. mp3 is the norm, the rest are here so
# nothing gets left behind if the download format ever changes.
$audioExtensions = @(".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aiff")

# Name of the single flat folder everything is collected into, created inside
# the music root next to the per-artist folders.
$collectFolderName = "All Music"

try {
    $base = $PSScriptRoot

    # Music root precedence: parameter > DJTOOLS_MUSIC_ROOT env var > prompt/default,
    # matching how digcrate.bat and dedupe_audio.ps1 resolve the download root.
    if ([string]::IsNullOrWhiteSpace($MusicRoot)) {
        $MusicRoot = $env:DJTOOLS_MUSIC_ROOT
    }

    if ([string]::IsNullOrWhiteSpace($MusicRoot)) {
        $defaultRoot = "C:\Music\SoundCloud"
        $inputRoot = Read-Host "Enter music root path, press ENTER for default [$defaultRoot], or Q to return to menu"
        if ($inputRoot -and $inputRoot.Trim().ToLower() -eq "q") {
            Write-Host "Returning to menu."
            exit 0
        }
        if ([string]::IsNullOrWhiteSpace($inputRoot)) {
            $MusicRoot = $defaultRoot
        }
        else {
            $MusicRoot = $inputRoot.Trim().Trim('"').Trim("'")
        }
    }
    else {
        $MusicRoot = $MusicRoot.Trim().Trim('"').Trim("'")
    }

    if (-not (Test-Path -LiteralPath $MusicRoot)) {
        Write-Err "music root not found: $MusicRoot"
        exit 1
    }

    $MusicRoot = (Resolve-Path -LiteralPath $MusicRoot).Path

    $collectRoot = Join-Path $MusicRoot $collectFolderName

    if (-not (Test-Path -LiteralPath $collectRoot)) {
        New-Item -ItemType Directory -Path $collectRoot | Out-Null
    }

    $collectRootNormalized = [System.IO.Path]::GetFullPath($collectRoot)
    # _dupes is where dedupe_audio.ps1 quarantines duplicates. Leave those out so
    # we don't drag known duplicates back into the collection.
    $dupeRootNormalized = [System.IO.Path]::GetFullPath((Join-Path $MusicRoot "_dupes"))

    # Force array with @(...) so .Count is always defined even for 0/1 results.
    $files = @(
        Get-ChildItem -LiteralPath $MusicRoot -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object {
                $audioExtensions -contains $_.Extension.ToLower() -and
                $_.DirectoryName -ne $collectRoot
            } |
            Where-Object {
                $full = [System.IO.Path]::GetFullPath($_.FullName)
                (-not $full.StartsWith($collectRootNormalized, [System.StringComparison]::OrdinalIgnoreCase)) -and
                (-not $full.StartsWith($dupeRootNormalized, [System.StringComparison]::OrdinalIgnoreCase))
            }
    )

    $total = $files.Count

    Write-Host ""
    Write-Host "=== GATHER ALL MUSIC START ==="
    Write-Host "Tool folder: $base"
    Write-Host "Music root: $MusicRoot"
    Write-Host "Collect folder: $collectRoot"
    Write-Host "Tracks to move: $total"
    Write-Host ""

    if ($total -eq 0) {
        Write-Host "No tracks found to move under $MusicRoot. Nothing to do." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "=== GATHER ALL MUSIC END ==="
        exit 0
    }

    $index = 0
    $movedCount = 0
    $skippedCount = 0
    $errorCount = 0

    foreach ($file in $files) {
        $index++
        try {
            $percent = [Math]::Min(100, [int](($index / $total) * 100))
            Write-Progress -Activity "Gathering tracks" -Status "Moving $index of $total" -PercentComplete $percent

            $target = Join-Path $collectRoot $file.Name

            if (Test-Path -LiteralPath $target) {
                Write-Host "[GATHER] Skipped (already in collection): $($file.Name)" -ForegroundColor Yellow
                $skippedCount++
                continue
            }

            Move-Item -LiteralPath $file.FullName -Destination $target -ErrorAction Stop
            Write-Host "[GATHER] Moved -> $($file.Name)"
            $movedCount++
        }
        catch {
            $errorCount++
            Write-Host "[GATHER] Error on $($file.Name): $($_.Exception.Message)" -ForegroundColor Red
            continue
        }
    }

    Write-Progress -Activity "Gathering tracks" -Completed

    # Clean up the per-artist subfolders that are now empty. The collect folder
    # and _dupes are left alone.
    $removedFolders = 0
    Get-ChildItem -LiteralPath $MusicRoot -Recurse -Directory -ErrorAction SilentlyContinue |
        Sort-Object { $_.FullName.Length } -Descending |
        ForEach-Object {
            $dirFull = [System.IO.Path]::GetFullPath($_.FullName)
            if ($dirFull.StartsWith($collectRootNormalized, [System.StringComparison]::OrdinalIgnoreCase) -or
                $dirFull.StartsWith($dupeRootNormalized, [System.StringComparison]::OrdinalIgnoreCase)) {
                return
            }
            if (-not (Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue)) {
                try {
                    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
                    $removedFolders++
                }
                catch {
                    # Leave folders we can't remove; not worth failing the run over.
                }
            }
        }

    Write-Host ""
    Write-Host "=== GATHER ALL MUSIC END ==="
    Write-Host "Moved: $movedCount"
    Write-Host "Skipped (duplicates): $skippedCount"
    Write-Host "Errors: $errorCount"
    Write-Host "Empty artist folders removed: $removedFolders"
    Write-Host "Everything is now in: $collectRoot"
    Write-Host ""
    exit 0
}
catch {
    Write-Err "Unhandled failure: $($_.Exception.Message)"
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    exit 1
}
