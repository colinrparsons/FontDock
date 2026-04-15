#!/bin/bash

# FontDock Adobe Scripts Uninstaller
# Removes auto-activation scripts for Illustrator, Photoshop, and InDesign

echo "========================================="
echo "FontDock Adobe Scripts Uninstaller"
echo "========================================="
echo ""

# Adobe startup script directories
ILLUSTRATOR_STARTUP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator"
PHOTOSHOP_STARTUP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop"
INDESIGN_STARTUP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/InDesign"

# Remove Illustrator script
ILLUSTRATOR_SCRIPT="$ILLUSTRATOR_STARTUP_DIR/FontDockAutoActivate_Illustrator.jsx"
if [ -f "$ILLUSTRATOR_SCRIPT" ]; then
    rm "$ILLUSTRATOR_SCRIPT"
    echo "✅ Removed Illustrator script"
else
    echo "⚠️  Illustrator script not found (already removed)"
fi

# Remove Photoshop script
PHOTOSHOP_SCRIPT="$PHOTOSHOP_STARTUP_DIR/FontDockAutoActivate_Photoshop.jsx"
if [ -f "$PHOTOSHOP_SCRIPT" ]; then
    rm "$PHOTOSHOP_SCRIPT"
    echo "✅ Removed Photoshop script"
else
    echo "⚠️  Photoshop script not found (already removed)"
fi

# Remove InDesign script
INDESIGN_SCRIPT="$INDESIGN_STARTUP_DIR/FontDockAutoActivate.jsx"
if [ -f "$INDESIGN_SCRIPT" ]; then
    rm "$INDESIGN_SCRIPT"
    echo "✅ Removed InDesign script"
else
    echo "⚠️  InDesign script not found (already removed)"
fi

echo ""
echo "========================================="
echo "✅ Uninstallation Complete!"
echo "========================================="
echo ""
echo "Please restart Adobe applications for changes to take effect."
