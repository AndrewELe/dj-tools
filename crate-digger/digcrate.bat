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

echo.
echo ========================================
echo   LETS FUCKING GOOOOOOOOOOOOOOOOOO
echo ========================================
echo.
echo Controls at startup:
echo   ENTER = step through each source
echo   S     = skip current source
echo   A     = run everything automatically
echo   Q     = quit now
echo.

set /p "USERINPUT=Press ENTER, A, or Q: "
if /I "%USERINPUT%"=="A" set "MODE=AUTO"
if /I "%USERINPUT%"=="Q" goto END

echo.
echo Working folder: %SCRIPT_DIR%
echo.

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
    set /p "STEPINPUT=ENTER = continue, S = skip, A = auto-run rest, Q = quit: "
    if /I "%STEPINPUT%"=="A" set "MODE=AUTO"
    if /I "%STEPINPUT%"=="Q" exit /b 1
    if /I "%STEPINPUT%"=="S" exit /b 0
)

echo ----------------------------------------
echo %LABEL%: %URL%
echo ----------------------------------------
"%YTDLP%" --config-location "%YTDLPCONF%" --ignore-errors --no-abort-on-error "%URL%"
exit /b 0

:RUN_DISCOVERED
set "LABEL=%~1"
set "URL=%~2"

if /I "%MODE%"=="STEP" (
    echo ----------------------------------------
    echo %LABEL%: %URL%
    echo ----------------------------------------
    set /p "STEPINPUT=ENTER = continue, S = skip, A = auto-run rest, Q = quit: "
    if /I "%STEPINPUT%"=="A" set "MODE=AUTO"
    if /I "%STEPINPUT%"=="Q" exit /b 1
    if /I "%STEPINPUT%"=="S" exit /b 0
)

echo ----------------------------------------
echo %LABEL%: %URL%
echo ----------------------------------------
"%YTDLP%" --config-location "%YTDLPCONF%" --ignore-errors --no-abort-on-error --playlist-end 5 "%URL%"
exit /b 0

:END
:END
echo.
echo ========================================
echo   CRATE UPDATE COMPLETE
echo ========================================
echo.
echo Started at: %STARTTIME%
echo Finished at: %TIME%
echo.

if exist "%DEDUPE_PS1%" (
    set /p "RUNDEDUPE=Run audio dedupe now? (Y/N): "
    if /I "%RUNDEDUPE%"=="Y" (
        echo.
        echo Running audio dedupe...
        powershell -NoProfile -ExecutionPolicy Bypass -File "%DEDUPE_PS1%"
    )
)

pause
endlocal
