# FontDock Server

FastAPI-based font server for creative teams.

## Quick Start

1. Install dependencies:
```bash
cd fontdock
pip install -r requirements.txt
```

2. Create initial admin user:
```bash
python scripts/create_admin.py
```

3. Run the server:
```bash
python run.py
```

4. Open API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Auth
- `POST /auth/login` - Get access token
- `GET /auth/me` - Get current user

### Fonts
- `GET /api/fonts` - List fonts
- `GET /api/fonts/{id}` - Get font details
- `POST /api/fonts/upload` - Upload font (admin)
- `GET /api/fonts/{id}/download` - Download font

### Collections
- `GET /api/collections` - List collections
- `GET /api/collections/{id}` - Get collection
- `POST /api/collections` - Create collection (admin)
- `PUT /api/collections/{id}` - Update collection (admin)
- `POST /api/collections/{id}/fonts` - Add font to collection (admin)

### Clients
- `GET /api/clients` - List clients
- `GET /api/clients/{id}` - Get client
- `POST /api/clients` - Create client (admin)
- `PUT /api/clients/{id}` - Update client (admin)

### Users
- `GET /api/users` - List users (admin)
- `POST /api/users` - Create user (admin)

## Configuration

Environment variables:
- `SECRET_KEY` - JWT secret key
- `DATABASE_URL` - Database connection string
- `STORAGE_PATH` - Path to store font files

## Authentication

The API uses OAuth2 with JWT tokens. Include the token in requests:

```bash
Authorization: Bearer <token>
```
