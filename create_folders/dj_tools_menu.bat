@echo off
setlocal

:menu
cls
echo ==========================================
echo DJ Tools Menu
echo ==========================================
echo.
echo 1. Build new dated crate tree
echo 2. Clean / mark empty folders
echo 3. Exit
echo.

set /p CHOICE=Choose an option (1-3): 

if "%CHOICE%"=="1" goto build
if "%CHOICE%"=="2" goto clean
if "%CHOICE%"=="3" goto end

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

set /p PARENT_PATH=Enter the parent folder path (example: D:\): 

if "%PARENT_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set PARENT_PATH=%PARENT_PATH:"=%

echo.
py "%~dp0make_music_paths.py" "%PARENT_PATH%"
echo.
set /p RETURN_TO_MENU=Press Enter to return to the menu...
goto menu

:clean
cls
echo ==========================================
echo Clean / Mark Empty Folders
echo ==========================================
echo.

set /p TARGET_PATH=Enter the folder to clean: 

if "%TARGET_PATH%"=="" (
    echo.
    echo No path entered.
    pause
    goto menu
)

set TARGET_PATH=%TARGET_PATH:"=%

echo.
py "%~dp0clean_empty_music_folders.py" "%TARGET_PATH%"
echo.
set /p RETURN_TO_MENU=Press Enter to return to the menu...
goto menu

:end
exit /b