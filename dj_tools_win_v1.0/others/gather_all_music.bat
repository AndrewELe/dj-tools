@echo off
setlocal

rem Double-click launcher for gather_all_music.ps1.
rem Moves every downloaded track out of its per-artist subfolder into a single
rem "All Music" folder inside the music root, so you don't have to click into
rem each artist folder to reach the songs.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "GATHER_PS1=%SCRIPT_DIR%\gather_all_music.ps1"

if not exist "%GATHER_PS1%" (
    echo ERROR: gather_all_music.ps1 not found in %SCRIPT_DIR%
    goto END
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%GATHER_PS1%"

:END
echo.
set /p "EXITPROMPT=Press ENTER to exit: "
endlocal
