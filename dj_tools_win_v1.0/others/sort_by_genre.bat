@echo off
setlocal EnableDelayedExpansion

rem Double-click launcher for sort_by_genre.py.
rem Reads the genre tag on every MP3 sitting directly in the folder you give it,
rem or in its "00 new" folder, and moves each track into its numbered genre
rem folder. Tracks with no genre, a catch-all genre like "Dance & EDM", or a
rem genre outside the toolkit's taxonomy go into "00 new".

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "ROOT_DIR=%SCRIPT_DIR%\.."
set "SORT_PY=%SCRIPT_DIR%\sort_by_genre.py"

if not exist "%SORT_PY%" (
    echo ERROR: sort_by_genre.py not found in %SCRIPT_DIR%
    goto END
)

echo ==========================================
echo Sort By Genre
echo ==========================================
echo.
echo Moves every MP3 sitting directly in a folder, or in its "00 new"
echo folder, into the numbered genre folder for its genre tag, matching
echo the folders "Build / update genre folders" creates.
echo.
echo Tracks are only read for their tags - nothing is re-tagged.
echo.

set "MUSIC_FOLDER="
set /p "MUSIC_FOLDER=Enter the folder holding your MP3s, or Q to quit: "

rem Strip surrounding quotes BEFORE comparing or passing the value on,
rem because cmd's if-comparison breaks on embedded literal quotes.
if defined MUSIC_FOLDER set "MUSIC_FOLDER=!MUSIC_FOLDER:"=!"

if /I "!MUSIC_FOLDER!"=="q" goto END
if not defined MUSIC_FOLDER (
    echo.
    echo No folder entered.
    goto END
)

set "DRY_RUN_ARG=--dry-run"
set "ENERGY_ARG="
set "MOVE_CHOICE="
set "ENERGY_CHOICE="

echo.
set /p "MOVE_CHOICE=Press Enter for a safe preview only, type M to move the files, or Q to quit: "
if /I "%MOVE_CHOICE%"=="q" goto END
if /I "%MOVE_CHOICE%"=="M" set "DRY_RUN_ARG="

echo.
echo The Rekordbox XML generator only reads tracks inside high/mid/low folders.
set /p "ENERGY_CHOICE=Create high/mid/low folders inside each genre folder? (Y/N, default N): "
if /I "%ENERGY_CHOICE%"=="q" goto END
if /I "%ENERGY_CHOICE%"=="Y" set "ENERGY_ARG=--with-energy"

echo.
call :run_musickey "%SORT_PY%" "!MUSIC_FOLDER!" !DRY_RUN_ARG! !ENERGY_ARG!

if not "%ERRORLEVEL%"=="0" (
    echo.
    echo [WARN] Sort by genre exited with code %ERRORLEVEL%.
    echo        Scroll up to see any error messages above.
)

goto END

:run_musickey
rem sort_by_genre.py needs mutagen, which lives in the musicKeyConversion venv.
if exist "%ROOT_DIR%\musicKeyConversion\.venv\Scripts\python.exe" (
    "%ROOT_DIR%\musicKeyConversion\.venv\Scripts\python.exe" %*
) else (
    py %*
)
exit /b %ERRORLEVEL%

:END
echo.
set /p "EXITPROMPT=Press ENTER to exit: "
endlocal
