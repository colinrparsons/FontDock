#!/bin/bash

# Script to create macOS .icns icon from SVG

echo "🎨 Creating FontDock app icon..."

# Check if we have the SVG
if [ ! -f "assets/icon.svg" ]; then
    echo "❌ Error: assets/icon.svg not found"
    exit 1
fi

# Create iconset directory
mkdir -p icon.iconset

# Generate PNG files at different sizes using sips (built-in macOS tool)
# First convert SVG to a large PNG using qlmanage
echo "Converting SVG to PNG..."
qlmanage -t -s 1024 -o . assets/icon.svg 2>/dev/null
mv assets/icon.svg.png icon_1024.png 2>/dev/null || {
    echo "⚠️  qlmanage failed, trying alternative method..."
    # Alternative: use Python with cairosvg if available
    python3 -c "
try:
    from cairosvg import svg2png
    svg2png(url='assets/icon.svg', write_to='icon_1024.png', output_width=1024, output_height=1024)
    print('✓ Converted with cairosvg')
except ImportError:
    print('❌ Please install: pip3 install cairosvg')
    exit(1)
" || {
        echo "❌ Could not convert SVG. Please install cairosvg:"
        echo "   pip3 install cairosvg"
        exit 1
    }
}

# Generate all required sizes using sips
echo "Generating icon sizes..."
sips -z 16 16     icon_1024.png --out icon.iconset/icon_16x16.png > /dev/null
sips -z 32 32     icon_1024.png --out icon.iconset/icon_16x16@2x.png > /dev/null
sips -z 32 32     icon_1024.png --out icon.iconset/icon_32x32.png > /dev/null
sips -z 64 64     icon_1024.png --out icon.iconset/icon_32x32@2x.png > /dev/null
sips -z 128 128   icon_1024.png --out icon.iconset/icon_128x128.png > /dev/null
sips -z 256 256   icon_1024.png --out icon.iconset/icon_128x128@2x.png > /dev/null
sips -z 256 256   icon_1024.png --out icon.iconset/icon_256x256.png > /dev/null
sips -z 512 512   icon_1024.png --out icon.iconset/icon_256x256@2x.png > /dev/null
sips -z 512 512   icon_1024.png --out icon.iconset/icon_512x512.png > /dev/null
cp icon_1024.png icon.iconset/icon_512x512@2x.png

# Create .icns file
echo "Creating .icns file..."
iconutil -c icns icon.iconset -o assets/icon.icns

# Clean up
rm -rf icon.iconset icon_1024.png

if [ -f "assets/icon.icns" ]; then
    echo "✅ Icon created successfully: assets/icon.icns"
else
    echo "❌ Failed to create icon"
    exit 1
fi
