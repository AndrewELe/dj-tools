@echo off
setlocal EnableDelayedExpansion

rem Double-click launcher for rekordbox_genre_xml_generator.py.
rem Builds a Rekordbox XML from a genre-sorted folder, the layout
rem sort_by_genre.py produces, where tracks sit directly in their genre folder
rem instead of inside high/mid/low energy folders.
rem
rem For the dated crate tree with energy folders, use the "Rekordbox XML
rem generator" option in dj_tools_menu.bat instead.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "GEN_PY=%SCRIPT_DIR%\rekordbox_genre_xml_generator.py"

if not exist "%GEN_PY%" (
    echo ERROR: rekordbox_genre_xml_generator.py not found in %SCRIPT_DIR%
    goto END
)

echo ==========================================
echo Rekordbox XML Generator ^(genre folders^)
echo ==========================================
echo.
echo Point this at the parent folder holding your genre folders.
echo Every folder with tracks in it becomes a playlist, and nested
echo folders like house\deep house become nested playlist folders.
echo.
echo The XML and a matching log are written into that same folder.
echo Music files are only read, never changed.
echo.

set "MUSIC_FOLDER="
set /p "MUSIC_FOLDER=Enter the folder path, or Q to quit: "

rem Strip surrounding quotes BEFORE comparing or passing the value on,
rem because cmd's if-comparison breaks on embedded literal quotes.
if defined MUSIC_FOLDER set "MUSIC_FOLDER=!MUSIC_FOLDER:"=!"

if /I "!MUSIC_FOLDER!"=="q" goto END
if not defined MUSIC_FOLDER (
    echo.
    echo No folder entered.
    goto END
)

echo.
py "%GEN_PY%" "!MUSIC_FOLDER!"

if not "%ERRORLEVEL%"=="0" (
    echo.
    echo [WARN] Rekordbox genre XML generator exited with code %ERRORLEVEL%.
    echo        Scroll up to see any error messages above.
)

:END
echo.
set /p "EXITPROMPT=Press ENTER to exit: "
endlocal
