# FontDock macOS Client

A desktop client for FontDock font management system.

## Features

- **Authentication**: Secure login with token storage in macOS Keychain
- **Metadata Sync**: Download and cache font metadata locally
- **Search**: Fast local search across fonts and families
- **Collections**: Browse and activate entire collections
- **Font Activation**: Download and activate fonts on demand
- **Recent Fonts**: Track recently activated fonts
- **InDesign Bridge**: Local API for InDesign integration

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

### Via InDesign Bridge

The client runs a local API server on `http://127.0.0.1:8765` for InDesign integration.

Example request:
```bash
curl -X POST http://127.0.0.1:8765/open-fonts \
  -H "Content-Type: application/json" \
  -d '{"fonts": ["HelveticaNeue-Bold", "CostaDisplay-Regular"]}'
```

## Local Storage

- **Cache**: `~/Library/Application Support/FontDock/cache/fonts/`
- **Database**: `~/Library/Application Support/FontDock/fontdock.db`
- **Credentials**: macOS Keychain (service: FontDock)

## Font Activation Notes

The current implementation uses `atsutil` for font verification. For full activation support, you may need to:

1. Use Font Book scripting
2. Implement CoreText/ATS integration
3. Create a native helper application

The activation mechanism can be extended in `font_manager.py`.

## Troubleshooting

### Login fails
- Check server is running on `http://localhost:9998`
- Verify credentials

### Fonts don't activate
- Check font cache directory exists
- Verify font files are downloaded
- Check macOS font activation permissions

### Sync fails
- Ensure network connection to server
- Check authentication token is valid
- Try logging out and back in
