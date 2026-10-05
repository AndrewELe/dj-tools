@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"

set "MODE=STEP"
set "STARTTIME=%TIME%"
set "YTDLP=%SCRIPT_DIR%\yt-dlp.exe"
set "YTDLPCONF=%SCRIPT_DIR%\yt-dlp.conf"
set "DISCOVER_PS1=%SCRIPT_DIR%\discover.ps1"
set "DEDUPE_PS1=%SCRIPT_DIR%\dedupe_audio.ps1"
set "SOURCES_FILE=%SCRIPT_DIR%\sources.txt"
set "CRAWLER_FILE=%SCRIPT_DIR%\crawler.txt"
set "DISCOVERED_FILE=%SCRIPT_DIR%\discovered_sources.txt"
set "FULL_DOWNLOAD_URL=https://soundcloud.com/druleprivate/likes"
if not defined DJTOOLS_MUSIC_ROOT (
    set "DJTOOLS_MUSIC_ROOT=C:\Music\SoundCloud"
)
set "DOWNLOAD_ROOT=%DJTOOLS_MUSIC_ROOT%"
set "YTDLP_OUTPUT_TEMPLATE=%DOWNLOAD_ROOT%\%%(artist,creator,uploader)s - %%(title)s.%%(ext)s"
set "ARCHIVE_FILE=%SCRIPT_DIR%\archive.txt"

rem --- SoundCloud login cookies (raises the rate-limit ceiling) -----------
rem Logging in as your account makes SoundCloud throttle far less aggressively
rem than anonymous traffic. Two ways to supply cookies:
rem
rem   1. Cookies file (recommended on Windows): drop an exported cookies.txt
rem      named "sc_cookies.txt" next to this script and it is picked up
rem      automatically. Or point DJTOOLS_SC_COOKIES_FILE at any path. This is
rem      the reliable option because Chrome locks its own cookie DB and (v127+)
rem      encrypts it in a way yt-dlp cannot read live on Windows.
rem
rem   2. Live from a browser: set DJTOOLS_SC_COOKIES_BROWSER (chrome, edge,
rem      firefox, brave). Firefox works while open; Chrome/Edge usually do NOT
rem      on current Windows versions (see above).
rem
rem Precedence: explicit file > sc_cookies.txt next to the script > browser.
rem With no cookies file and no browser set, runs anonymously (with a warning).
if not defined DJTOOLS_SC_COOKIES_BROWSER (
    set "DJTOOLS_SC_COOKIES_BROWSER=none"
)
if not defined DJTOOLS_SC_COOKIES_FILE (
    if exist "%SCRIPT_DIR%\sc_cookies.txt" (
        set "DJTOOLS_SC_COOKIES_FILE=%SCRIPT_DIR%\sc_cookies.txt"
    )
)
set "COOKIE_ARGS="
if defined DJTOOLS_SC_COOKIES_FILE (
    set "COOKIE_ARGS=--cookies "%DJTOOLS_SC_COOKIES_FILE%""
    echo [OK] Using SoundCloud login cookies from: !DJTOOLS_SC_COOKIES_FILE!
    findstr /C:"oauth_token" "!DJTOOLS_SC_COOKIES_FILE!" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] No oauth_token in that cookies file - you are NOT logged in.
        echo        Re-export sc_cookies.txt while signed in to soundcloud.com.
    )
) else if /I not "%DJTOOLS_SC_COOKIES_BROWSER%"=="none" (
    set "COOKIE_ARGS=--cookies-from-browser %DJTOOLS_SC_COOKIES_BROWSER%"
    echo [OK] Using SoundCloud login cookies from browser: %DJTOOLS_SC_COOKIES_BROWSER%
) else (
    echo [WARN] No sc_cookies.txt found - downloading ANONYMOUSLY.
    echo        No Go+ 256kbps streams and heavier throttling.
)

echo.
echo ========================================
echo   LETS FUCKING GOOOOOOOOOOOOOOOOOO
echo ========================================
echo.
echo Controls at startup:
echo   ENTER = step through each source
echo   S     = skip current source
echo   A     = run everything automatically (you can press Q during a download
echo           to stop after the current source finishes)
echo   Q     = return to main menu now
echo.

set "USERINPUT="
set /p "USERINPUT=Press ENTER, A, or Q to return to main menu: "
if /I "%USERINPUT%"=="A" set "MODE=AUTO"
if /I "%USERINPUT%"=="Q" goto END

echo.
echo Working folder: %SCRIPT_DIR%
echo.

call :CHECK_INTERNET
if errorlevel 1 set "PRECHECK_WARNING=1"

call :CHECK_SOUNDCLOUD
if errorlevel 1 set "PRECHECK_WARNING=1"

if defined PRECHECK_WARNING (
    call :PROMPT_AFTER_WARNINGS
    if errorlevel 1 goto EXIT_NOW
)

if not exist "%SOURCES_FILE%" (
    echo ERROR: sources.txt not found in %SCRIPT_DIR%
    goto END
)

if not exist "%CRAWLER_FILE%" (
    echo ERROR: crawler.txt not found in %SCRIPT_DIR%
    goto END
)

if not exist "%YTDLP%" (
    echo ERROR: yt-dlp.exe not found in %SCRIPT_DIR%
    goto END
)

if not exist "%YTDLPCONF%" (
    echo ERROR: yt-dlp.conf not found in %SCRIPT_DIR%
    goto END
)

call :PREPARE_OUTPUT_ROOT
if errorlevel 1 goto END

call :UPDATE_YTDLP_IF_STALE

echo Checking main sources...
echo.

set COUNT=0
for /f "usebackq tokens=* delims=" %%i in ("%SOURCES_FILE%") do (
    if not "%%~i"=="" (
        set "LINE=%%~i"
        if /I not "!LINE:~0,1!"=="#" (
            set /a COUNT+=1
            call :RUN_SOURCE "Source !COUNT!" "%%i"
            if errorlevel 1 goto END
        )
    )
)

echo.
echo Checking crawler seeds...
echo.

set COUNT=0
for /f "usebackq tokens=* delims=" %%i in ("%CRAWLER_FILE%") do (
    if not "%%~i"=="" (
        set "LINE=%%~i"
        if /I not "!LINE:~0,1!"=="#" (
            set /a COUNT+=1
            call :RUN_SOURCE "Crawler !COUNT!" "%%i"
            if errorlevel 1 goto END
        )
    )
)

echo.
echo Running discovery crawler...
echo.

if exist "%DISCOVER_PS1%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%DISCOVER_PS1%"
) else (
    echo WARNING: discover.ps1 not found, skipping discovery crawler.
)

echo.
echo Crawling discovered sources...
echo.

if exist "%DISCOVERED_FILE%" (
    set COUNT=0
    for /f "usebackq tokens=* delims=" %%i in ("%DISCOVERED_FILE%") do (
        if not "%%~i"=="" (
            set "LINE=%%~i"
            if /I not "!LINE:~0,1!"=="#" (
                set /a COUNT+=1
                call :RUN_DISCOVERED "Discovered !COUNT!" "%%i"
                if errorlevel 1 goto END
            )
        )
    )
) else (
    echo No discovered_sources.txt found, skipping discovered sources.
)

goto END

:RUN_SOURCE
set "LABEL=%~1"
set "URL=%~2"

if /I "%MODE%"=="STEP" (
    echo ----------------------------------------
    echo %LABEL%: %URL%
    echo ----------------------------------------
    set "STEPINPUT="
    set /p "STEPINPUT=ENTER = continue, S = skip, A = auto-run rest, Q = return to main menu: "
    if /I "!STEPINPUT!"=="A" set "MODE=AUTO"
    if /I "!STEPINPUT!"=="Q" exit /b 1
    if /I "!STEPINPUT!"=="S" exit /b 0
)

echo ----------------------------------------
echo %LABEL%: %URL%
echo ----------------------------------------
call :GET_PLAYLIST_ARGS "%URL%"
"%YTDLP%" --config-location "%YTDLPCONF%" %COOKIE_ARGS% --download-archive "%ARCHIVE_FILE%" --no-update -o "%YTDLP_OUTPUT_TEMPLATE%" --ignore-errors --no-abort-on-error %PLAYLIST_ARGS% "%URL%"
call :CHECK_QUIT
if errorlevel 1 exit /b 1
exit /b 0

:RUN_DISCOVERED
set "LABEL=%~1"
set "URL=%~2"

if /I "%MODE%"=="STEP" (
    echo ----------------------------------------
    echo %LABEL%: %URL%
    echo ----------------------------------------
    set "STEPINPUT="
    set /p "STEPINPUT=ENTER = continue, S = skip, A = auto-run rest, Q = return to main menu: "
    if /I "!STEPINPUT!"=="A" set "MODE=AUTO"
    if /I "!STEPINPUT!"=="Q" exit /b 1
    if /I "!STEPINPUT!"=="S" exit /b 0
)

echo ----------------------------------------
echo %LABEL%: %URL%
echo ----------------------------------------
call :GET_PLAYLIST_ARGS "%URL%"
"%YTDLP%" --config-location "%YTDLPCONF%" %COOKIE_ARGS% --download-archive "%ARCHIVE_FILE%" --no-update -o "%YTDLP_OUTPUT_TEMPLATE%" --ignore-errors --no-abort-on-error %PLAYLIST_ARGS% "%URL%"
call :CHECK_QUIT
if errorlevel 1 exit /b 1
exit /b 0

:CHECK_QUIT
rem In AUTO mode, give the user a brief window to press Q after each download.
rem Any Q queued during the download (via the cmd keyboard buffer) is also caught.
if /I not "%MODE%"=="AUTO" exit /b 0
echo.
choice /T 2 /D N /C QN /M "Press Q to stop after this source (continuing in 2s)"
if errorlevel 2 exit /b 0
if errorlevel 1 (
    echo.
    echo [USER] Q detected. Returning to main menu after this source.
    exit /b 1
)
exit /b 0

:GET_PLAYLIST_ARGS
set "TARGET_URL=%~1"
set "PLAYLIST_ARGS=--playlist-end 15"
if /I "%TARGET_URL%"=="%FULL_DOWNLOAD_URL%" set "PLAYLIST_ARGS="
if /I "%TARGET_URL%"=="%FULL_DOWNLOAD_URL%/" set "PLAYLIST_ARGS="
exit /b 0

:PREPARE_OUTPUT_ROOT
echo Checking download root...
if not exist "%DOWNLOAD_ROOT%" (
    mkdir "%DOWNLOAD_ROOT%" 2>nul
)
if not exist "%DOWNLOAD_ROOT%" (
    echo ERROR: Could not create download root: %DOWNLOAD_ROOT%
    echo        Set DJTOOLS_MUSIC_ROOT to a writable folder and try again.
    exit /b 1
)
set "WRITE_TEST_FILE=%DOWNLOAD_ROOT%\.djtools_write_test.tmp"
break > "%WRITE_TEST_FILE%" 2>nul
if errorlevel 1 (
    echo ERROR: Download root is not writable: %DOWNLOAD_ROOT%
    echo        Set DJTOOLS_MUSIC_ROOT to a writable folder and try again.
    exit /b 1
)
del "%WRITE_TEST_FILE%" >nul 2>&1
echo [OK] Download root is ready: %DOWNLOAD_ROOT%
exit /b 0

:CHECK_UPDATE_STAMP
rem Returns errorlevel 0 if stamp is fresh (less than 7 days old),
rem errorlevel 1 if the stamp is missing or older than 7 days.
set "STAMP_FILE=%SCRIPT_DIR%\.last_update_check"
if not exist "%STAMP_FILE%" exit /b 1
powershell -NoProfile -Command "if (((Get-Date) - (Get-Item '%STAMP_FILE%').LastWriteTime).TotalDays -ge 7) { exit 1 } else { exit 0 }"
exit /b %ERRORLEVEL%

:UPDATE_YTDLP_IF_STALE
rem Runs `yt-dlp -U` at most once per week. Refreshes the stamp
rem afterwards even on failure so a broken update server doesn't make
rem us retry every single run.
call :CHECK_UPDATE_STAMP
if not errorlevel 1 exit /b 0
echo.
echo ----------------------------------------
echo Checking for yt-dlp updates ^(weekly^)...
echo ----------------------------------------
"%YTDLP%" -U
echo. > "%SCRIPT_DIR%\.last_update_check"
echo.
exit /b 0

:CHECK_INTERNET
echo Checking internet connectivity...
ping -n 1 -w 1000 1.1.1.1 >nul 2>&1
if errorlevel 1 (
    echo [WARN] No general internet connection detected by ping.
    echo        Some networks block ICMP even when downloads still work.
    exit /b 1
)
echo [OK] Internet connectivity looks good.
exit /b 0

:CHECK_SOUNDCLOUD
echo Checking SoundCloud reachability...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'https://soundcloud.com/' -Method Get -MaximumRedirection 0 -TimeoutSec 5; if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { exit 0 } else { exit 1 } } catch [System.Net.WebException] { if ($_.Exception.Response -and ([int]$_.Exception.Response.StatusCode) -ge 200 -and ([int]$_.Exception.Response.StatusCode) -lt 400) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [WARN] SoundCloud appears unreachable right now.
    echo        SoundCloud sources may fail, but other sources can still work.
    exit /b 1
)
echo [OK] SoundCloud is reachable.
exit /b 0

:PROMPT_AFTER_WARNINGS
echo.
echo One or more connectivity checks raised warnings.
echo   C = continue into crate digger anyway
echo   M = return to the main menu
set "WARN_CHOICE="
set /p "WARN_CHOICE=Choose C, M, or Q to return to main menu (default C): "
if /I "%WARN_CHOICE%"=="M" exit /b 1
if /I "%WARN_CHOICE%"=="Q" exit /b 1
exit /b 0

:END
echo.
echo ========================================
echo   CRATE UPDATE COMPLETE
echo ========================================
echo.
echo Started at: %STARTTIME%
echo Finished at: %TIME%
echo.
echo To dedupe duplicate MP3s, use option 4 in the main DJ Tools menu.
echo.

:CLEAN_EXIT
set /p "EXITPROMPT=Press ENTER to exit: "
:EXIT_NOW
endlocal
