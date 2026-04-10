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
