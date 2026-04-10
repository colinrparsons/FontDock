# FontDock Project Blueprint

Below are the full contents for the markdown files for the open-source project.

---

# README.md

```md
# FontDock

**FontDock** is an open-source font server and macOS client designed for creative teams who need a simple, secure way to organise, search, download, and activate licensed fonts across a distributed team.

It is built for real-world agency and studio workflows where users open Adobe InDesign files, discover missing fonts, and need a fast way to activate the correct font set without hunting through shared folders or font managers.

## Core idea

FontDock provides:

- A central **font server**
- A **web admin portal** for uploading and organising fonts
- A **macOS client** for local font activation
- An **InDesign integration bridge** for detecting missing fonts
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

4. **InDesign Integration**
   - Reads current document context
   - Detects missing fonts
   - Sends requests to local client

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

This project is currently in the design and build-planning stage.

## License

Recommended: MIT or Apache-2.0

## Contributing

Contributions, ideas, and workflow feedback are welcome.

This project is especially interested in input from:

- artworkers
- designers
- prepress operators
- production studios
- agencies
- font management admins

```

---

# docs/01-project-overview.md

```md
# Project Overview

## What FontDock is

FontDock is a self-hosted font server and client system built for creative production teams.

The main purpose is to make it easier to:

- organise licensed fonts centrally
- assign them to clients or projects
- let users search and retrieve them quickly
- activate them locally on macOS
- reduce missing-font issues when opening Adobe InDesign files

## The workflow problem it solves

In many teams, fonts are spread across:

- shared drives
- old job folders
- packaged projects
- manually maintained font folders
- expensive proprietary font managers

This leads to problems such as:

- users cannot find the correct font quickly
- font names are inconsistent
- old projects open with missing fonts
- remote users over VPN have slow access to font shares
- users activate too many fonts or wrong versions
- no central source of truth exists

## The product vision

FontDock should eventually support a workflow where:

1. A user opens an InDesign document
2. Missing fonts are detected automatically
3. The local client receives the missing font names and document context
4. The client checks the central server
5. Exact or likely matches are found
6. The user is prompted to activate the correct set
7. Fonts are activated locally
8. InDesign refreshes with minimal manual effort

## Design principles

- Build the server first
- Use a clean API contract
- Keep client logic separate from server logic
- Prefer deterministic matching first
- Use AI only where it adds value
- Make every phase useful even before the next one exists
- Keep the project understandable for future contributors

## What v1 should be

Version 1 should **not** try to do everything.

The best first useful version is:

- Upload fonts
- Extract metadata
- Store fonts on server
- Organise by client and collection
- Search fonts in a web UI
- Download fonts manually

This alone already creates value.

## What makes this open-source worthy

This is not just a toy project.

It solves a real production problem that many studios and agencies have.

A clean open-source version could be useful to:

- small agencies
- in-house design teams
- publishers
- prepress teams
- freelancers managing licensed client font sets

```

---

# docs/02-system-architecture.md

```md
# System Architecture

## High-level components

FontDock consists of five major components:

1. **Server Backend**
2. **Database**
3. **Web Admin/User Interface**
4. **macOS Desktop Client**
5. **InDesign Integration Bridge**

An optional sixth component can be added later:

6. **AI Assist Layer**

## Architecture diagram (conceptual)

User / Admin Browser
    -> Web UI (FastAPI + Jinja2)
    -> FastAPI API
    -> Database + Font Storage

macOS Client
    -> Authenticates to API
    -> Syncs metadata
    -> Downloads/caches fonts
    -> Activates fonts locally

InDesign JSX Script
    -> Sends missing font request to local client
    -> Local client resolves via API

Optional AI Layer
    -> Assists query interpretation and ranking

## Server responsibilities

The server is the source of truth for:

- font files
- font metadata
- users
- permissions
- clients
- collections
- aliases
- audit logs
- download tokens / access control

The server should **not** be responsible for local font activation.

## Client responsibilities

The macOS client is responsible for:

- login/session management
- local cache
- downloading fonts
- activating fonts locally
- deactivating fonts
- receiving InDesign bridge requests
- running matching logic locally or via API

## InDesign bridge responsibilities

The InDesign integration should:

- read current document context
- identify missing fonts
- extract document path and filename
- send a structured request to the local client

It should remain lightweight.

## Matching responsibilities

Matching can be split between server and client.

Recommended split:

- Server: metadata, aliases, search endpoints, candidate generation
- Client: local context, user history, final activation decisions

## AI responsibilities (optional)

AI should only assist with:

- interpreting vague user intent
- ranking likely collections
- resolving ambiguous searches
- suggesting likely project sets

AI should not blindly activate fonts without a safe deterministic fallback.

## Deployment modes

### Local development

- FastAPI app on localhost
- SQLite database
- local font storage directory

### Small team production

- FastAPI behind reverse proxy
- PostgreSQL
- local or mounted storage
- HTTPS

### Agency / distributed team production

- Ubuntu server or VM
- PostgreSQL
- persistent storage volume
- reverse proxy (Nginx / Caddy)
- Tailscale access and/or internal HTTPS
- optional office VPN coexistence

```

---

# docs/03-server-backend-spec.md

```md
# Server Backend Specification

## Primary goals

The backend must provide:

- secure storage of font files
- metadata extraction and indexing
- user authentication
- permissions
- search and filtering
- download endpoints
- collection management
- audit logging

## Suggested stack

- **Python 3.11+**
- **FastAPI**
- **SQLAlchemy** or **SQLModel**
- **Alembic**
- **Pydantic**
- **SQLite** for local dev
- **PostgreSQL** for production

## Suggested project structure

```text
fontdock/
  app/
    main.py
    config.py
    db.py
    dependencies.py
    models/
    schemas/
    services/
    routers/
    templates/
    static/
  storage/
  tests/
  scripts/
```

## Core modules

### 1. Authentication

Should support:

- local username/password
- session-based auth for web UI
- token or API key for client auth
- later: optional SSO / LDAP / OIDC

### 2. Font ingestion

Upload endpoint should:

- accept `.otf`, `.ttf`, optionally `.ttc`
- validate file type
- compute SHA256 hash
- extract metadata
- store file safely
- avoid duplicate storage when possible
- create DB records

### 3. Search API

Should support searching by:

- family name
- style name
- PostScript name
- client
- collection
- tags
- aliases
- status (active/archived)

### 4. Download API

Should:

- verify user permissions
- log the event
- return file stream or signed temporary access

### 5. Matching API

Should return candidate matches for:

- exact font name
- alias lookup
- family/style combination
- collection candidates by keywords

### 6. Admin APIs

- create/edit clients
- create/edit collections
- assign fonts to collections
- manage aliases
- manage tags
- manage users
- manage permissions

## Recommended endpoints (example)

### Auth

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### Fonts

- `GET /api/fonts`
- `POST /api/fonts/upload`
- `GET /api/fonts/{font_id}`
- `GET /api/fonts/{font_id}/download`
- `POST /api/fonts/{font_id}/aliases`

### Families

- `GET /api/families`
- `GET /api/families/{family_id}`

### Clients

- `GET /api/clients`
- `POST /api/clients`
- `GET /api/clients/{client_id}`

### Collections

- `GET /api/collections`
- `POST /api/collections`
- `GET /api/collections/{collection_id}`
- `POST /api/collections/{collection_id}/fonts`

### Matching

- `POST /api/match/missing-fonts`
- `POST /api/match/search`

### Audit

- `GET /api/audit/events`

## Services layer recommendation

Keep business logic out of route handlers.

Recommended service modules:

- `font_ingest_service.py`
- `font_metadata_service.py`
- `font_search_service.py`
- `font_match_service.py`
- `download_service.py`
- `auth_service.py`
- `audit_service.py`

```

---

# docs/04-database-schema.md

```md
# Database Schema

## Design goals

The schema should support:

- individual font files
- font families and styles
- multiple clients
- collections per client or global
- aliases for messy legacy names
- user permissions
- usage history
- audit logging
- future AI-friendly metadata

## Core tables

### users

Fields:

- id
- username
- email
- password_hash
- is_admin
- is_active
- created_at
- updated_at

### roles (optional later)

Fields:

- id
- name
- description

### clients

Fields:

- id
- name
- code
- description
- is_active
- created_at
- updated_at

### collections

Fields:

- id
- name
- slug
- description
- client_id (nullable for global collections)
- is_active
- created_at
- updated_at

Examples:

- Tesco Summer POS 2026
- Nike Brand Core
- Global Sans Serif Essentials

### tags

Fields:

- id
- name
- slug

### font_families

Fields:

- id
- name
- normalized_name
- foundry
- notes
- created_at
- updated_at

### fonts

Represents a specific font file/style.

Fields:

- id
- family_id
- filename_original
- filename_storage
- storage_path
- file_hash_sha256
- file_size_bytes
- extension
- postscript_name
- full_name
- style_name
- weight_class
- width_class
- italic_angle
- version_string
- is_variable_font
- is_active
- created_at
- updated_at

### font_aliases

Used to map weird names or legacy naming.

Fields:

- id
- font_id
- alias_name
- alias_normalized
- source_type
- created_at

Examples:

- HelveticaNeueLTStd-Bd
- Gotham-Bold
- Knockout-HTF48-Featherweight

### collection_fonts

Join table:

- id
- collection_id
- font_id
- added_at

### collection_tags

Join table:

- id
- collection_id
- tag_id

### user_client_permissions

- id
- user_id
- client_id
- can_view
- can_download
- can_activate

### user_collection_permissions (optional later)

- id
- user_id
- collection_id
- can_view
- can_download
- can_activate

### font_usage_events

Tracks usage history.

Fields:

- id
- user_id
- font_id
- collection_id (nullable)
- source
- document_name (nullable)
- document_path_hint (nullable)
- event_type
- created_at

Event examples:

- download
- activate
- deactivate
- indesign_missing_font_match

### audit_events

Broad audit trail.

Fields:

- id
- user_id (nullable)
- event_type
- entity_type
- entity_id
- payload_json
- created_at

## AI-friendly additions

To support future AI or smarter matching, it helps to store:

- normalized names
- aliases
- usage history
- document filename hints (not full sensitive paths in production if privacy matters)
- client codes
- collection keywords
- tags

```

---

# docs/05-web-ui-spec.md

```md
# Web UI Specification

## Purpose

The web UI is the first usable product.

It should allow admins and normal users to:

- browse fonts
- search fonts
- manage collections
- upload fonts
- view families
- download fonts

## Recommended approach

Start with:

- **FastAPI + Jinja2 templates**
- minimal JavaScript
- server-rendered forms and tables

This is faster and simpler for an MVP.

## Main pages

### 1. Login page

- username/email
- password
- remember me (optional)

### 2. Dashboard

Show:

- total fonts
- total families
- total collections
- recent uploads
- recent activations/downloads
- quick links

### 3. Fonts page

List with:

- family
- style
- PostScript name
- client/collections
- tags
- download button
- detail link

Filters:

- client
- collection
- tag
- active status

### 4. Font detail page

Show:

- file info
- family
- style
- PostScript name
- aliases
- collections
- tags
- usage history (admin)

### 5. Families page

Group fonts by family.

Show:

- family name
- style count
- foundry
- linked collections

### 6. Clients page

Show:

- all clients
- collection counts
- font counts

### 7. Client detail page

Show:

- collections for that client
- core brand sets
- seasonal/project sets

### 8. Collections page

This is a key page.

Show:

- collection name
- client
- description
- included fonts
- tags
- download all / export manifest (later)

### 9. Upload page (admin)

Features:

- multi-file upload
- drag and drop later
- validation messages
- duplicate detection
- preview metadata before save (later)

### 10. User management page (admin)

- create user
- edit user
- assign permissions

## Search behaviour

Search should match:

- family names
- style names
- PostScript names
- aliases
- client names
- collection names
- tags

## Nice future additions

- font preview text rendering (server-side image or browser CSS preview if practical)
- recently used collections
- favourite collections
- collection templates
- CSV import/export

```

---

# docs/06-mac-client-spec.md

```md
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

```

---

# docs/07-indesign-integration-spec.md

```md
# InDesign Integration Specification

## Goal

Allow Adobe InDesign to trigger the local FontDock client when a document has missing fonts.

## Recommended v1 approach

Use **ExtendScript / JSX**.

This is the most practical first implementation.

## Why not parse INDD directly first?

INDD files are not the best first target for external parsing.

InDesign already knows:

- which fonts are used
- which fonts are missing
- document path
- document name

So the cleanest design is to let InDesign report that context.

## Responsibilities of the JSX script

The script should:

1. Detect the active document
2. Read document name and path
3. Inspect fonts used in the document
4. Identify missing fonts
5. Build a JSON payload
6. Send it to the local FontDock client (or write to a watched file)

## Suggested payload shape

```json
{
  "document_name": "Tesco_Summer_POS_2026.indd",
  "document_path": "/Volumes/Jobs/Tesco/Summer/POS/Tesco_Summer_POS_2026.indd",
  "missing_fonts": [
    "Gotham-Bold",
    "Gotham-Book",
    "Knockout-HTF48-Featherweight"
  ],
  "all_fonts": [
    "Gotham-Bold",
    "Gotham-Book",
    "Knockout-HTF48-Featherweight",
    "HelveticaNeueLTStd-Bd"
  ]
}
```

## Delivery methods to local client

### Option A (preferred)

POST JSON to local HTTP endpoint:

- `http://127.0.0.1:8765/open-fonts`

### Option B

Write JSON to a watched file location:

- `~/Library/Application Support/FontDock/requests/pending_request.json`

## Trigger modes

### Manual menu command (best for v1)

- User opens document
- User runs “Check Missing Fonts” script
- Script sends request to client

### Semi-automatic later

- Script can be run from startup or custom workflow
- Potential event-based hooks if practical

## Expected client response flow

1. Receive request
2. Run exact matching
3. Run alias matching
4. Rank likely collections
5. Prompt user if ambiguous
6. Activate selected fonts
7. Show result

## Important practical note

The InDesign integration should be treated as a bridge only.

Do not put heavy matching logic inside the JSX script.

Keep it simple and stable.

```

---

# docs/08-font-matching-engine.md

```md
# Font Matching Engine

## Purpose

The matching engine is the core intelligence of FontDock.

It should resolve missing fonts safely and predictably.

## Matching philosophy

Always prefer:

1. deterministic exact matches
2. alias matches
3. ranked collection suggestions
4. AI only when helpful

## Matching pipeline

### Step 1: Exact PostScript match

Try to match the missing font name against:

- `postscript_name`

This should be the highest-confidence path.

### Step 2: Exact full name match

Try to match against:

- `full_name`

### Step 3: Family + style normalization

Split and normalize names into likely:

- family
- style

Examples:

- Gotham-Bold -> family Gotham, style Bold
- HelveticaNeueLTStd-Bd -> family Helvetica Neue LT Std, style Bold

### Step 4: Alias lookup

Use `font_aliases`.

This is essential for real-world messy legacy naming.

### Step 5: Collection candidate scoring

If one or more fonts are found, score collections by:

- how many missing fonts they contain
- client match from document path/name
- collection keyword match from path/name
- recent user usage
- exact family overlap

### Step 6: Suggest activation plan

Possible outcomes:

- exact one-to-one matches for all fonts
- exact matches plus best collection suggestion
- partial match with user confirmation
- no match found

## Example scoring inputs

Use document context such as:

- filename
- parent folder names
- client aliases
- job codes
- recent collections activated by this user

## Safety rules

Never silently auto-activate uncertain substitutes.

If confidence is low:

- show candidates
- ask user to confirm

## Logging

Record:

- missing font names
- matched font IDs
- match method
- confidence score
- selected collection
- activation result

This improves future matching and debugging.

## Future enhancements

- better name normalization rules
- foundry-aware matching
- family completeness scoring
- user-specific ranking
- project-type ranking
- AI interpretation for ambiguous requests

```

---

# docs/09-ai-assist-layer.md

```md
# AI Assist Layer

## Important principle

AI is optional.

FontDock should be useful and reliable **without** AI.

The AI layer should improve user experience, not replace deterministic logic.

## Good uses of AI in this project

### 1. Natural-language search

Examples:

- "Open the fonts for Tesco summer POS"
- "Show me the Nike brand core fonts"
- "Load the fonts we used last month for Aldi"

AI can convert these into structured filters.

### 2. Ambiguity resolution

If multiple collections are plausible:

- suggest top 2–3 likely matches
- explain why

### 3. Context-aware ranking

Given:

- document name
- folder path hints
- missing font names
- recent usage

AI can help rank likely collections.

### 4. Query interpretation

AI can map vague user phrases to:

- client
- collection keywords
- family hints
- project type

## What AI should not do

- blindly activate substitute fonts
- override exact deterministic matches
- invent non-existent fonts
- guess without showing confidence when uncertain

## Recommended architecture

Use AI as a translation layer.

Input:

- user request or document context

Output:

- structured search intent

Example output:

```json
{
  "intent": "activate_collection",
  "client": "Tesco",
  "collection_keywords": ["summer", "pos"],
  "families": ["Gotham", "Knockout"],
  "confidence": 0.91
}
```

Then the standard search and matching engine performs the real work.

## Suggested implementation stages

### Stage 1: No LLM

Use:

- aliases
- fuzzy matching
- keyword scoring
- recent usage

### Stage 2: Optional hosted AI

Use an LLM API for:

- query interpretation
- ranking assistance

### Stage 3: Optional local AI

For privacy-sensitive teams, a local model could run in the client or server.

But this should come much later.

## AI data considerations

Be careful with:

- sensitive file paths
- client names
- project names
- internal campaign data

For hosted AI, consider redacting or simplifying path data before sending.

```

---

# docs/10-security-and-networking.md

```md
# Security and Networking

## Security goals

FontDock should:

- protect licensed font files
- restrict access by user/team/client
- avoid exposing storage publicly
- support remote users securely
- coexist with existing office VPN setups

## Recommended production model

### Best practical setup

- Host FontDock on an internal Ubuntu server or VM
- Put the server behind **Tailscale**
- Allow browser access over the Tailscale IP / MagicDNS name
- Allow the macOS client to connect over Tailscale

## Why Tailscale is a strong fit

Tailscale gives you:

- encrypted private networking
- no need to expose public ports
- simple client connectivity for remote users
- easier access control than opening services to the internet

## VPN coexistence concern

If users also need an office VPN, avoid routing everything through Tailscale.

Recommended:

- use Tailscale only for FontDock server access
- do not force full-tunnel behaviour
- do not use exit nodes for this workflow unless needed
- let the office VPN continue to handle office shares and other services

This reduces network conflicts.

## Client networking recommendation

The FontDock client should:

- connect only to the FontDock server hostname/IP over Tailscale
- avoid trying to become a general VPN replacement

## Authentication recommendations

### v1

- username/password for web
- API token/session for client

### v2+

- optional SSO / LDAP / OIDC

## Authorization recommendations

Permissions should be checked for:

- viewing clients
- viewing collections
- downloading fonts
- activating fonts

## Storage security

- do not store fonts in a public web root
- use internal storage paths
- stream downloads through authenticated endpoints
- log download and activation events

## Audit logging

Log at minimum:

- login events
- upload events
- download events
- activation events
- permission changes
- admin edits

## macOS local security

The client should:

- store tokens in Keychain if possible
- store cache in Application Support
- avoid world-readable cache directories
- validate downloaded file hashes if practical

```

---

# docs/11-development-roadmap.md

```md
# Development Roadmap

## Build philosophy

Build the product in phases where each phase is useful on its own.

## Phase 1: Core server MVP

Goal:

- upload fonts
- extract metadata
- store in DB
- browse in web UI
- download fonts manually

Deliverables:

- FastAPI app
- SQLite dev DB
- Jinja2 pages
- font upload route
- metadata parser
- fonts list page
- families page
- collections basics

## Phase 2: Better data model

Goal:

- clients
- collections
- tags
- aliases
- permissions

Deliverables:

- client CRUD
- collection CRUD
- collection assignment
- alias editing
- user roles/permissions basics

## Phase 3: Production-ready backend

Goal:

- prepare for real team usage

Deliverables:

- PostgreSQL migration path
- Alembic migrations
- better auth/session handling
- audit logging
- file deduplication

## Phase 4: macOS client MVP

Goal:

- connect to server
- search collections
- download fonts
- cache locally
- prototype activation

Deliverables:

- login UI
- local cache DB
- search UI
- collection activation UI

## Phase 5: InDesign bridge

Goal:

- send missing font data from InDesign to client

Deliverables:

- JSX script
- local HTTP endpoint or file watcher
- client request handling

## Phase 6: Matching engine

Goal:

- reliable automatic suggestions

Deliverables:

- exact matching
- alias matching
- collection scoring
- confidence handling

## Phase 7: Smart search / AI assist

Goal:

- improve UX with contextual suggestions

Deliverables:

- natural-language query parsing
- ranked suggestions
- optional LLM integration

## Phase 8: Open-source polish

Goal:

- make it contributor-friendly

Deliverables:

- clean README
- setup docs
- sample data
- screenshots
- issue templates
- contribution guide

```

---

# docs/12-mvp-checklist.md

```md
# MVP Checklist

## Server

- [ ] FastAPI project created
- [ ] Config system added
- [ ] SQLite DB connected
- [ ] SQLAlchemy models created
- [ ] Alembic added (optional in first local prototype)

## Font ingestion

- [ ] Upload route works
- [ ] Accepts OTF/TTF
- [ ] Saves file to storage folder
- [ ] Computes SHA256 hash
- [ ] Extracts metadata
- [ ] Saves DB record

## Web UI

- [ ] Login page
- [ ] Dashboard page
- [ ] Fonts list page
- [ ] Font detail page
- [ ] Families page
- [ ] Collections page
- [ ] Upload page

## Data model

- [ ] Users table
- [ ] Clients table
- [ ] Collections table
- [ ] Font families table
- [ ] Fonts table
- [ ] Font aliases table
- [ ] Collection-font join table

## Search

- [ ] Search by family
- [ ] Search by style
- [ ] Search by PostScript name
- [ ] Search by alias
- [ ] Search by collection

## Security

- [ ] Password hashing
- [ ] Protected routes
- [ ] Download permission checks
- [ ] Audit logging basics

## Client (later MVP)

- [ ] Login to server
- [ ] Sync metadata
- [ ] Search collections
- [ ] Download fonts
- [ ] Cache locally
- [ ] Prototype activation

## InDesign bridge (later MVP)

- [ ] JSX script reads current document
- [ ] Detects missing fonts
- [ ] Sends JSON to local client
- [ ] Client receives and logs request

```

---

# docs/13-open-source-plan.md

```md
# Open Source Plan

## Why open source this project

FontDock solves a real workflow problem that many teams share.

An open-source release could help:

- small studios
- agencies
- in-house marketing teams
- publishers
- freelancers
- prepress and packaging teams

## Recommended license

### MIT

Best if you want:

- maximum adoption
- easy reuse
- low friction

### Apache-2.0

Best if you want:

- explicit patent grant
- slightly more formal enterprise comfort

## Repository structure suggestion

```text
fontdock/
  README.md
  LICENSE
  CONTRIBUTING.md
  .gitignore
  docs/
  app/
  scripts/
  tests/
  examples/
```

## Good open-source hygiene

Before public release:

- remove internal client names from sample data
- remove real font files
- use fake/example metadata
- include sample JSON fixtures only
- document what users need to provide themselves

## What not to include

- proprietary font files
- real agency client data
- real job folder names
- internal credentials or URLs

## Great contributor targets

Good first issues:

- improve font metadata extraction
- add TTC support
- improve macOS activation method
- build collection import/export
- add search ranking improvements
- build better admin pages
- add Docker support

## Nice future public milestones

- v0.1: server MVP
- v0.2: collections + permissions
- v0.3: macOS client prototype
- v0.4: InDesign bridge
- v0.5: matching engine
- v0.6: smart search
- v1.0: stable creative-team workflow

## Community angle

This project will be strongest if positioned as:

- a workflow-first tool
- practical for creative production
- not trying to replace every enterprise feature on day one

That focus makes it credible.

```

---

# Suggested next file (recommended to add later)

```md
# docs/14-ai-build-prompts.md

This file should contain copy/paste prompts for using AI to build each phase of the project.

Recommended sections:

- Prompt for generating FastAPI project skeleton
- Prompt for SQLAlchemy models
- Prompt for upload route
- Prompt for font metadata extraction
- Prompt for Jinja2 templates
- Prompt for search implementation
- Prompt for macOS client scaffold
- Prompt for local HTTP listener
- Prompt for InDesign JSX script
- Prompt for matching engine
```

---

# Notes for Col

Recommended first build target:

1. Build `README.md`
2. Build the FastAPI project skeleton
3. Build upload + metadata extraction
4. Build the fonts list page
5. Build collections
6. Only then start thinking about the client

The most important thing is to get a useful server MVP first.

