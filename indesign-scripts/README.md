# FontDock InDesign Integration

## Overview

This integration allows Adobe InDesign to **automatically activate missing fonts** when you open a document. No manual intervention required!

## Two Scripts Available

### 1. **FontDockAutoActivate.jsx** (Recommended)
- Runs **automatically** when you open any InDesign document
- Detects missing fonts and activates them silently
- Only shows a dialog if fonts can't be found in your library
- **This is the workflow you want!**

### 2. **CheckMissingFonts.jsx** (Manual)
- Run manually from Scripts panel
- Shows detailed information about all fonts
- Useful for troubleshooting

## Installation

### Auto-Activation (Recommended)

1. **Copy the auto-activation script to InDesign Startup Scripts folder:**

   **macOS:**
   ```bash
   cp FontDockAutoActivate.jsx ~/Library/Preferences/Adobe\ InDesign/Version\ XX.0/en_GB/Scripts/Startup\ Scripts/
   ```

   Replace `XX.0` with your InDesign version (e.g., `21.0` for InDesign 2025)
   
   **Note:** Use `en_GB` for UK English or `en_US` for US English (check your InDesign preferences folder)

2. **Restart InDesign**

3. **Make sure FontDock client is running** before opening documents

### Manual Script (Optional)

1. **Copy the manual script to Scripts Panel folder:**

   **macOS:**
   ```bash
   cp CheckMissingFonts.jsx ~/Library/Preferences/Adobe\ InDesign/Version\ XX.0/en_US/Scripts/Scripts\ Panel/
   ```

2. **Restart InDesign**

## Usage

### Auto-Activation Workflow

1. **Start FontDock client** (must be running)
2. **Open InDesign document** with missing fonts
3. **InDesign detects missing fonts** (shows warning)
4. **Script automatically runs** in background
5. **Fonts are activated** from FontDock library
6. **InDesign updates** - fonts are now available!
7. **You can start working** immediately

**That's it!** No dialogs, no clicking, just automatic activation.

### Manual Workflow

1. Open an InDesign document with missing fonts
2. Go to **Window > Utilities > Scripts**
3. Double-click **CheckMissingFonts** in the Scripts panel
4. Review the dialog showing found/not found fonts
5. Click "Activate" to activate matched fonts

## How It Works

### Auto-Activation Flow

```
1. User opens InDesign document with missing fonts
       ↓
2. InDesign shows "Missing Fonts" warning
       ↓
3. FontDockAutoActivate.jsx (afterOpen event listener)
       ↓
4. Script detects missing fonts automatically
       ↓
5. HTTP POST → http://127.0.0.1:8765/open-fonts
   Payload: {"auto_activate": true, "missing_fonts": [...]}
       ↓
6. FontDock Client receives request
       ↓
7. Font Matching (PostScript name → Family name)
       ↓
8. Auto-Activate matched fonts → ~/Library/Fonts/
       ↓
9. Status bar shows: "InDesign: Activated 6/6 fonts"
       ↓
10. InDesign detects fonts are now available
       ↓
11. User can start working immediately!
```

### Manual Flow (CheckMissingFonts.jsx)

```
User runs script manually → Dialog shows results → User clicks Activate
```

## Payload Format

The script sends JSON data to the FontDock client:

```json
{
  "document_name": "MyDocument.indd",
  "document_path": "/Users/username/Documents/MyDocument.indd",
  "missing_fonts": [
    "Gotham-Bold",
    "Gotham-Book"
  ],
  "all_fonts": [
    "Gotham-Bold",
    "Gotham-Book",
    "HelveticaNeueLTStd-Bd"
  ]
}
```

## Troubleshooting

### "Could not connect to FontDock client"

- Make sure FontDock client is running
- Check that the HTTP server is listening on port 8765
- Check FontDock logs: `~/Library/Application Support/FontDock/fontdock.log`

### Fonts not activating

- Verify fonts exist in your FontDock library
- Check font names match (PostScript names are case-sensitive)
- Try syncing FontDock with the server

### Script not appearing in Scripts panel

- Check the script is in the correct folder
- Restart InDesign
- Make sure the file has `.jsx` extension

## Technical Details

- **HTTP Endpoint:** `http://127.0.0.1:8765/open-fonts`
- **Method:** POST
- **Content-Type:** application/json
- **Timeout:** 2 seconds

## Font Matching Logic

FontDock tries to match fonts in this order:

1. **Exact PostScript name match** (e.g., `Gotham-Bold`)
2. **Family name partial match** (e.g., `Gotham` matches `Gotham-Bold`, `Gotham-Book`)

## Future Enhancements

- Automatic triggering on document open
- Collection-based activation (activate all fonts from a client's collection)
- Font substitution suggestions
- Batch processing for multiple documents

## Support

For issues or questions, check the FontDock documentation or logs.
