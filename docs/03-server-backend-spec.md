# Server Backend Specification

## Status: Phase 1-2 MVP Complete

**Last Updated:** April 2, 2026  
**Completed By:** Initial MVP build session

---

## What We Built

### Core Infrastructure ✅

- **FastAPI** application with modular router structure
- **SQLite** database for development (PostgreSQL ready for production)
- **SQLAlchemy** ORM with full model definitions
- **Pydantic** schemas for API validation
- **JWT authentication** with token-based auth
- **File storage** system for font files
- **Restart script** for server management

### Database Schema ✅

Implemented all core tables:
- `users` - with granular permissions (create, delete, upload, download, collections, clients)
- `font_families` - grouping by typographic family name
- `fonts` - individual font files with full metadata
- `clients` - client/brand management
- `collections` - font collections per client or global
- `collection_fonts` - many-to-many join table
- `font_aliases` - for legacy name mapping (table ready)

### API Endpoints ✅

#### Authentication
- `POST /auth/login` - JWT token generation
- `GET /auth/me` - current user info

#### Fonts
- `GET /api/fonts` - list with pagination, search, family data included
- `POST /api/fonts/upload` - file upload with metadata extraction (permission-based)
- `GET /api/fonts/{font_id}` - font details
- `DELETE /api/fonts/{font_id}` - delete single font (permission-based)
- `DELETE /api/fonts/all` - bulk delete all fonts (admin only)
- `GET /api/fonts/{font_id}/download` - download with auth (header or query token)
- `GET /api/fonts/{font_id}/preview` - font preview generation

#### Collections
- `GET /api/collections` - list collections
- `POST /api/collections` - create collection
- `GET /api/collections/{id}` - collection details with fonts
- `POST /api/collections/{id}/fonts` - add font to collection (permission-based)
- `DELETE /api/collections/{id}/fonts/{font_id}` - remove font from collection

#### Clients
- `GET /api/clients` - list clients
- `POST /api/clients` - create client
- `GET /api/clients/{id}` - client details with collections

#### Users
- `GET /api/users` - list users (admin)
- `POST /api/users` - create user (admin)
- `PUT /api/users/{id}` - update user including permissions

#### Admin
- `POST /api/admin/restart-script` - restart server
- `GET /api/admin/logs` - view server logs
- `DELETE /api/admin/logs` - clear server logs

### Web UI Pages ✅

- **Login** - Authentication page
- **Dashboard** - Stats overview (fonts, families, collections, clients)
- **Fonts** - Family-grouped list view with actual font rendering
- **Collections** - List all collections
- **Collection Detail** - View collection with fonts, add fonts by family
- **Clients** - Client management
- **Upload** - Font upload with client/collection assignment
- **Users** - User management
- **Permissions** - Granular permission editor
- **Logs** - Server log viewer with download/clear

### Key Features Implemented ✅

1. **Font Ingestion**
   - Accepts OTF, TTF, TTC files
   - Extracts metadata (family, style, PostScript name, etc.)
   - Uses typographic family names (nameID 16/17) for proper grouping
   - SHA256 hash computation
   - File deduplication via hash check

2. **Font Preview**
   - CSS @font-face dynamic loading with authentication
   - Actual font rendering in browser (Bold, Light, etc. show correctly)

3. **Permissions System**
   - `can_create_users`
   - `can_delete_users`
   - `can_upload_fonts`
   - `can_download_fonts`
   - `can_delete_fonts`
   - `can_create_collections`
   - `can_create_clients`

4. **Collection Management**
   - Add fonts grouped by family
   - "Add All" button for entire families
   - Expandable family view with individual font selection

5. **Admin Tools**
   - Server restart button
   - Log viewer (auto-refresh, download, clear)
   - DB status indicator
   - Logged-in user display

---

## What's Still Pending (Tomorrow)

### Priority 1: Backup System
- Database backup endpoint
- Font files backup
- Automated scheduled backups
- Restore functionality

### Priority 2: Font Activation Flow
- Collection download all fonts
- Font activation status tracking
- Download history

### Priority 3: Search Improvements
- Full-text search across all font fields
- Alias matching
- Fuzzy search for typos

### Priority 4: Production Hardening
- PostgreSQL migration path
- Alembic database migrations
- Environment-based configuration
- Better error handling

---

## Technical Stack

- **Python 3.11+**
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **fontTools** - Font metadata extraction
- **PyJWT** - Authentication
- **passlib** - Password hashing
- **Jinja2** - Templating
- **SQLite** - Development database

---

## File Structure

```
fontdock/
├── app/
│   ├── main.py              # FastAPI app setup
│   ├── config.py            # Settings
│   ├── db.py                # Database connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API endpoints
│   │   ├── auth.py
│   │   ├── fonts.py
│   │   ├── collections.py
│   │   ├── clients.py
│   │   ├── users.py
│   │   └── admin.py
│   ├── services/            # Business logic
│   │   ├── font_ingest_service.py
│   │   ├── font_search_service.py
│   │   └── auth_service.py
│   └── templates/           # Jinja2 templates
├── docs/                    # Documentation
├── storage/fonts/           # Font file storage
├── logs/                    # Server logs
└── scripts/                 # Utility scripts
    └── restart.sh
```

---

## API Authentication

All protected endpoints require:
- **Header**: `Authorization: Bearer <token>`
- **Query param** (for @font-face only): `?token=<token>`

Token obtained via `POST /auth/login` with username/password.

---

## Next Steps

1. **Backup System** - Critical for production use
2. **macOS Client** - Local font activation
3. **InDesign Bridge** - Missing font detection
4. **Production Deployment** - PostgreSQL, migrations, docs

The server MVP is **functional and usable** for font management today.
