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
