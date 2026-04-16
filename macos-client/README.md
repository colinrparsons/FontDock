# FontDock Desktop Client

A cross-platform desktop client (Windows + macOS) for the FontDock font management system.

## Features

- **Authentication**: Secure login with token storage in system keychain (macOS Keychain / Windows Credential Manager)
- **Metadata Sync**: Download and cache font metadata locally
- **Search**: Fast local search across fonts and families
- **Collections**: Browse and activate entire collections
- **Font Activation**: Download and activate fonts on demand
- **Recent Fonts**: Track recently activated fonts
- **Adobe App Integration**: Auto-activation for InDesign, Illustrator, and Photoshop
- **System Fonts Tab**: Browse all system-installed fonts alongside FontDock fonts
- **Font Comparison**: Side-by-side or vertical comparison with adjustable point size
- **Offline Mode**: Works without server connection using local DB and cache
- **Status Panel**: Persistent connection indicator, last sync time, and cache count

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the client:
```bash
python main.py
```

Or make it executable:
```bash
chmod +x main.py
./main.py
```

## First Time Setup

1. Launch the application
2. Enter your FontDock credentials
3. Click "Sync" to download metadata
4. Search for fonts or browse collections

## Font Activation

### Via GUI
- Search for a font
- Double-click or click "Activate Selected"
- Font will be downloaded and activated

### Via Collections
- Go to Collections tab
- Select a collection
- Click "Activate All Fonts"

### Via Font Comparison
- Select 2–6 fonts in the Fonts tab
- Click "Compare" to open the comparison dialog
- Toggle vertical/horizontal layout, adjust point size, edit preview text live

### Via Adobe App Auto-Activation

The client automatically detects when Adobe documents are opened and activates missing fonts:

- **InDesign**: Startup script with `afterOpen` event sends missing font info via HTTP
- **Illustrator**: App watcher detects new `.ai` files, parses fonts from disk
- **Photoshop**: App watcher detects new `.psd` files, scans text layers for font names

All three apps are version-independent — the client auto-detects installed versions.

Install scripts:
```bash
cd adobe-scripts
./install.sh    # Install all 3 apps (macOS)
./uninstall.sh  # Uninstall all 3 apps (macOS)
```

The client also runs a local API server on `http://127.0.0.1:8765` for manual requests:
```bash
curl -X POST http://127.0.0.1:8765/open-fonts \
  -H "Content-Type: application/json" \
  -d '{"fonts": ["HelveticaNeue-Bold", "CostaDisplay-Regular"]}'
```

## Tabs

| Tab | Description |
|---|---|
| **Fonts** | FontDock-managed fonts with search, filters (Activated Only, Recently Used, Collection), preview presets, and state badges (Local/Cached/Remote) |
| **Collections** | Browse and activate font collections |
| **Clients** | View client-specific font assignments |
| **Recent** | Recently activated fonts |
| **System Fonts** | All system-installed fonts (not FontDock-managed), with search and family grouping |

## Status Bar

The persistent status bar shows:
- **Connection state**: ● Connected (green) / ● Connecting... (orange) / ● Disconnected (red)
- **Last sync**: Relative time (e.g., "2 mins ago"), auto-refreshed every 60s
- **Cache count**: Number of fonts cached locally

## Offline Mode

The client works without a server connection:
- Fonts already in the local cache can be activated/deactivated
- Local DB is used for browsing and search
- Clear "working offline" messaging in the status bar
- Sync will retry when the server becomes available

## Local Storage

### Windows
- **Cache**: `%LOCALAPPDATA%\FontDock\cache\fonts\`
- **Database**: `%LOCALAPPDATA%\FontDock\fontdock.db`
- **Settings**: `%LOCALAPPDATA%\FontDock\settings.json`
- **Credentials**: Windows Credential Manager (service: FontDock)

### macOS
- **Cache**: `~/Library/Application Support/FontDock/cache/fonts/`
- **Database**: `~/Library/Application Support/FontDock/fontdock.db`
- **Settings**: `~/Library/Application Support/FontDock/settings.json`
- **Credentials**: macOS Keychain (service: FontDock)

## Font States

| State | Location | Meaning |
|---|---|---|
| **Remote** | Server only | Font exists on server, not downloaded |
| **Cached** | Local cache dir | Font downloaded to cache, not installed |
| **Local** | User fonts dir | Font activated and available to apps |

## Settings

The settings dialog is organized into grouped sections:
- **Server**: Address + Port (separate fields), Test Connection with inline result, last known good URL
- **Sync**: Collapse Families by Default toggle
- **Appearance**: Font Preview Size, App Font Size, Dark Mode

## Font Activation Notes

The current implementation uses `atsutil` for font verification. For full activation support, you may need to:

1. Use Font Book scripting
2. Implement CoreText/ATS integration
3. Create a native helper application

The activation mechanism can be extended in `font_manager.py`.

## Troubleshooting

### Login fails
- Check server is running and reachable
- Verify credentials
- Use Test Connection in settings to verify connectivity

### Fonts don't activate
- Check font cache directory exists
- Verify font files are downloaded (Cached state)
- On Windows, check registry entries under `HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`

### Sync fails / Offline
- Client works offline using local DB and cache
- Check connection state indicator in status bar
- Try Test Connection in settings
- Ensure server address and port are correct

### Cache count shows 0
- Run a sync to populate the database
- Cache state is preserved across syncs (fixed in v1.1)
