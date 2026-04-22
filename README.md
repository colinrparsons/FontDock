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

**Version 1.3.0** - Font Sense-style smart matching, unlimited sync, family name normalization!

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

### 🆕 v1.2 Features — Backup/Restore, Bulk Import & UI Consistency

- ✅ **Full Backup & Restore** — ZIP archives containing database + all font files; download, upload, and restore for server migration
- ✅ **Configurable Scheduled Backups** — Daily, weekly (default), monthly, or never; only 2 most recent backups retained
- ✅ **Bulk User Import via CSV** — Upload CSV with first_name, last_name, username, email, password, and all permissions; downloadable template with examples
- ✅ **Granular Permissions UI** — Dedicated permissions page with per-user checkboxes for all 8 permission flags
- ✅ **First Name / Last Name** — User records now include first and last name fields; displayed in Users and Permissions tables
- ✅ **Server Log Viewer** — Web UI to view, download, and clear server logs with auto-refresh
- ✅ **UI Font Size Consistency** — Standardized 13px/12px typography across all pages; consistent input, button, and label sizing
- ✅ **Batch Font Import** — Import fonts from server folder or ZIP file with automatic client creation and duplicate detection

### 🆕 v1.3 Features — Smart Font Matching & Sync Improvements

- ✅ **Font Sense-style Smart Matching** — Multi-field matching engine (PostScript name → Family+Style → Full name → Family → Fuzzy) inspired by Extensis Font Sense, all case-insensitive
- ✅ **Case-Insensitive Matching** — Fonts like `KFC-Regular` now match regardless of case differences between InDesign reports and DB storage (`KFC` vs `Kfc`)
- ✅ **Unlimited Font Sync** — Removed all pagination limits; client syncs entire font library (12,000+ fonts)
- ✅ **Family Name Normalization** — Server normalizes ALL CAPS family names to title case on ingest; admin endpoint to fix existing records
- ✅ **Offline Mode** — Login dialog includes "Work Offline" button; client loads local DB and works without server connection
- ✅ **Constructed PostScript Matching** — InDesign sends `family+style`, client constructs PostScript name (e.g. `KFC` + `Regular` → `KFC-Regular`) for matching

### 🚀 Quick Start

#### Server Setup (Development)
```bash
cd fontdock
pip install -r requirements.txt
./start_server.sh
```
Server runs at `http://localhost:9998`

#### Server Setup (Production / LXC)
```bash
cd fontdock
sudo ./install.sh
```
Installs to `/opt/fontdock` with systemd service and Nginx reverse proxy.

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
