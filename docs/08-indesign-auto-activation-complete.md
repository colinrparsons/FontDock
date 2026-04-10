# InDesign Auto-Activation - Complete ✅

**Date:** April 9, 2026  
**Status:** Working and Production Ready

## Overview

Successfully implemented automatic font activation for Adobe InDesign. When a document with missing fonts is opened, InDesign automatically detects the missing fonts and activates them from FontDock without user intervention.

## How It Works

1. **ExtendScript Startup Script** (`FontDockAutoActivate.jsx`) runs when InDesign starts
2. **Event Listener** attached to `afterOpen` event triggers when documents are opened
3. **Font Detection** scans document for missing/substituted fonts
4. **HTTP Request** sent to local FontDock client (port 8765) with list of missing fonts
5. **Font Activation** FontDock client activates fonts by copying to `~/Library/Fonts/`

## Architecture

```
InDesign Document Open
    ↓
ExtendScript Event Listener
    ↓
Detect Missing Fonts
    ↓
Build JSON: {"fonts": ["Costa Display Wave Regular", ...]}
    ↓
Execute curl via AppleScript (app.doScript)
    ↓
HTTP POST → http://127.0.0.1:8765/open-fonts
    ↓
FontDock Client (local_api.py)
    ↓
Smart Font Name Matching (PostScript conversion)
    ↓
Activate Fonts → ~/Library/Fonts/
```

## Files

### ExtendScript
- **Location:** `~/Library/Preferences/Adobe InDesign/Version 21.0/en_GB/Scripts/Startup Scripts/FontDockAutoActivate.jsx`
- **Purpose:** Auto-activation script that runs on InDesign startup
- **Key Features:**
  - Event listener for document open
  - Font status detection (NOT_AVAILABLE, SUBSTITUTED)
  - Full font name extraction (family + style)
  - JSON payload construction
  - HTTP request via AppleScript bridge

### FontDock Client
- **File:** `macos-client/local_api.py`
- **Port:** 8765
- **Endpoint:** `POST /open-fonts`
- **Payload:** `{"fonts": ["Font Name Style", ...]}`
- **Response:** Array of activation results

## Font Name Matching

### Challenge
InDesign provides font names like: `"Costa Display Wave Regular"`  
Database stores PostScript names like: `"CostaDisplay-WaveRegular"`

### Solution
Smart conversion with multiple split attempts:
1. Try exact match first
2. Convert to PostScript format by trying different family/style split points:
   - `"CostaDisplayWave-Regular"` (split at last word)
   - `"CostaDisplay-WaveRegular"` (split at second-to-last word) ✅
   - Continue until match found

## Testing Results

### ✅ Successfully Activated
- Costa Text Regular
- Costa Text Bold
- Costa Display Regular
- Costa Display Bold
- Costa Display Wave Regular
- Costa Display Wave Bold

### ❌ Not Activated (Not in Database)
- Helvetica Neue LT Std 75 Bold
- Helvetica Neue LT Std 67 Medium Condensed
- Helvetica Neue LT Std 55 Roman
- Helvetica Neue LT Std 45 Light

## Installation

### 1. ExtendScript
Copy `FontDockAutoActivate.jsx` to:
```
~/Library/Preferences/Adobe InDesign/Version 21.0/en_GB/Scripts/Startup Scripts/
```

### 2. FontDock Client
Ensure FontDock client is running:
```bash
cd /Users/colinparsons/Documents/Developement/FontDock/macos-client
python3 main.py
```

### 3. Restart InDesign
Required for startup script to load.

## Usage

1. **Start FontDock Client** (must be running before opening InDesign documents)
2. **Open InDesign Document** with missing fonts
3. **Fonts Auto-Activate** - no user interaction required
4. **Document Opens** with fonts activated

## Technical Details

### ExtendScript Limitations
- No `system.callSystem()` available in InDesign ExtendScript
- **Solution:** Use `app.doScript(appleScript, ScriptLanguage.APPLESCRIPT_LANGUAGE)` to execute shell commands via AppleScript

### Font Status Codes
- `FontStatus.NOT_AVAILABLE` = 1718832705 (font completely missing)
- `FontStatus.SUBSTITUTED` = 1718834037 (font missing, substituted)

### Network Communication
- Uses `curl` via AppleScript for HTTP requests
- Timeout: 2 seconds max, 1 second connect timeout
- Non-blocking execution (doesn't delay document opening)

## Debugging

### Manual Test Script
Run `DebugFontInfo.jsx` from Scripts Panel to see font details:
```
Window > Utilities > Scripts > DebugFontInfo
```
Output written to: `~/Desktop/indesign_font_debug.txt`

### FontDock Client Logs
```bash
tail -f ~/Library/Application\ Support/FontDock/fontdock.log
```

### Check Port
```bash
lsof -i :8765
```

## Future Enhancements

1. **User Notification** - Optional alert when fonts are activated
2. **Activation Report** - Show which fonts were activated vs not found
3. **Batch Download** - Pre-download fonts from server if not in local cache
4. **Font Sync** - Auto-sync with server before activation
5. **Preferences Panel** - Enable/disable auto-activation, configure server URL

## Notes

- Script runs silently (no popups or alerts)
- Errors are caught and suppressed to avoid interrupting InDesign
- Works with both new documents and existing documents
- Compatible with InDesign 2026 (Version 21.0)
- Requires FontDock client to be running on localhost:8765

## Success Criteria ✅

- [x] Auto-detect missing fonts on document open
- [x] Send HTTP request to FontDock client
- [x] Match InDesign font names to database fonts
- [x] Activate fonts automatically
- [x] Non-blocking (doesn't delay document opening)
- [x] Silent operation (no user prompts)
- [x] Error handling (graceful failures)
- [x] Production ready

---

**Status:** Complete and working in production! 🎉
