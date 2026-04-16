# FontDock

**FontDock** is an open-source font server and macOS client designed for creative teams who need a simple, secure way to organise, search, download, and activate licensed fonts across a distributed team.

It is built for real-world agency and studio workflows where users open Adobe InDesign files, discover missing fonts, and need a fast way to activate the correct font set without hunting through shared folders or font managers.

## Core idea

FontDock provides:

- A central **font server**
- A **web admin portal** for uploading and organising fonts
- A **macOS client** for local font activation
- **Adobe app integration** (InDesign, Illustrator, Photoshop) for auto-activating missing fonts
- A **smart matching engine** to identify likely font sets
- An optional **AI assist layer** for natural-language and context-aware suggestions

## Why this exists

Many teams use expensive enterprise font managers or rely on:

- messy shared folders
- manual font hunting
- old naming conventions
- missing fonts in InDesign
- inconsistent project packaging
- remote users over VPN

FontDock aims to solve that with a practical, open-source workflow-first tool.

## Project goals

- Make font discovery and activation easier for creative teams
- Reduce missing-font friction in Adobe workflows
- Provide a self-hosted alternative to enterprise font managers
- Work securely over a private network (e.g. Tailscale)
- Be modular enough for teams to adapt to their own workflow

## Planned architecture

- **Server backend:** FastAPI
- **Database:** SQLite (dev), PostgreSQL (production)
- **Web UI:** FastAPI + Jinja2 initially
- **macOS client:** Python + PyQt5 (or PySide6 in future)
- **InDesign bridge:** ExtendScript / JSX (initially)
- **Networking:** HTTPS and/or Tailscale

## Main components

1. **Font Server**
   - Stores font files and metadata
   - Exposes API endpoints
   - Handles authentication and permissions

2. **Web Portal**
   - Upload and manage fonts
   - Organise by client, collection, family, and tags
   - Search and preview

3. **macOS Client**
   - Authenticates to server
   - Syncs metadata
   - Downloads and caches fonts
   - Activates/deactivates fonts locally

4. **Adobe App Integration**
   - InDesign: ExtendScript startup script with `afterOpen` event
   - Illustrator: AppleScript app watcher + file-based IPC
   - Photoshop: AppleScript font scanning from text layers
   - Auto-detects installed app versions (no hardcoded paths)

5. **Matching Engine**
   - Exact name matching
   - Alias matching
   - Collection ranking
   - Usage history weighting

6. **AI Assist Layer (Optional)**
   - Natural language search
   - Contextual suggestions
   - Ambiguity handling

## Development philosophy

FontDock is designed to be built in phases:

1. Server + metadata storage
2. Web UI + search + downloads
3. macOS client + activation
4. InDesign bridge
5. Smart matching
6. Optional AI features

This keeps the project realistic, testable, and useful at every stage.

## Status

**Version 1.1.0** - Fully functional MVP with trust signals and offline mode!

### ✅ Completed Features

- ✅ FastAPI backend with SQLite database
- ✅ JWT authentication and user management
- ✅ Font upload, metadata extraction, and storage
- ✅ Web admin portal with font preview
- ✅ Client and collection management
- ✅ Cross-platform client (macOS + Windows) with PyQt5 GUI
- ✅ Font activation/deactivation (direct file copy + Windows registry)
- ✅ Local font caching and sync
- ✅ InDesign auto-activation (startup script + `afterOpen` event)
- ✅ Illustrator auto-activation (AppleScript/COM watcher + file parsing)
- ✅ Photoshop auto-activation (AppleScript/COM font scanning)
- ✅ Version-independent Adobe app detection
- ✅ Family grouping with collapsible UI
- ✅ Dark mode support
- ✅ Customizable font preview sizes
- ✅ Status indicators (active/inactive fonts)
- ✅ Duplicate detection (PostScript name + file hash)
- ✅ Many-to-many client-font relationships

### 🆕 v1.1 Features — Trust Signals & Offline Mode

- ✅ **System Status Panel** — Persistent status bar showing connection state (● Connected/Connecting/Disconnected), last sync time (relative), and cached font count
- ✅ **Offline Mode** — Client works without server connection; loads fonts from local DB, activates cached fonts, shows clear "working offline" messaging
- ✅ **Settings Dialog Restructure** — Grouped sections (Server/Sync/Appearance), separate address + port fields, inline test result, last known good URL
- ✅ **Enhanced Test Connection** — Multi-step check (health endpoint + font count), inline color-coded feedback (no more blocking dialogs)
- ✅ **Connection State Persistence** — Last sync time and last known good URL saved to settings, restored on startup
- ✅ **System Fonts Tab** — Browse all system-installed fonts alongside FontDock fonts, with search, family grouping, and collapse-by-default support
- ✅ **Font Comparison Dialog** — Side-by-side or vertical comparison, adjustable point size (6–120pt), live preview text, cyan-themed font name badges
- ✅ **Filter Fixes** — "Activated Only" and "Recently Used" filters now work correctly with collapsed families; collection filter combo refreshes after sync
- ✅ **Cache Count Fix** — Fixed `INSERT OR REPLACE` wiping cached state on sync; cache count now persists correctly across syncs

### 🚀 Quick Start

#### Server Setup
```bash
cd fontdock
pip install -r requirements.txt
python run.py
```
Server runs at `http://localhost:8000`

#### macOS Client Setup
```bash
cd macos-client
pip install -r requirements.txt
python main.py
```

#### Build Standalone App
```bash
cd macos-client
./build.sh
```
Creates `dist/FontDock.app`

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions, ideas, and workflow feedback are welcome.

This project is especially interested in input from:

- artworkers
- designers
- prepress operators
- production studios
- agencies
- font management admins
