#!/bin/bash

# FontDock Adobe Scripts Uninstaller
# Removes auto-activation scripts for Illustrator, Photoshop, and InDesign

echo "========================================="
echo "FontDock Adobe Scripts Uninstaller"
echo "========================================="
echo ""

REMOVED=0

# ============================================================
# Illustrator
# ============================================================
ILLUSTRATOR_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator"
ILLUSTRATOR_SCRIPT="$ILLUSTRATOR_DIR/FontDockAutoActivate_Illustrator.jsx"
if [ -f "$ILLUSTRATOR_SCRIPT" ]; then
    rm "$ILLUSTRATOR_SCRIPT"
    echo "✅ Removed Illustrator script"
    REMOVED=$((REMOVED + 1))
else
    echo "⚠️  Illustrator script not found"
fi

# ============================================================
# Photoshop
# ============================================================
PHOTOSHOP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop"
PHOTOSHOP_SCRIPT="$PHOTOSHOP_DIR/FontDockAutoActivate_Photoshop.jsx"
if [ -f "$PHOTOSHOP_SCRIPT" ]; then
    rm "$PHOTOSHOP_SCRIPT"
    echo "✅ Removed Photoshop script"
    REMOVED=$((REMOVED + 1))
else
    echo "⚠️  Photoshop script not found"
fi

# ============================================================
# InDesign - check both CS6 and versioned preferences paths
# ============================================================
INDESIGN_CS6_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/InDesign"
INDESIGN_PREFS="$HOME/Library/Preferences/Adobe InDesign"

# Remove from CS6 startup scripts
INDESIGN_CS6_SCRIPT="$INDESIGN_CS6_DIR/FontDockAutoActivate.jsx"
if [ -f "$INDESIGN_CS6_SCRIPT" ]; then
    rm "$INDESIGN_CS6_SCRIPT"
    echo "✅ Removed InDesign script (CS6)"
    REMOVED=$((REMOVED + 1))
fi
INDESIGN_CS6_SCRIPT2="$INDESIGN_CS6_DIR/FontDockAutoActivate_InDesign.jsx"
if [ -f "$INDESIGN_CS6_SCRIPT2" ]; then
    rm "$INDESIGN_CS6_SCRIPT2"
    echo "✅ Removed InDesign script (CS6)"
    REMOVED=$((REMOVED + 1))
fi

# Remove from versioned preferences
if [ -d "$INDESIGN_PREFS" ]; then
    while IFS= read -r startup_dir; do
        for script_name in FontDockAutoActivate.jsx FontDockAutoActivate_InDesign.jsx; do
            if [ -f "$startup_dir/$script_name" ]; then
                rm "$startup_dir/$script_name"
                echo "✅ Removed InDesign script (versioned prefs)"
                REMOVED=$((REMOVED + 1))
            fi
        done
    done < <(find "$INDESIGN_PREFS" -path "*/Startup Scripts" -type d 2>/dev/null)
fi

if [ $REMOVED -eq 0 ]; then
    echo "⚠️  No InDesign scripts found"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "========================================="
echo "Uninstallation Complete: $REMOVED scripts removed"
echo "========================================="
echo ""
echo "Please restart Adobe applications for changes to take effect."
