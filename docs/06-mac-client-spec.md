# macOS Client Specification

## Purpose

The macOS client is responsible for turning the server into a practical daily tool.

It should:

- authenticate to the server
- sync metadata
- search collections and fonts
- download fonts on demand
- cache fonts locally
- activate/deactivate fonts locally
- receive InDesign bridge requests

## Recommended stack

- **Python 3.11+**
- **PyQt5** (good for familiarity and existing plans)
- or **PySide6** later if preferred
- `requests` or `httpx`
- `keyring` for secure credential/token storage
- local SQLite for cache metadata

## Client modes

### 1. GUI app

User-facing app with:

- login screen
- search bar
- collections browser
- activate buttons
- recent items
- status tray/menu bar later

### 2. Local background service

A small local HTTP listener or file watcher used for:

- receiving requests from InDesign
- processing activation commands

This can be part of the GUI app initially.

## Core features

### Authentication

- login to server
- store token securely in macOS Keychain (via Python keyring)
- refresh or re-login when needed
- **Offline mode**: "Work Offline" button on login dialog loads local DB without server connection

### Metadata sync

- fetch clients
- fetch collections
- fetch font metadata
- sync aliases
- cache locally for fast searching

### Download and cache

Store fonts under a controlled local directory, for example:

`~/Library/Application Support/FontDock/cache/fonts/`

Each font can be stored by:

- font ID
- file hash
- original filename metadata

### Activation logic

The client should:

- ensure file exists locally
- download if missing
- activate font using macOS-safe approach
- track what it activated
- optionally deactivate when done

## Important note about activation

macOS font activation can be tricky.

Potential approaches:

- use **Font Book / CoreText / ATS** via subprocess or native bridge later
- use AppleScript in limited cases
- use `fonttools` only for metadata, not activation
- consider a small native helper later if Python-only is insufficient

The exact activation mechanism should be prototyped early.

## UI screens

### Login

- server URL
- username
- password
- sign in

### Main window

- search bar
- tabs: Clients / Collections / Fonts / Recent
- activate button
- download status

### Collection detail

- list included fonts
- activate all
- deactivate all (if session-managed)
- show last used

### Notifications

- activation success
- activation failed
- missing font not found
- ambiguous match found

## Local API suggestion

Expose a localhost endpoint:

- `POST http://127.0.0.1:8765/open-fonts`

This allows InDesign JSX to send a JSON request directly.

Alternative:

- watch a JSON file in Application Support folder

## Local data

Keep a local SQLite DB for:

- synced font metadata
- synced collections
- aliases
- recent activations
- local cache status
