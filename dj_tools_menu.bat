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
echo 4. Camelot converter
echo 5. Camelot to comments
echo 6. Clean .bak files
echo 7. Rekordbox XML generator
echo 8. Exit
echo.

set "CHOICE="
set /p "CHOICE=Choose an option (1-8): "

if "%CHOICE%"=="1" goto build
if "%CHOICE%"=="2" goto clean
if "%CHOICE%"=="3" goto digcrate
if "%CHOICE%"=="4" goto camelot_converter
if "%CHOICE%"=="5" goto camelot_comments
if "%CHOICE%"=="6" goto bak_cleaner
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
set /p "PARENT_PATH=Enter the parent folder path (example: D:\): "

if "%PARENT_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set "PARENT_PATH=%PARENT_PATH:"=%"

echo.
py "%ROOT_DIR%\create_folders\make_music_paths.py" "%PARENT_PATH%"
goto return_to_menu

:clean
cls
echo ==========================================
echo Clean / Mark Empty Folders
echo ==========================================
echo.

set "TARGET_PATH="
set /p "TARGET_PATH=Enter the folder to clean: "

if "%TARGET_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set "TARGET_PATH=%TARGET_PATH:"=%"

echo.
py "%ROOT_DIR%\create_folders\clean_empty_music_folders.py" "%TARGET_PATH%"
goto return_to_menu

:digcrate
cls
echo ==========================================
echo Crate Digger
echo ==========================================
echo.
call "%ROOT_DIR%\crate-digger\digcrate.bat"
goto menu

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
set /p "MUSIC_FOLDER=Enter the root music folder to scan: "

if "%MUSIC_FOLDER%"=="" (
    echo.
    echo No folder entered.
    pause
    goto menu
)

set "MUSIC_FOLDER=%MUSIC_FOLDER:"=%"
set "DEST_ARG=--dest comment"
set "CUSTOM_NAME_ARG="
set "SOURCE_FIELD_ARG="
set "WRITE_ARGS="
set "RENAME_ARGS="
set "VERBOSE_ARG="
set "SHOW_MAP_ARG="
set "DEST_CHOICE="
set "CUSTOM_NAME="
set "SOURCE_FIELD="
set "WRITE_CHOICE="
set "BACKUP_CHOICE="
set "RENAME_CHOICE="
set "RENAME_PATTERN="
set "VERBOSE_CHOICE="
set "SHOW_MAP_CHOICE="

echo.
echo Where should the Camelot value be saved?
echo   1. Comment tag ^(best default for most users^)
echo   2. Grouping tag
echo   3. Custom tag name
set /p "DEST_CHOICE=Choose where to save it (1-3, default 1): "

if "%DEST_CHOICE%"=="2" set "DEST_ARG=--dest grouping"
if "%DEST_CHOICE%"=="3" (
    set "DEST_ARG=--dest custom"
    set /p "CUSTOM_NAME=Enter the custom tag name (press Enter for CAMELOT): "
    if not "%CUSTOM_NAME%"=="" set "CUSTOM_NAME_ARG=--custom-name ""%CUSTOM_NAME%"""
)

echo.
echo Leave the next prompt blank unless your music key is stored in a specific tag
echo such as TKEY, INITIALKEY, or KEY.
set /p "SOURCE_FIELD=Key source tag override (press Enter to auto-detect): "
if not "%SOURCE_FIELD%"=="" set "SOURCE_FIELD_ARG=--source-field ""%SOURCE_FIELD%"""

echo.
set /p "WRITE_CHOICE=Press Enter for a safe preview only, or type W to actually write tag changes: "
if /I "%WRITE_CHOICE%"=="W" (
    set "WRITE_ARGS=--write"
    set /p "BACKUP_CHOICE=Create .bak backup files before writing? (Y/N, default Y): "
    if /I not "%BACKUP_CHOICE%"=="N" set "WRITE_ARGS=!WRITE_ARGS! --backup"
)

echo.
echo Filename rename format:
echo   Camelot ^| Musical Key ^| BPM - Artist - Title
echo BPM is skipped automatically if it is missing.
echo The track title tag is also updated to:
echo   Camelot ^| Musical Key - Title
set /p "RENAME_CHOICE=Also rename the files using that format? (Y/N, default N): "
if /I "%RENAME_CHOICE%"=="Y" (
    set "RENAME_ARGS=--rename"
    set /p "RENAME_PATTERN=Optional custom filename pattern (press Enter to use the format above): "
    if not "%RENAME_PATTERN%"=="" set "RENAME_ARGS=!RENAME_ARGS! --rename-pattern ""%RENAME_PATTERN%"""
)

set /p "VERBOSE_CHOICE=Show detailed output while processing? (Y/N, default Y): "
if /I not "%VERBOSE_CHOICE%"=="N" set "VERBOSE_ARG=--verbose"

set /p "SHOW_MAP_CHOICE=Show the Camelot key map before processing? (Y/N, default N): "
if /I "%SHOW_MAP_CHOICE%"=="Y" set "SHOW_MAP_ARG=--show-map"

echo.
call :run_musickey "%ROOT_DIR%\musicKeyConversion\camelot_converter.py" "%MUSIC_FOLDER%" !DEST_ARG! !CUSTOM_NAME_ARG! !SOURCE_FIELD_ARG! !WRITE_ARGS! !RENAME_ARGS! !VERBOSE_ARG! !SHOW_MAP_ARG!
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
set /p "MUSIC_FOLDER=Enter the root music folder to scan: "

if "%MUSIC_FOLDER%"=="" (
    echo.
    echo No folder entered.
    pause
    goto menu
)

set "MUSIC_FOLDER=%MUSIC_FOLDER:"=%"
set "SOURCE_FIELD_ARG="
set "WRITE_ARGS="
set "VERBOSE_ARG="
set "SHOW_MAP_ARG="
set "SOURCE_FIELD="
set "WRITE_CHOICE="
set "BACKUP_CHOICE="
set "VERBOSE_CHOICE="
set "SHOW_MAP_CHOICE="

echo Leave the next prompt blank unless your music key is stored in a specific tag
echo such as TKEY, INITIALKEY, or KEY.
set /p "SOURCE_FIELD=Key source tag override (press Enter to auto-detect): "
if not "%SOURCE_FIELD%"=="" set "SOURCE_FIELD_ARG=--source-field ""%SOURCE_FIELD%"""

echo.
set /p "WRITE_CHOICE=Press Enter for a safe preview only, or type W to actually write comment tags: "
if /I "%WRITE_CHOICE%"=="W" (
    set "WRITE_ARGS=--write"
    set /p "BACKUP_CHOICE=Create .bak backup files before writing? (Y/N, default Y): "
    if /I not "%BACKUP_CHOICE%"=="N" set "WRITE_ARGS=!WRITE_ARGS! --backup"
)

set /p "VERBOSE_CHOICE=Show detailed output while processing? (Y/N, default Y): "
if /I not "%VERBOSE_CHOICE%"=="N" set "VERBOSE_ARG=--verbose"

set /p "SHOW_MAP_CHOICE=Show the Camelot key map before processing? (Y/N, default N): "
if /I "%SHOW_MAP_CHOICE%"=="Y" set "SHOW_MAP_ARG=--show-map"

echo.
call :run_musickey "%ROOT_DIR%\musicKeyConversion\camelot_to_comments.py" "%MUSIC_FOLDER%" !SOURCE_FIELD_ARG! !WRITE_ARGS! !VERBOSE_ARG! !SHOW_MAP_ARG!
goto return_to_menu

:bak_cleaner
cls
echo ==========================================
echo Clean .bak Files
echo ==========================================
echo.
echo This launches the backup cleaner.
echo The cleaner will prompt for the folder path to scan recursively.
echo.
call :run_musickey "%ROOT_DIR%\musicKeyConversion\bakCleaner.py"
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
goto return_to_menu

:run_musickey
if exist "%ROOT_DIR%\musicKeyConversion\.venv\Scripts\python.exe" (
    "%ROOT_DIR%\musicKeyConversion\.venv\Scripts\python.exe" %*
) else (
    py %*
)
exit /b

:run_python
py %*
exit /b

:return_to_menu
echo.
set /p "RETURN_TO_MENU=Press Enter to return to the menu..."
goto menu

:end
exit /b
