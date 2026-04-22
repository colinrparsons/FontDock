# InDesign Auto-Activation - Complete ✅

**Date:** April 22, 2026  
**Status:** Working and Production Ready

## Overview

Successfully implemented automatic font activation for Adobe InDesign. When a document with missing fonts is opened, InDesign automatically detects the missing fonts and activates them from FontDock without user intervention.

## How It Works

1. **ExtendScript Startup Script** (`FontDockAutoActivate_InDesign.jsx`) runs when InDesign starts
2. **Event Listener** attached to `afterOpen` event triggers when documents are opened
3. **Font Detection** scans document for missing/substituted fonts using `font.fontFamily` and `font.fontStyleName`
4. **HTTP Request** sent to local FontDock client (port 8765) with `{"fonts": [{family, style}, ...]}` payload
5. **Smart Font Matching** FontDock client uses `database.smart_match_font()` with 5-strategy matching
6. **Font Activation** matched fonts are activated by copying to `~/Library/Fonts/`

## Architecture

```
InDesign Document Open
    ↓
ExtendScript afterOpen Event Listener
    ↓
Detect Missing Fonts (font.fontFamily + font.fontStyleName)
    ↓
Build JSON: {"fonts": [{"family": "KFC", "style": "Regular"}, ...]}
    ↓
Execute curl via AppleScript (app.doScript)
    ↓
HTTP POST → http://127.0.0.1:8765/open-fonts
    ↓
FontDock Client (local_api.py)
    ↓
Smart Font Matching (database.smart_match_font)
  Strategy 1: PostScript name exact match (case-insensitive)
  Strategy 2: Family+Style match + constructed PS name (KFC+Regular → KFC-Regular)
  Strategy 3: Full name match
  Strategy 4: Family name match (all members)
  Strategy 5: Fuzzy search fallback
    ↓
Activate Fonts → ~/Library/Fonts/
```

## Files

### ExtendScript
- **Location:** `~/Library/Application Support/Adobe/Startup Scripts CS6/InDesign/FontDockAutoActivate_InDesign.jsx`
- **Purpose:** Auto-activation script that runs on InDesign startup
- **Key Features:**
  - Event listener for document open
  - Font status detection (NOT_AVAILABLE, SUBSTITUTED)
  - Family + style extraction (not just full name)
  - JSON payload construction with `{family, style}` objects
  - HTTP request via AppleScript bridge

### FontDock Client
- **File:** `macos-client/local_api.py`
- **Port:** 8765
- **Endpoint:** `POST /open-fonts`
- **Payload:** `{"fonts": [{"family": "KFC", "style": "Regular"}, ...]}`
- **Response:** Array of activation results

### Smart Matching
- **File:** `macos-client/database.py` — `smart_match_font()` method
- **5 strategies** tried in priority order, all case-insensitive
- See [Font Matching Engine](08-font-matching-engine.md) for full details

## Font Name Matching

### Challenge
InDesign provides font names as family+style: `family="KFC", style="Regular"`  
Database stores PostScript names like: `KFC-Regular` with family_name `Kfc` (title-cased)

### Solution: Smart Multi-Field Matching
1. **PostScript name** exact match (case-insensitive)
2. **Family + Style** match + **constructed PostScript** name (`KFC` + `Regular` → `KFC-Regular`)
3. **Full name** match (`KFC Regular`)
4. **Family name** match (case-insensitive, returns all members)
5. **Fuzzy search** fallback (LIKE across all fields)

### Case-Insensitive Matching
All matching uses `COLLATE NOCASE` in SQLite. This is critical because:
- InDesign reports `font.fontFamily` using the font's internal name (e.g., `KFC`)
- FontDock normalizes family names to title case on ingest (e.g., `Kfc`)
- Without case-insensitive matching, these would never match

## Testing Results

### ✅ Successfully Activated
- Costa Text Regular
- Costa Text Bold
- Costa Display Regular
- Costa Display Bold
- Costa Display Wave Regular
- Costa Display Wave Bold
- KFC-Regular (previously failed due to case mismatch — fixed in v1.3)

### ❌ Not Activated (Not in Database)
- Helvetica Neue LT Std 75 Bold
- Helvetica Neue LT Std 67 Medium Condensed
- Helvetica Neue LT Std 55 Roman
- Helvetica Neue LT Std 45 Light

## Installation

### 1. ExtendScript
Run the install script:
```bash
cd adobe-scripts
./install.sh
```
Or manually copy `FontDockAutoActivate_InDesign.jsx` to:
```
~/Library/Application Support/Adobe/Startup Scripts CS6/InDesign/
```

### 2. FontDock Client
Ensure FontDock client is running:
```bash
cd macos-client
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
Run `CheckMissingFonts_InDesign.jsx` from Scripts Panel to see font details:
```
Window > Utilities > Scripts > CheckMissingFonts
```

### FontDock Client Logs
```bash
tail -f ~/Library/Application\ Support/FontDock/fontdock.log
```

### Check Port
```bash
lsof -i :8765
```

### Test Smart Matching
```bash
sqlite3 ~/Library/Application\ Support/FontDock/fontdock.db
> SELECT id, postscript_name, family_name, style_name FROM fonts WHERE family_name COLLATE NOCASE = 'KFC';
```

## Future Enhancements

1. **Font Fingerprinting** — Hash-based exact version matching (like Extensis Font Sense)
2. **Alias Lookup** — Table for legacy name variants
3. **Collection Scoring** — Rank collections by how many missing fonts they contain
4. **Batch Download** — Pre-download fonts from server if not in local cache
5. **Font Sync** — Auto-sync with server before activation

## Notes

- Script runs silently (no popups or alerts)
- Errors are caught and suppressed to avoid interrupting InDesign
- Works with both new documents and existing documents
- Compatible with InDesign 2026 (Version 21.0)
- Requires FontDock client to be running on localhost:8765
- Version-independent startup script path (`Startup Scripts CS6/`)

## Success Criteria ✅

- [x] Auto-detect missing fonts on document open
- [x] Send HTTP request to FontDock client
- [x] Match InDesign font names to database fonts
- [x] Case-insensitive matching (KFC vs Kfc)
- [x] Constructed PostScript name matching (family+style → PS name)
- [x] Activate fonts automatically
- [x] Non-blocking (doesn't delay document opening)
- [x] Silent operation (no user prompts)
- [x] Error handling (graceful failures)
- [x] Production ready

---

**Status:** Complete and working in production! 🎉
