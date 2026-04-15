#!/bin/bash

# FontDock Adobe Scripts Installer
# Installs auto-activation scripts for Illustrator, Photoshop, and InDesign

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "FontDock Adobe Scripts Installer"
echo "========================================="
echo ""

INSTALLED=0
SKIPPED=0

# ============================================================
# Illustrator
# ============================================================
if [ -f "$SCRIPT_DIR/FontDockAutoActivate_Illustrator.jsx" ]; then
    ILLUSTRATOR_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator"
    mkdir -p "$ILLUSTRATOR_DIR"
    cp "$SCRIPT_DIR/FontDockAutoActivate_Illustrator.jsx" "$ILLUSTRATOR_DIR/"
    if [ $? -eq 0 ]; then
        echo "✅ Illustrator script installed"
        INSTALLED=$((INSTALLED + 1))
    else
        echo "❌ Failed to install Illustrator script"
    fi
else
    echo "⚠️  Illustrator script not found (skipping)"
    SKIPPED=$((SKIPPED + 1))
fi

# ============================================================
# Photoshop
# ============================================================
if [ -f "$SCRIPT_DIR/FontDockAutoActivate_Photoshop.jsx" ]; then
    PHOTOSHOP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop"
    mkdir -p "$PHOTOSHOP_DIR"
    cp "$SCRIPT_DIR/FontDockAutoActivate_Photoshop.jsx" "$PHOTOSHOP_DIR/"
    if [ $? -eq 0 ]; then
        echo "✅ Photoshop script installed"
        INSTALLED=$((INSTALLED + 1))
    else
        echo "❌ Failed to install Photoshop script"
    fi
else
    echo "⚠️  Photoshop script not found (skipping)"
    SKIPPED=$((SKIPPED + 1))
fi

# ============================================================
# InDesign - uses versioned preferences path
# ============================================================
if [ -f "$SCRIPT_DIR/FontDockAutoActivate_InDesign.jsx" ]; then
    INDESIGN_PREFS="$HOME/Library/Preferences/Adobe InDesign"
    if [ -d "$INDESIGN_PREFS" ]; then
        # Find latest version and locale
        LATEST_VERSION=$(ls "$INDESIGN_PREFS" 2>/dev/null | grep "Version" | sort -V | tail -n 1)
        if [ -n "$LATEST_VERSION" ]; then
            # Detect locale
            LOCALE=""
            for loc in en_GB en_US; do
                if [ -d "$INDESIGN_PREFS/$LATEST_VERSION/$loc" ]; then
                    LOCALE="$loc"
                    break
                fi
            done
            
            if [ -n "$LOCALE" ]; then
                STARTUP_DIR="$INDESIGN_PREFS/$LATEST_VERSION/$LOCALE/Scripts/Startup Scripts"
                mkdir -p "$STARTUP_DIR"
                cp "$SCRIPT_DIR/FontDockAutoActivate_InDesign.jsx" "$STARTUP_DIR/"
                if [ $? -eq 0 ]; then
                    echo "✅ InDesign script installed ($LATEST_VERSION/$LOCALE)"
                    INSTALLED=$((INSTALLED + 1))
                else
                    echo "❌ Failed to install InDesign script"
                fi
            else
                echo "⚠️  Could not detect InDesign locale (skipping)"
                SKIPPED=$((SKIPPED + 1))
            fi
        else
            echo "⚠️  No InDesign version found in preferences (skipping)"
            SKIPPED=$((SKIPPED + 1))
        fi
    else
        # Fallback: also install to CS6 startup scripts
        INDESIGN_CS6_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/InDesign"
        mkdir -p "$INDESIGN_CS6_DIR"
        cp "$SCRIPT_DIR/FontDockAutoActivate_InDesign.jsx" "$INDESIGN_CS6_DIR/"
        if [ $? -eq 0 ]; then
            echo "✅ InDesign script installed (CS6 fallback)"
            INSTALLED=$((INSTALLED + 1))
        else
            echo "❌ Failed to install InDesign script"
        fi
    fi
else
    echo "⚠️  InDesign script not found (skipping)"
    SKIPPED=$((SKIPPED + 1))
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "========================================="
echo "Installation Complete: $INSTALLED installed, $SKIPPED skipped"
echo "========================================="
echo ""
echo "Auto-activation works via two mechanisms:"
echo "  • InDesign: startup script runs automatically on document open"
echo "  • Illustrator/Photoshop: FontDock client monitors open documents"
echo "    via AppleScript and auto-activates fonts when new docs appear"
echo ""
echo "Requirements:"
echo "  • FontDock macOS client must be running"
echo "  • Client auto-detects installed Adobe app versions"
echo ""
echo "To uninstall: ./uninstall.sh"
echo "To debug: run DebugFontInfo_*.jsx scripts manually in each app"
