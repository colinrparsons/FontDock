@echo off
REM FontDock Adobe Scripts Uninstaller for Windows
REM Removes auto-activation scripts for Illustrator, Photoshop, and InDesign

echo =========================================
echo FontDock Adobe Scripts Uninstaller (Windows)
echo =========================================
echo.

set REMOVED=0

REM ============================================================
REM Illustrator
REM ============================================================
set "ILL_DIR=%APPDATA%\Adobe\Startup Scripts CS6\Illustrator"
set "ILL_SCRIPT=%ILL_DIR%\FontDockAutoActivate_Illustrator_Win.jsx"
if exist "%ILL_SCRIPT%" (
    del "%ILL_SCRIPT%"
    echo   [OK] Removed Illustrator script
    set /a REMOVED+=1
) else (
    echo   [SKIP] Illustrator script not found
)

REM ============================================================
REM Photoshop
REM ============================================================
set "PS_DIR=%APPDATA%\Adobe\Startup Scripts CS6\Adobe Photoshop"
set "PS_SCRIPT=%PS_DIR%\FontDockAutoActivate_Photoshop_Win.jsx"
if exist "%PS_SCRIPT%" (
    del "%PS_SCRIPT%"
    echo   [OK] Removed Photoshop script
    set /a REMOVED+=1
) else (
    echo   [SKIP] Photoshop script not found
)

REM ============================================================
REM InDesign - check both CS6 and versioned preferences paths
REM ============================================================
set "ID_CS6_DIR=%APPDATA%\Adobe\Startup Scripts CS6\InDesign"
set "ID_PREFS=%APPDATA%\Adobe\InDesign"

REM Remove from CS6 startup scripts
set "ID_CS6_SCRIPT=%ID_CS6_DIR%\FontDockAutoActivate_InDesign_Win.jsx"
if exist "%ID_CS6_SCRIPT%" (
    del "%ID_CS6_SCRIPT%"
    echo   [OK] Removed InDesign script (CS6)
    set /a REMOVED+=1
)

REM Remove from versioned preferences
if exist "%ID_PREFS%" (
    for /d %%v in ("%ID_PREFS%\Version*") do (
        for /d %%l in ("%%v\en_*") do (
            set "STARTUP=%%l\Scripts\Startup Scripts"
            if exist "!STARTUP!\FontDockAutoActivate_InDesign_Win.jsx" (
                del "!STARTUP!\FontDockAutoActivate_InDesign_Win.jsx"
                echo   [OK] Removed InDesign script (versioned prefs)
                set /a REMOVED+=1
            )
        )
    )
)

if %REMOVED% equ 0 (
    echo   [SKIP] No InDesign scripts found
)

REM ============================================================
REM Summary
REM ============================================================
echo.
echo =========================================
echo Uninstallation Complete: %REMOVED% scripts removed
echo =========================================
echo.
echo Please restart Adobe applications for changes to take effect.
