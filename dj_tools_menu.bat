@echo off
setlocal EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

:menu
cls
echo ==========================================
echo DJ Tools Menu
echo ==========================================
echo.
echo 1. Build new dated crate tree
echo 2. Clean / mark empty folders
echo 3. Run crate digger
echo 4. Dedupe audio (find duplicate MP3s)
echo 5. Camelot converter
echo 6. Camelot to comments
echo 7. Rekordbox XML generator
echo 8. Exit
echo.

set "CHOICE="
set /p "CHOICE=Choose an option (1-8, or Q to quit): "

if /I "%CHOICE%"=="q" goto end
if "%CHOICE%"=="1" goto build
if "%CHOICE%"=="2" goto clean
if "%CHOICE%"=="3" goto digcrate
if "%CHOICE%"=="4" goto dedupe_audio
if "%CHOICE%"=="5" goto camelot_converter
if "%CHOICE%"=="6" goto camelot_comments
if "%CHOICE%"=="7" goto rekordbox_xml
if "%CHOICE%"=="8" goto end

echo.
echo Invalid choice.
pause
goto menu

:build
cls
echo ==========================================
echo Build New Dated Crate Tree
echo ==========================================
echo.

set "PARENT_PATH="
set /p "PARENT_PATH=Enter the parent folder path (example: D:\), or Q to return to menu: "

if /I "%PARENT_PATH%"=="q" goto menu
if "%PARENT_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set "PARENT_PATH=%PARENT_PATH:"=%"

echo.
py "%ROOT_DIR%\create_folders\make_music_paths.py" "%PARENT_PATH%"
call :report_exit "Build crate tree" %ERRORLEVEL%
goto return_to_menu

:clean
cls
echo ==========================================
echo Clean / Mark Empty Folders
echo ==========================================
echo.

set "TARGET_PATH="
set /p "TARGET_PATH=Enter the folder to clean, or Q to return to menu: "

if /I "%TARGET_PATH%"=="q" goto menu
if "%TARGET_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set "TARGET_PATH=%TARGET_PATH:"=%"

echo.
py "%ROOT_DIR%\create_folders\clean_empty_music_folders.py" "%TARGET_PATH%"
call :report_exit "Clean folders" %ERRORLEVEL%
goto return_to_menu

:digcrate
cls
echo ==========================================
echo Crate Digger
echo ==========================================
echo.
call "%ROOT_DIR%\crate-digger\digcrate.bat"
call :report_exit "Crate digger" %ERRORLEVEL%
goto menu

:dedupe_audio
cls
echo ==========================================
echo Dedupe Audio
echo ==========================================
echo.
echo Recursively fingerprints every .mp3 under the folder you provide
echo and moves duplicates into a _dupes subfolder next to your music.
echo.

set "DEDUPE_PATH="
set /p "DEDUPE_PATH=Enter the folder path to scan recursively, or Q to return to menu: "

if /I "%DEDUPE_PATH%"=="q" goto menu
if "%DEDUPE_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set "DEDUPE_PATH=%DEDUPE_PATH:"=%"

echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%\crate-digger\dedupe_audio.ps1" "%DEDUPE_PATH%"
call :report_exit "Dedupe audio" %ERRORLEVEL%
goto return_to_menu

:camelot_converter
cls
echo ==========================================
echo Camelot Converter
echo ==========================================
echo.
echo This tool reads the musical key from your files, converts it to Camelot,
echo and can save that value into a tag, update the track title, and optionally rename the filename.
echo.

set "MUSIC_FOLDER="
set /p "MUSIC_FOLDER=Enter the root music folder to scan, or Q to return to menu: "

if /I "%MUSIC_FOLDER%"=="q" goto menu
if "%MUSIC_FOLDER%"=="" (
    echo.
    echo No folder entered.
    pause
    goto menu
)

set "MUSIC_FOLDER=%MUSIC_FOLDER:"=%"
set "DEST_ARG=--dest comment"
set "WRITE_ARGS="
set "RENAME_ARGS="
set "VERBOSE_ARG="
set "DEST_CHOICE="
set "WRITE_CHOICE="
set "RENAME_CHOICE="
set "VERBOSE_CHOICE="

echo.
echo Where should the Camelot value be saved?
echo   1. Comment tag ^(best default for most users^)
echo   2. Grouping tag
echo   3. Custom CAMELOT tag
set /p "DEST_CHOICE=Choose where to save it (1-3, default 1, or Q to return to menu): "
if /I "%DEST_CHOICE%"=="q" goto menu

if "%DEST_CHOICE%"=="2" set "DEST_ARG=--dest grouping"
if "%DEST_CHOICE%"=="3" set "DEST_ARG=--dest custom"

echo.
set /p "WRITE_CHOICE=Press Enter for a safe preview only, type W to write, or Q to return to menu: "
if /I "%WRITE_CHOICE%"=="q" goto menu
if /I "%WRITE_CHOICE%"=="W" set "WRITE_ARGS=--write"

echo.
echo Filename rename format: Camelot ^| Key ^| BPM - Artist - Title
echo The track title tag is also updated to: Camelot ^| Key - Title
set /p "RENAME_CHOICE=Also rename the files? (Y/N, default N, or Q to return to menu): "
if /I "%RENAME_CHOICE%"=="q" goto menu
if /I "%RENAME_CHOICE%"=="Y" set "RENAME_ARGS=--rename"

set /p "VERBOSE_CHOICE=Show detailed output? (Y/N, default Y, or Q to return to menu): "
if /I "%VERBOSE_CHOICE%"=="q" goto menu
if /I "%VERBOSE_CHOICE%"=="N" (set "VERBOSE_ARG=") else (set "VERBOSE_ARG=--verbose")

echo.
call :run_musickey "%ROOT_DIR%\musicKeyConversion\camelot_converter.py" "%MUSIC_FOLDER%" !DEST_ARG! !WRITE_ARGS! !RENAME_ARGS! !VERBOSE_ARG!
call :report_exit "Camelot converter" %ERRORLEVEL%
goto return_to_menu

:camelot_comments
cls
echo ==========================================
echo Camelot To Comments
echo ==========================================
echo.
echo This tool reads each file's musical key, converts it to Camelot,
echo writes Camelot ^| musical key ^| BPM into the comment tag,
echo and updates the track title to Camelot ^| musical key - Title.
echo File names stay unchanged unless you use the other converter tool.
echo.

set "MUSIC_FOLDER="
set /p "MUSIC_FOLDER=Enter the root music folder to scan, or Q to return to menu: "

if /I "%MUSIC_FOLDER%"=="q" goto menu
if "%MUSIC_FOLDER%"=="" (
    echo.
    echo No folder entered.
    pause
    goto menu
)

set "MUSIC_FOLDER=%MUSIC_FOLDER:"=%"
set "WRITE_ARGS="
set "VERBOSE_ARG="
set "WRITE_CHOICE="
set "VERBOSE_CHOICE="

echo.
set /p "WRITE_CHOICE=Press Enter for a safe preview only, type W to write, or Q to return to menu: "
if /I "%WRITE_CHOICE%"=="q" goto menu
if /I "%WRITE_CHOICE%"=="W" set "WRITE_ARGS=--write"

set /p "VERBOSE_CHOICE=Show detailed output? (Y/N, default Y, or Q to return to menu): "
if /I "%VERBOSE_CHOICE%"=="q" goto menu
if /I "%VERBOSE_CHOICE%"=="N" (set "VERBOSE_ARG=") else (set "VERBOSE_ARG=--verbose")

echo.
call :run_musickey "%ROOT_DIR%\musicKeyConversion\camelot_to_comments.py" "%MUSIC_FOLDER%" !WRITE_ARGS! !VERBOSE_ARG!
call :report_exit "Camelot to comments" %ERRORLEVEL%
goto return_to_menu

:rekordbox_xml
cls
echo ==========================================
echo Rekordbox XML Generator
echo ==========================================
echo.
echo This tool scans a Root/Genre/Energy/tracks folder structure
echo and creates a Rekordbox-compatible XML plus a matching log file.
echo.
call :run_python "%ROOT_DIR%\xml_generator\rekordbox_xml_generator.py"
call :report_exit "Rekordbox XML generator" %ERRORLEVEL%
goto return_to_menu

:run_musickey
if exist "%ROOT_DIR%\musicKeyConversion\.venv\Scripts\python.exe" (
    "%ROOT_DIR%\musicKeyConversion\.venv\Scripts\python.exe" %*
) else (
    py %*
)
exit /b %ERRORLEVEL%

:run_python
py %*
exit /b %ERRORLEVEL%

:report_exit
if not "%~2"=="0" (
    echo.
    echo [WARN] %~1 exited with code %~2.
    echo        Scroll up to see any error messages above.
)
exit /b 0

:return_to_menu
echo.
set /p "RETURN_TO_MENU=Press Enter to return to the menu..."
goto menu

:end
exit /b
