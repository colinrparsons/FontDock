@echo off
setlocal enabledelayedexpansion
REM FontDock Adobe Scripts Installer for Windows
REM Installs auto-activation scripts for Illustrator, Photoshop, and InDesign

echo =========================================
echo FontDock Adobe Scripts Installer (Windows)
echo =========================================
echo.

set SCRIPT_DIR=%~dp0
set INSTALLED=0
set SKIPPED=0

REM ============================================================
REM Illustrator
REM ============================================================
if exist "%SCRIPT_DIR%FontDockAutoActivate_Illustrator_Win.jsx" (
    set "ILL_DIR=%APPDATA%\Adobe\Startup Scripts CS6\Illustrator"
    if not exist "!ILL_DIR!" mkdir "!ILL_DIR!"
    copy /Y "%SCRIPT_DIR%FontDockAutoActivate_Illustrator_Win.jsx" "!ILL_DIR!\" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] Illustrator script installed
        set /a INSTALLED+=1
    ) else (
        echo   [FAIL] Failed to install Illustrator script
    )
) else (
    echo   [SKIP] Illustrator script not found
    set /a SKIPPED+=1
)

REM ============================================================
REM Photoshop
REM ============================================================
if exist "%SCRIPT_DIR%FontDockAutoActivate_Photoshop_Win.jsx" (
    set "PS_DIR=%APPDATA%\Adobe\Startup Scripts CS6\Adobe Photoshop"
    if not exist "!PS_DIR!" mkdir "!PS_DIR!"
    copy /Y "%SCRIPT_DIR%FontDockAutoActivate_Photoshop_Win.jsx" "!PS_DIR!\" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] Photoshop script installed
        set /a INSTALLED+=1
    ) else (
        echo   [FAIL] Failed to install Photoshop script
    )
) else (
    echo   [SKIP] Photoshop script not found
    set /a SKIPPED+=1
)

REM ============================================================
REM InDesign - uses versioned preferences path
REM ============================================================
if not exist "%SCRIPT_DIR%FontDockAutoActivate_InDesign_Win.jsx" (
    echo   [SKIP] InDesign script not found
    set /a SKIPPED+=1
    goto :indesign_done
)

set "ID_PREFS=%APPDATA%\Adobe\InDesign"
if not exist "!ID_PREFS!" goto :indesign_cs6_fallback

REM Find latest version directory
set "LATEST_VER="
for /f "delims=" %%v in ('dir /b /ad /o-n "!ID_PREFS!\Version*" 2^>nul') do (
    if not defined LATEST_VER set "LATEST_VER=%%v"
)

if not defined LATEST_VER goto :indesign_cs6_fallback

REM Detect locale
set "LOCALE="
if exist "!ID_PREFS!\!LATEST_VER!\en_GB" set "LOCALE=en_GB"
if exist "!ID_PREFS!\!LATEST_VER!\en_US" set "LOCALE=en_US"

if not defined LOCALE (
    echo   [SKIP] Could not detect InDesign locale
    set /a SKIPPED+=1
    goto :indesign_done
)

set "STARTUP_DIR=!ID_PREFS!\!LATEST_VER!\!LOCALE!\Scripts\Startup Scripts"
if not exist "!STARTUP_DIR!" mkdir "!STARTUP_DIR!"
copy /Y "%SCRIPT_DIR%FontDockAutoActivate_InDesign_Win.jsx" "!STARTUP_DIR!\" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] InDesign script installed ^(!LATEST_VER!/!LOCALE!^)
    set /a INSTALLED+=1
) else (
    echo   [FAIL] Failed to install InDesign script
)
goto :indesign_done

:indesign_cs6_fallback
set "ID_CS6_DIR=%APPDATA%\Adobe\Startup Scripts CS6\InDesign"
if not exist "!ID_CS6_DIR!" mkdir "!ID_CS6_DIR!"
copy /Y "%SCRIPT_DIR%FontDockAutoActivate_InDesign_Win.jsx" "!ID_CS6_DIR!\" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] InDesign script installed (CS6 fallback)
    set /a INSTALLED+=1
) else (
    echo   [FAIL] Failed to install InDesign script
)

:indesign_done

REM ============================================================
REM Summary
REM ============================================================
echo.
echo =========================================
echo Installation Complete: !INSTALLED! installed, !SKIPPED! skipped
echo =========================================
echo.
echo Auto-activation works via two mechanisms:
echo   * InDesign: startup script runs automatically on document open
echo   * Illustrator/Photoshop: FontDock client monitors open documents
echo     via COM automation and auto-activates fonts when new docs appear
echo.
echo Requirements:
echo   * FontDock client must be running
echo   * Client auto-detects installed Adobe app versions
echo.
echo To uninstall: uninstall.bat
echo To debug: run DebugFontInfo_*.jsx scripts manually in each app
