param(
    [string]$MusicRoot
)

$base = $PSScriptRoot
$fpcalc = Join-Path $base "fpcalc.exe"

if (-not (Test-Path $fpcalc)) {
    Write-Host "ERROR: fpcalc.exe not found at $fpcalc" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command $fpcalc -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Unable to execute local fpcalc.exe at $fpcalc" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($MusicRoot)) {
    $defaultRoot = "C:\Music\SoundCloud"
    $inputRoot = Read-Host "Enter music root path or press ENTER for default [$defaultRoot]"
    if ([string]::IsNullOrWhiteSpace($inputRoot)) {
        $MusicRoot = $defaultRoot
    }
    else {
        $MusicRoot = $inputRoot.Trim('"')
    }
}

if (-not (Test-Path $MusicRoot)) {
    Write-Host "ERROR: music root not found: $MusicRoot" -ForegroundColor Red
    exit 1
}

$dupeRoot = Join-Path $MusicRoot "_dupes"

if (-not (Test-Path $dupeRoot)) {
    New-Item -ItemType Directory -Path $dupeRoot | Out-Null
}

$dupeRootNormalized = [System.IO.Path]::GetFullPath($dupeRoot)

$files = Get-ChildItem -Path $MusicRoot -Recurse -File -Include *.mp3 |
    Where-Object {
        $full = [System.IO.Path]::GetFullPath($_.FullName)
        -not $full.StartsWith($dupeRootNormalized, [System.StringComparison]::OrdinalIgnoreCase)
    }

$total = $files.Count
$index = 0

Write-Host ""
Write-Host "=== AUDIO DEDUPE START ==="
Write-Host "Tool folder: $base"
Write-Host "Music root: $MusicRoot"
Write-Host "Duplicate folder: $dupeRoot"
Write-Host "MP3 files to fingerprint: $total"
Write-Host ""

$fingerprints = @{}

foreach ($file in $files) {
    $index++
    Write-Progress -Activity "Audio duplicate scan" -Status "Fingerprinting $index of $total" -PercentComplete (($index / $total) * 100)
    Write-Host "[DEDUPE] ($index/$total) $($file.FullName)"

    try {
        $output = & $fpcalc -raw -length 120 "$($file.FullName)" 2>$null
    }
    catch {
        Write-Host "[DEDUPE] Skipped (fpcalc failed): $($file.Name)" -ForegroundColor Yellow
        continue
    }

    $fpLine = $output | Where-Object { $_ -like "FINGERPRINT=*" }

    if (-not $fpLine) {
        Write-Host "[DEDUPE] Skipped (no fingerprint): $($file.Name)"
        continue
    }

    $fingerprint = $fpLine -replace "^FINGERPRINT=", ""

    if ($fingerprints.ContainsKey($fingerprint)) {
        $target = Join-Path $dupeRoot $file.Name

        if (Test-Path $target) {
            $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
            $ext = $file.Extension
            $target = Join-Path $dupeRoot ("{0}__dup_{1}{2}" -f $baseName, $index, $ext)
        }

        Move-Item -LiteralPath $file.FullName -Destination $target
        Write-Host "[DEDUPE] Moved duplicate -> $target"
    }
    else {
        $fingerprints[$fingerprint] = $file.FullName
    }
}

Write-Progress -Activity "Audio duplicate scan" -Completed
Write-Host ""
Write-Host "=== AUDIO DEDUPE END ==="
Write-Host ""
