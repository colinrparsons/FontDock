# Illustrator & Photoshop Auto-Activation Plan

**Date:** April 9, 2026  
**Updated:** April 16, 2026  
**Status:** ✅ Complete

## Overview

FontDock auto-activation for Adobe Illustrator and Photoshop, using a different architecture than InDesign due to ExtendScript limitations.

## Architecture

### InDesign (Reference)
- ✅ Has `document.fonts` collection with status (NOT_AVAILABLE, SUBSTITUTED)
- ✅ `afterOpen` event listener works
- ✅ `app.doScript` for HTTP requests
- ✅ Startup script auto-runs from `~/Library/Application Support/Adobe/Startup Scripts CS6/InDesign/`

### Illustrator
- ❌ `app.doScript` undefined (InDesign only)
- ❌ `system.callSystem` undefined
- ❌ `Socket` no constructor
- ❌ `app.notifiers` undefined
- ❌ `app.addEventListener` undefined
- ❌ Reading font info from textFrames with missing fonts throws GFKU error
- ✅ `File`/`Folder` read/write works
- **Solution:** AppleScript app watcher + file-based IPC + parse .ai files on disk

### Photoshop
- ✅ DOM can read font names from text layers
- ❌ `do javascript` AppleScript command fails in PS 2026 (Internal Error 8800)
- **Solution:** AppleScript font scanning directly from Python client

## Implementation

### Illustrator Auto-Activation Flow
1. FontDock client's `AdobeAppWatcher` polls every 5s using AppleScript
2. Detects new `.ai` documents via `file path` property
3. Parses `.ai` file on disk using `strings` + regex (XMP `stFnt:fontName`)
4. Activates fonts by copying to `~/Library/Fonts/`

### Photoshop Auto-Activation Flow
1. FontDock client's `AdobeAppWatcher` polls every 5s using AppleScript
2. Detects new `.psd` documents via `file path` property
3. Scans text layers for font PostScript names via AppleScript:
   - Uses `kind of layer i of document d` to find text layers
   - Uses `font of text object of layer i of document d` for PostScript name
4. Activates fonts by copying to `~/Library/Fonts/`

### Key Technical Details

**Version-Independent App Detection:**
- Scans `/Applications/Adobe Illustrator*`, `/Applications/Adobe Photoshop*` with glob
- Reads `CFBundleDisplayName` from `Info.plist` for correct AppleScript names
- Illustrator: "Adobe Illustrator" (no version)
- Photoshop: "Adobe Photoshop 2026" (with version!)

**Preventing Accidental App Launches:**
- `tell application "X"` in AppleScript launches apps if not running
- All AppleScript guarded with System Events check first:
  ```applescript
  tell application "System Events"
      set isRunning to (name of processes) contains "Adobe Photoshop 2026"
  end tell
  ```

**Photoshop AppleScript Quirks:**
- `repeat with doc in documents` causes Internal Error 9999
- Must use `repeat with d from 1 to count of documents` instead
- `do javascript` fails with error 8800 in PS 2026

## Script Locations

### Unified Install/Uninstall
```
adobe-scripts/install.sh    # Installs all 3 apps
adobe-scripts/uninstall.sh  # Uninstalls all 3 apps
```

### Illustrator
```
~/Library/Application Support/Adobe/Startup Scripts CS6/Illustrator/FontDockAutoActivate_Illustrator.jsx
```

### Photoshop
```
~/Library/Application Support/Adobe/Startup Scripts CS6/Adobe Photoshop/FontDockAutoActivate_Photoshop.jsx
```

### InDesign
```
~/Library/Preferences/Adobe InDesign/Version 21.0/en_GB/Scripts/Startup Scripts/FontDockAutoActivate_InDesign.jsx
```

## File-Based IPC

Request files written to `~/Library/Application Support/FontDock/requests/`:

```json
{
  "file_path": "/path/to/document.ai",
  "app": "illustrator",
  "timestamp": 1776295129519
}
```

Photoshop can also send font names directly:
```json
{
  "file_path": "/path/to/document.psd",
  "app": "photoshop",
  "font_names": ["CostaDisplay-WaveBold", "CostaDisplay-Bold"],
  "timestamp": 1776295129519
}
```

The `RequestFileWatcher` prioritizes `font_names` over file parsing when present.

---

**Status:** Implemented and tested with Illustrator 2026, Photoshop 2026, InDesign 2026
