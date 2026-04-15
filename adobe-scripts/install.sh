#!/bin/bash

# FontDock Adobe Scripts Installer
# Installs auto-activation scripts for Illustrator, Photoshop, and InDesign

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "FontDock Adobe Scripts Installer"
echo "========================================="
echo ""

# Check if scripts exist
if [ ! -f "$SCRIPT_DIR/FontDockAutoActivate_Illustrator.jsx" ]; then
    echo "❌ Illustrator script not found at $SCRIPT_DIR/FontDockAutoActivate_Illustrator.jsx"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/FontDockAutoActivate_Photoshop.jsx" ]; then
    echo "❌ Photoshop script not found at $SCRIPT_DIR/FontDockAutoActivate_Photoshop.jsx"
    exit 1
fi

# Adobe startup script directories
ILLUSTRATOR_STARTUP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator"
PHOTOSHOP_STARTUP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop"
INDESIGN_STARTUP_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/InDesign"

# User script directories (alternative locations)
ILLUSTRATOR_USER_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator"
PHOTOSHOP_USER_DIR="$HOME/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop"

# Create directories if they don't exist
mkdir -p "$ILLUSTRATOR_STARTUP_DIR"
mkdir -p "$PHOTOSHOP_STARTUP_DIR"
mkdir -p "$INDESIGN_STARTUP_DIR"

# Install Illustrator script
echo "📌 Installing Illustrator auto-activate script..."
cp "$SCRIPT_DIR/FontDockAutoActivate_Illustrator.jsx" "$ILLUSTRATOR_STARTUP_DIR/"
if [ $? -eq 0 ]; then
    echo "   ✅ Installed to: $ILLUSTRATOR_STARTUP_DIR/"
else
    echo "   ❌ Failed to install Illustrator script"
fi

# Install Photoshop script
echo "📌 Installing Photoshop auto-activate script..."
cp "$SCRIPT_DIR/FontDockAutoActivate_Photoshop.jsx" "$PHOTOSHOP_STARTUP_DIR/"
if [ $? -eq 0 ]; then
    echo "   ✅ Installed to: $PHOTOSHOP_STARTUP_DIR/"
else
    echo "   ❌ Failed to install Photoshop script"
fi

# Install InDesign script (if it exists in the indesign-scripts directory)
INDESIGN_SCRIPT="$SCRIPT_DIR/../indesign-scripts/FontDockAutoActivate.jsx"
if [ -f "$INDESIGN_SCRIPT" ]; then
    echo "📌 Installing InDesign auto-activate script..."
    cp "$INDESIGN_SCRIPT" "$INDESIGN_STARTUP_DIR/"
    if [ $? -eq 0 ]; then
        echo "   ✅ Installed to: $INDESIGN_STARTUP_DIR/"
    else
        echo "   ❌ Failed to install InDesign script"
    fi
else
    echo "⚠️  InDesign script not found at $INDESIGN_SCRIPT (skipping)"
fi

# Install debug scripts to user scripts directory
echo ""
echo "📌 Installing debug scripts (optional - for troubleshooting)..."

# Illustrator debug script
if [ -f "$SCRIPT_DIR/DebugFontInfo_Illustrator.jsx" ]; then
    echo "   ✅ DebugFontInfo_Illustrator.jsx available in $SCRIPT_DIR/"
fi

# Photoshop debug script
if [ -f "$SCRIPT_DIR/DebugFontInfo_Photoshop.jsx" ]; then
    echo "   ✅ DebugFontInfo_Photoshop.jsx available in $SCRIPT_DIR/"
fi

echo ""
echo "========================================="
echo "✅ Installation Complete!"
echo "========================================="
echo ""
echo "The auto-activation scripts will run automatically when you:"
echo "  • Open a document in Illustrator"
echo "  • Open a document in Photoshop"
echo "  • Open a document in InDesign"
echo ""
echo "Requirements:"
echo "  • FontDock macOS client must be running"
echo "  • FontDock client local API must be on port 8765"
echo ""
echo "To uninstall, run: ./uninstall.sh"
echo "To debug font info, run the DebugFontInfo_*.jsx scripts manually"
