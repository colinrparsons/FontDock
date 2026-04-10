---
description: Add client_id column to Font model with database migration
---

# Add client_id Column to Font Model

## Overview
This workflow adds a `client_id` foreign key column to the `fonts` table to link fonts to clients. This enables client-based font activation where fonts can be grouped and activated per client.

## Steps

### 1. Update Font Model
Add the `client_id` column and relationship to `app/models/__init__.py`:

```python
class Font(Base):
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("font_families.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)  # NULL = unassigned
    # ... other columns ...
    
    # Relationships
    family = relationship("FontFamily", back_populates="fonts")
    client = relationship("Client", back_populates="fonts")
    collections = relationship("Collection", secondary=collection_fonts, back_populates="fonts")
```

### 2. Update Client Model
Add the reverse relationship to `app/models/__init__.py`:

```python
class Client(Base):
    # ... existing columns ...
    
    # Relationships
    collections = relationship("Collection", back_populates="client")
    fonts = relationship("Font", back_populates="client")
    user_permissions = relationship("UserClientPermission", back_populates="client")
```

### 3. Apply Database Migration
Run the SQLite migration to add the column:

```sql
ALTER TABLE fonts ADD COLUMN client_id INTEGER REFERENCES clients(id);
```

Or use the migration script:

```bash
cd /Users/colinparsons/Documents/Developement/FontDock/fontdock
sqlite3 fontdock.db "ALTER TABLE fonts ADD COLUMN client_id INTEGER REFERENCES clients(id);"
```

### 4. Verify Migration
Check the database schema:

```sql
.schema fonts
```

Or query:

```sql
SELECT name FROM pragma_table_info('fonts') WHERE name = 'client_id';
```

### 5. Restart Server
Restart the application server to load the updated models:

```bash
# Kill existing server
pkill -f "python.*run.py"

# Start server
cd /Users/colinparsons/Documents/Developement/FontDock/fontdock
source ../venv/bin/activate
python run.py
```

### 6. Test Client-Font Association
Verify the relationship works:

```python
# Example: Assign fonts to a client
from app.db import get_db
from app.models import Font, Client

db = next(get_db())
client = db.query(Client).filter_by(name="Costa").first()
font = db.query(Font).first()
font.client_id = client.id
db.commit()
```

## Troubleshooting

### Error: "no such column: client_id"
The migration hasn't been applied. Run the ALTER TABLE command again.

### Error: "Foreign key mismatch"
Ensure the client_id value references an existing client in the clients table.

### Error: "Mapper has no property 'fonts'"
Both sides of the relationship must be defined - check Client model has `fonts = relationship()` and Font model has `client = relationship()`.

## Related Files
- `app/models/__init__.py` - Font and Client model definitions
- `fontdock.db` - SQLite database file
- `app/routers/import_batch.py` - Batch import that sets client_id on fonts

## Notes
- `client_id` is nullable to allow fonts without client assignment
- Deleting a client will not cascade delete fonts (fonts become unassigned)
- Client-based font activation is handled by the desktop client application
