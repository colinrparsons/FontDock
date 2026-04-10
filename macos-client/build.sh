#!/bin/bash

# FontDock macOS Client Build Script
# This script builds the FontDock client into a standalone .app bundle

echo "🚀 Building FontDock macOS Client..."

# Check if pyinstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "🔨 Building application..."
python3 -m PyInstaller FontDock.spec

# Check if build was successful
if [ -d "dist/FontDock.app" ]; then
    echo "✅ Build successful!"
    echo "📦 Application bundle created at: dist/FontDock.app"
    echo ""
    echo "To run the app:"
    echo "  open dist/FontDock.app"
    echo ""
    echo "To install the app:"
    echo "  cp -r dist/FontDock.app /Applications/"
else
    echo "❌ Build failed!"
    exit 1
fi
