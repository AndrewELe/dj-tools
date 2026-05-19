param(
    [string]$MusicRoot
)

$ErrorActionPreference = "Stop"

function Write-Err($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
}

function Pause-OnExit {
    if ($Host.Name -eq "ConsoleHost") {
        Read-Host "Press ENTER to close"
    }
}

try {
    $base = $PSScriptRoot
    $fpcalc = Join-Path $base "fpcalc.exe"

    if (-not (Test-Path -LiteralPath $fpcalc)) {
        Write-Err "fpcalc.exe not found at $fpcalc"
        Pause-OnExit
        exit 1
    }

    if ([string]::IsNullOrWhiteSpace($MusicRoot)) {
        $defaultRoot = "C:\Music\SoundCloud"
        $inputRoot = Read-Host "Enter music root path or press ENTER for default [$defaultRoot]"
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
        Pause-OnExit
        exit 1
    }

    $MusicRoot = (Resolve-Path -LiteralPath $MusicRoot).Path

    $dupeRoot = Join-Path $MusicRoot "_dupes"

    if (-not (Test-Path -LiteralPath $dupeRoot)) {
        New-Item -ItemType Directory -Path $dupeRoot | Out-Null
    }

    $dupeRootNormalized = [System.IO.Path]::GetFullPath($dupeRoot)

    # -Filter is faster and actually works with -Recurse, unlike -Include with -Path.
    # Force array with @(...) so .Count is always defined even for 0/1 results.
    $files = @(
        Get-ChildItem -LiteralPath $MusicRoot -Recurse -File -Filter *.mp3 -ErrorAction SilentlyContinue |
            Where-Object {
                $full = [System.IO.Path]::GetFullPath($_.FullName)
                -not $full.StartsWith($dupeRootNormalized, [System.StringComparison]::OrdinalIgnoreCase)
            }
    )

    $total = $files.Count

    Write-Host ""
    Write-Host "=== AUDIO DEDUPE START ==="
    Write-Host "Tool folder: $base"
    Write-Host "Music root: $MusicRoot"
    Write-Host "Duplicate folder: $dupeRoot"
    Write-Host "MP3 files to fingerprint: $total"
    Write-Host ""

    if ($total -eq 0) {
        Write-Host "No MP3 files found under $MusicRoot. Nothing to dedupe." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "=== AUDIO DEDUPE END ==="
        Pause-OnExit
        exit 0
    }

    $fingerprints = @{}
    $index = 0
    $movedCount = 0
    $skippedCount = 0
    $errorCount = 0

    foreach ($file in $files) {
        $index++
        try {
            $percent = [Math]::Min(100, [int](($index / $total) * 100))
            Write-Progress -Activity "Audio duplicate scan" -Status "Fingerprinting $index of $total" -PercentComplete $percent
            Write-Host "[DEDUPE] ($index/$total) $($file.FullName)"

            $output = $null
            try {
                $output = & $fpcalc -raw -length 120 -- "$($file.FullName)" 2>&1
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "[DEDUPE] Skipped (fpcalc exit $LASTEXITCODE): $($file.Name)" -ForegroundColor Yellow
                    $skippedCount++
                    continue
                }
            }
            catch {
                Write-Host "[DEDUPE] Skipped (fpcalc threw): $($file.Name) -> $($_.Exception.Message)" -ForegroundColor Yellow
                $skippedCount++
                continue
            }

            $fpLine = $output | Where-Object { $_ -is [string] -and $_ -like "FINGERPRINT=*" } | Select-Object -First 1

            if (-not $fpLine) {
                Write-Host "[DEDUPE] Skipped (no fingerprint): $($file.Name)"
                $skippedCount++
                continue
            }

            $fingerprint = $fpLine -replace "^FINGERPRINT=", ""

            if ($fingerprints.ContainsKey($fingerprint)) {
                $target = Join-Path $dupeRoot $file.Name

                if (Test-Path -LiteralPath $target) {
                    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
                    $ext = $file.Extension
                    $target = Join-Path $dupeRoot ("{0}__dup_{1}{2}" -f $baseName, $index, $ext)
                }

                Move-Item -LiteralPath $file.FullName -Destination $target -ErrorAction Stop
                Write-Host "[DEDUPE] Moved duplicate -> $target"
                $movedCount++
            }
            else {
                $fingerprints[$fingerprint] = $file.FullName
            }
        }
        catch {
            $errorCount++
            Write-Host "[DEDUPE] Error on $($file.Name): $($_.Exception.Message)" -ForegroundColor Red
            continue
        }
    }

    Write-Progress -Activity "Audio duplicate scan" -Completed
    Write-Host ""
    Write-Host "=== AUDIO DEDUPE END ==="
    Write-Host "Fingerprinted: $($total - $skippedCount - $errorCount) of $total"
    Write-Host "Duplicates moved: $movedCount"
    Write-Host "Skipped: $skippedCount"
    Write-Host "Errors: $errorCount"
    Write-Host ""
    Pause-OnExit
    exit 0
}
catch {
    Write-Err "Unhandled failure: $($_.Exception.Message)"
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    Pause-OnExit
    exit 1
}
