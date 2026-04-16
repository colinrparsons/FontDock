# FontDock Windows Client Setup

This guide covers setting up and running the FontDock client on Windows.

## Prerequisites

- **Python 3.11+** — [Download from python.org](https://www.python.org/downloads/)
  - During install, check **"Add Python to PATH"**
- **Git** (to clone the repo)
- **FontDock server** running and accessible (see [Server Setup](../fontdock/QUICK_START.md))

## Quick Start

### 1. Clone the Repository

```cmd
git clone https://github.com/colinrparsons/FontDock.git
cd FontDock\macos-client
```

> The directory is called `macos-client` but the code is cross-platform.

### 2. Create a Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```cmd
pip install -r requirements.txt
```

Dependencies:
- `PyQt5>=5.15.0` — GUI framework
- `requests>=2.31.0` — HTTP client
- `keyring>=24.0.0` — Secure token storage (uses Windows Credential Manager)

### 4. Run the Client

```cmd
python main.py
```

On first launch:
1. Enter your **Server URL** (e.g. `http://YOUR_SERVER_IP:8000` or `http://localhost:9998`)
2. Click **Test** to verify connectivity
3. Login with your FontDock credentials
4. Sync metadata and start activating fonts

## How It Works on Windows

### Paths

| Item | Windows Path |
|------|-------------|
| App data | `%LOCALAPPDATA%\FontDock\` |
| Font cache | `%LOCALAPPDATA%\FontDock\cache\fonts\` |
| Database | `%LOCALAPPDATA%\FontDock\fontdock.db` |
| Log file | `%LOCALAPPDATA%\FontDock\fontdock.log` |
| Request files | `%LOCALAPPDATA%\FontDock\requests\` |
| User fonts | `%LOCALAPPDATA%\Microsoft\Windows\Fonts\` |

### Font Activation

When you activate a font on Windows:
1. The font file is copied to `%LOCALAPPDATA%\Microsoft\Windows\Fonts\`
2. The font is registered in the Windows registry under `HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`
3. The system is notified via the `AddFontResource` Win32 API and `WM_FONTCHANGE` broadcast

When you deactivate a font:
1. The font file is deleted from the user fonts directory
2. The registry entry is removed
3. The system is notified via `RemoveFontResource`

> **Note:** Per-user font installation requires Windows 10 1803+. No admin rights needed.

### Adobe Integration

On Windows, the FontDock client communicates with Adobe apps via:

- **InDesign**: Startup script writes request files to `%LOCALAPPDATA%\FontDock\requests\` (file-based IPC)
- **Illustrator**: Startup script writes request files; client parses `.ai` files on disk for font names
- **Photoshop**: Client monitors open documents via PowerShell/COM automation and triggers font scanning

The client detects running Adobe apps and open documents using **PowerShell and COM automation** instead of AppleScript.

## Adobe Scripts Installation

### Automatic (Recommended)

Run the Windows installer from the `adobe-scripts` directory:

```cmd
cd adobe-scripts
install.bat
```

This will install the Windows-specific JSX scripts to the correct Adobe startup script directories.

### Manual

If the automatic installer doesn't detect your Adobe apps, copy the scripts manually:

**Illustrator:**
```
Copy FontDockAutoActivate_Illustrator_Win.jsx to:
%APPDATA%\Adobe\Startup Scripts CS6\Illustrator\
```

**Photoshop:**
```
Copy FontDockAutoActivate_Photoshop_Win.jsx to:
%APPDATA%\Adobe\Startup Scripts CS6\Adobe Photoshop\
```

**InDesign:**
```
Copy FontDockAutoActivate_InDesign_Win.jsx to:
%APPDATA%\Adobe\InDesign\Version<XX>\<locale>\Scripts\Startup Scripts\
```
Where `<XX>` is your InDesign version (e.g. `20.0`) and `<locale>` is your locale (e.g. `en_US`).

### Uninstall

```cmd
cd adobe-scripts
uninstall.bat
```

## Troubleshooting

### Python not found

Make sure Python was added to PATH during installation. Verify:
```cmd
python --version
```

If not found, reinstall Python and check "Add Python to PATH", or add it manually:
- Settings → System → About → Advanced system settings → Environment Variables
- Add `C:\Users\<you>\AppData\Local\Programs\Python\Python311` to PATH

### pip install fails

Make sure you activated the virtual environment:
```cmd
venv\Scripts\activate
```

If PyQt5 fails to install, try:
```cmd
pip install PyQt5 --prefer-binary
```

### keyring errors

The `keyring` library uses the Windows Credential Manager by default. If you see errors:
```cmd
pip install keyring.backends.Windows
```

### Fonts not appearing in Adobe apps

1. Check that the font file exists in `%LOCALAPPDATA%\Microsoft\Windows\Fonts\`
2. Check the registry: run `regedit` and navigate to `HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts`
3. Some Adobe apps may need a restart to pick up new fonts
4. Check the log file at `%LOCALAPPDATA%\FontDock\fontdock.log`

### Adobe app detection not working

The client uses PowerShell and COM automation to detect running Adobe apps. Requirements:
- PowerShell 5.1+ (included with Windows 10/11)
- Adobe apps must be running (the client detects them via their COM objects)

### Port 8765 already in use

The local API server uses port 8765. If it's occupied:
```cmd
netstat -ano | findstr :8765
```
To kill the process using that port:
```cmd
taskkill /PID <pid> /F
```

### Can't connect to server

1. Verify the server URL in Settings
2. Test with a browser: navigate to `http://YOUR_SERVER:PORT/health`
3. Check firewall: Windows may block outgoing connections
4. If the server is on your LAN, make sure Windows Firewall allows the connection

## File Structure

```
macos-client/
├── main.py                      # Entry point
├── gui.py                        # Main GUI (cross-platform)
├── config.py                     # Platform-aware configuration
├── font_manager.py               # Font management (cross-platform)
├── local_api.py                  # Adobe integration (cross-platform)
├── api_client.py                 # HTTP client
├── database.py                   # Local SQLite database
├── http_server.py                # Local API server for InDesign
├── fontdock_platform/
│   ├── __init__.py               # Platform selector
│   ├── macos.py                  # macOS-specific code
│   └── windows.py                # Windows-specific code
├── assets/                       # Icons and images
├── requirements.txt              # Python dependencies
├── WINDOWS_SETUP.md              # This file
├── BUILD.md                      # macOS build instructions
└── README.md                     # General README
```
