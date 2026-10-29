# Warns when the SoundCloud login in a cookies.txt file is about to run out,
# so sc_cookies.txt only needs re-exporting when it actually matters.
# Called by digcrate.bat. Prints nothing while the login has a month or more left.

param(
    [Parameter(Mandatory = $true)][string]$CookiesFile
)

$warnDays = 30

# Netscape cookies.txt columns: domain, subdomains, path, secure, expiry, name, value.
$line = Get-Content -LiteralPath $CookiesFile -ErrorAction SilentlyContinue |
    Where-Object { ($_ -split "`t")[5] -eq "oauth_token" } |
    Select-Object -First 1

# A missing token is already reported by digcrate.bat.
if (-not $line) { exit 0 }

$expires = [int64]0
if (-not [int64]::TryParse(($line -split "`t")[4], [ref]$expires) -or $expires -le 0) {
    exit 0  # session cookie with no fixed expiry
}

$expiry = [DateTimeOffset]::FromUnixTimeSeconds($expires).LocalDateTime
$expiryText = $expiry.ToString("yyyy-MM-dd")
$daysLeft = [int][Math]::Floor(($expiry - (Get-Date)).TotalDays)

if ($expiry -le (Get-Date)) {
    Write-Host "[WARN] Your SoundCloud login in sc_cookies.txt expired on $expiryText." -ForegroundColor Yellow
}
elseif ($daysLeft -lt $warnDays) {
    Write-Host "[WARN] Your SoundCloud login in sc_cookies.txt expires in $daysLeft day(s), on $expiryText." -ForegroundColor Yellow
}
else {
    exit 0
}
Write-Host "       Sign out and back in on soundcloud.com in Chrome, then re-export" -ForegroundColor Yellow
Write-Host "       sc_cookies.txt with the Get cookies.txt LOCALLY extension." -ForegroundColor Yellow
exit 0
