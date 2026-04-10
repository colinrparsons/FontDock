# Building FontDock macOS Client

This guide explains how to build the FontDock macOS client into a standalone application bundle.

## Prerequisites

- Python 3.11 or higher
- PyInstaller (`pip3 install pyinstaller`)
- All dependencies from `requirements.txt`

## Quick Build

Simply run the build script:

```bash
./build.sh
```

This will:
1. Install PyInstaller if needed
2. Clean previous builds
3. Build the application bundle
4. Create `dist/FontDock.app`

## Manual Build

If you prefer to build manually:

```bash
# Install PyInstaller
pip3 install pyinstaller

# Clean previous builds
rm -rf build dist

# Build the app
pyinstaller FontDock.spec
```

## Running the Built App

```bash
# Run directly
open dist/FontDock.app

# Or install to Applications folder
cp -r dist/FontDock.app /Applications/
```

## What's Included

The built application includes:
- All Python dependencies bundled
- Asset files (icons, images)
- Standalone executable (no Python installation required)
- macOS app bundle with proper metadata

## Customization

Edit `FontDock.spec` to customize:
- **Icon**: Set `icon='path/to/icon.icns'` in the BUNDLE section
- **Bundle ID**: Change `bundle_identifier`
- **Version**: Update `CFBundleVersion` and `CFBundleShortVersionString`
- **Additional files**: Add to `datas` list in Analysis section

## Troubleshooting

### Missing modules
Add them to `hiddenimports` in `FontDock.spec`:
```python
hiddenimports=[
    'PyQt5',
    'your_module_here',
],
```

### Missing files
Add them to `datas` in `FontDock.spec`:
```python
datas=[
    ('path/to/file', 'destination/folder'),
],
```

### App won't open
Check console logs:
```bash
open -a Console
# Filter for FontDock
```

## Distribution

To distribute the app:

1. **Code signing** (optional but recommended):
   ```bash
   codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/FontDock.app
   ```

2. **Create DMG** (optional):
   ```bash
   hdiutil create -volname FontDock -srcfolder dist/FontDock.app -ov -format UDZO FontDock.dmg
   ```

3. **Notarization** (for distribution outside App Store):
   Follow Apple's notarization guide

## File Structure

```
macos-client/
├── FontDock.spec       # PyInstaller spec file
├── build.sh            # Build script
├── BUILD.md            # This file
├── main.py             # Entry point
├── gui.py              # Main GUI
├── font_manager.py     # Font management
├── database.py         # Local database
├── assets/             # Icons and images
└── dist/               # Built application (after build)
    └── FontDock.app    # Final app bundle
```
