# FontDock Server

FastAPI-based font server for creative teams.

## Quick Start

### Development

1. Install dependencies:
```bash
cd fontdock
pip install -r requirements.txt
```

2. Run the server:
```bash
./start_server.sh
```

Server runs at `http://localhost:9998` with auto-reload.

### Production (Ubuntu/Debian LXC)

```bash
sudo ./install.sh
```

Installs to `/opt/fontdock` with systemd service, Nginx reverse proxy, and auto-start on boot.

## Web UI

Access the web admin portal at `http://localhost:9998/ui/login`

Default credentials: `admin` / `admin123`

### Pages

| Page | URL | Description |
|---|---|---|
| Dashboard | `/ui/dashboard` | Overview with stats and recent uploads |
| Fonts | `/ui/fonts` | Browse, search, preview, download fonts |
| Collections | `/ui/collections` | Manage font collections |
| Clients | `/ui/clients` | Manage client organizations |
| Upload | `/ui/upload` | Upload individual font files |
| Batch Import | `/ui/import` | Import fonts from server folder or ZIP |
| Users | `/ui/users` | User management with CSV bulk import |
| Permissions | `/ui/permissions` | Granular per-user permission settings |
| Backup | `/ui/backup` | Full backup/restore with scheduled backups |
| Logs | `/ui/logs` | Server log viewer with auto-refresh |

## API Endpoints

### Auth
- `POST /auth/login` - Get access token
- `GET /auth/me` - Get current user
- `POST /change-password` - Change password

### Fonts
- `GET /api/fonts` - List fonts (with search, family, client, collection filters)
- `GET /api/fonts/{id}` - Get font details
- `POST /api/fonts/upload` - Upload font (admin or can_upload_fonts)
- `GET /api/fonts/{id}/download` - Download font
- `DELETE /api/fonts/{id}` - Delete font (admin or can_delete_fonts)
- `GET /api/fonts/families` - List font families
- `GET /api/fonts/search` - Search fonts

### Collections
- `GET /api/collections` - List collections
- `GET /api/collections/{id}` - Get collection with fonts
- `POST /api/collections` - Create collection (admin)
- `PUT /api/collections/{id}` - Update collection (admin)
- `POST /api/collections/{id}/fonts?font_id=X` - Add font to collection
- `DELETE /api/collections/{id}/fonts/{font_id}` - Remove font from collection
- `DELETE /api/collections/{id}` - Delete collection (admin)

### Clients
- `GET /api/clients` - List clients
- `GET /api/clients/{id}` - Get client with fonts
- `POST /api/clients` - Create client (admin)
- `PUT /api/clients/{id}` - Update client (admin)
- `DELETE /api/clients/{id}` - Delete client (admin)

### Users (admin only)
- `GET /api/users` - List users
- `POST /api/users` - Create user (with first_name, last_name, permissions)
- `GET /api/users/{id}` - Get user
- `PUT /api/users/{id}` - Update user
- `POST /api/users/import-csv` - Bulk import users from CSV
- `GET /api/users/import-template` - Download CSV template

### Backup & Restore (admin only)
- `GET /api/admin/backups` - List available backups
- `POST /api/admin/backup` - Create full backup (ZIP: DB + fonts)
- `GET /api/admin/backup/{filename}` - Download a backup
- `POST /api/admin/restore` - Restore from uploaded backup ZIP
- `POST /api/admin/restore/{filename}` - Restore from existing backup
- `DELETE /api/admin/backup/{filename}` - Delete a backup
- `GET /api/admin/backup/settings` - Get backup schedule settings
- `POST /api/admin/backup/settings` - Update backup schedule (never/daily/weekly/monthly)

### Batch Import (admin only)
- `POST /api/import/batch-folder?folder_path=X` - Import from server folder
- `POST /api/import/upload-zip` - Import from uploaded ZIP
- `GET /api/import/browse?path=X` - Browse server filesystem

### Server
- `GET /health` - Health check
- `POST /api/admin/restart` - Restart server (admin)
- `GET /auth/sessions` - Active session count

## User Permissions

Users can be assigned granular permissions:

| Permission | Description |
|---|---|
| `is_admin` | Full admin access (all permissions) |
| `can_create_users` | Can create new users |
| `can_delete_users` | Can delete/deactivate users |
| `can_upload_fonts` | Can upload font files |
| `can_download_fonts` | Can download font files (default: true) |
| `can_delete_fonts` | Can delete fonts |
| `can_create_collections` | Can create collections and add fonts |
| `can_create_clients` | Can create clients |

## CSV Bulk Import

Download the template from the Users page or API:

```
first_name,last_name,username,email,password,is_admin,can_create_users,can_delete_users,can_upload_fonts,can_download_fonts,can_delete_fonts,can_create_collections,can_create_clients
John,Doe,jdoe,jdoe@company.com,ChangeMe123,false,false,false,true,true,false,false,false
Admin,User,admin,admin@company.com,AdminPass456,true,true,true,true,true,true,true,true
```

## Backup & Restore

- **Full backups** include the SQLite database and all font files in a single ZIP
- **Scheduled backups** default to weekly; configurable to daily, monthly, or never
- **Retention**: Only the 2 most recent backups are kept
- **Restore**: Upload a backup ZIP from another server to migrate all data
- Server restarts automatically after restore

## Configuration

Environment variables (or `.env` file):
- `SERVER_HOST` - Bind address (default: `0.0.0.0`)
- `SERVER_PORT` - Port (default: `8000`)
- `SECRET_KEY` - JWT secret key (auto-generated by install.sh)
- `DATABASE_URL` - Database connection string (default: `sqlite:///./fontdock.db`)
- `STORAGE_PATH` - Path to store font files (default: `./storage/fonts`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Authentication

The API uses OAuth2 with JWT tokens. Include the token in requests:

```bash
Authorization: Bearer <token>
```
