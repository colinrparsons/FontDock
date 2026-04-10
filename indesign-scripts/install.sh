#!/bin/bash

# FontDock InDesign Integration Installer
# This script installs the auto-activation script to InDesign

echo "FontDock InDesign Integration Installer"
echo "========================================"
echo ""

# Detect InDesign version
INDESIGN_PREFS="$HOME/Library/Preferences/Adobe InDesign"

if [ ! -d "$INDESIGN_PREFS" ]; then
    echo "Error: Adobe InDesign preferences folder not found."
    echo "Please make sure InDesign is installed."
    exit 1
fi

# Find the latest version
LATEST_VERSION=$(ls "$INDESIGN_PREFS" | grep "Version" | sort -V | tail -n 1)

if [ -z "$LATEST_VERSION" ]; then
    echo "Error: No InDesign version found."
    exit 1
fi

echo "Found InDesign: $LATEST_VERSION"
echo ""

# Detect locale (en_US or en_GB)
LOCALE=""
if [ -d "$INDESIGN_PREFS/$LATEST_VERSION/en_GB" ]; then
    LOCALE="en_GB"
    echo "Detected locale: en_GB"
elif [ -d "$INDESIGN_PREFS/$LATEST_VERSION/en_US" ]; then
    LOCALE="en_US"
    echo "Detected locale: en_US"
else
    echo "Error: Could not detect InDesign locale (en_US or en_GB)"
    exit 1
fi
echo ""

# Set paths
STARTUP_SCRIPTS="$INDESIGN_PREFS/$LATEST_VERSION/$LOCALE/Scripts/Startup Scripts"
SCRIPTS_PANEL="$INDESIGN_PREFS/$LATEST_VERSION/$LOCALE/Scripts/Scripts Panel"

# Create Startup Scripts folder if it doesn't exist (it usually doesn't by default)
if [ ! -d "$STARTUP_SCRIPTS" ]; then
    echo "Creating Startup Scripts folder..."
    mkdir -p "$STARTUP_SCRIPTS"
    echo "✓ Folder created: $STARTUP_SCRIPTS"
    echo ""
fi

# Copy auto-activation script to Startup Scripts
echo "Installing FontDockAutoActivate.jsx to Startup Scripts..."
cp FontDockAutoActivate.jsx "$STARTUP_SCRIPTS/"

if [ $? -eq 0 ]; then
    echo "✓ Auto-activation script installed successfully!"
else
    echo "✗ Failed to install auto-activation script"
    exit 1
fi

# Copy manual script to Scripts Panel (optional)
echo ""
read -p "Do you want to install the manual CheckMissingFonts script? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Verify Scripts Panel folder exists (it should always exist)
    if [ ! -d "$SCRIPTS_PANEL" ]; then
        echo "Warning: Scripts Panel folder not found. Creating it..."
        mkdir -p "$SCRIPTS_PANEL"
    fi
    
    echo "Installing CheckMissingFonts.jsx to Scripts Panel..."
    cp CheckMissingFonts.jsx "$SCRIPTS_PANEL/"
    
    if [ $? -eq 0 ]; then
        echo "✓ Manual script installed successfully!"
        echo "  Location: $SCRIPTS_PANEL"
    else
        echo "✗ Failed to install manual script"
    fi
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo ""
echo "Next steps:"
echo "1. Restart InDesign (if it's currently running)"
echo "2. Start FontDock client"
echo "3. Open an InDesign document with missing fonts"
echo "4. Fonts will be activated automatically!"
echo ""
echo "Scripts installed to:"
echo "  $STARTUP_SCRIPTS"
echo ""
