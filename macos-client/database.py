import sqlite3
from config import DB_PATH


class LocalDatabase:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fonts (
                id INTEGER PRIMARY KEY,
                postscript_name TEXT,
                style_name TEXT,
                full_name TEXT,
                filename_original TEXT,
                family_id INTEGER,
                family_name TEXT,
                extension TEXT,
                file_hash_sha256 TEXT,
                cached BOOLEAN DEFAULT 0,
                cached_path TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY,
                name TEXT,
                description TEXT,
                client_id INTEGER,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_fonts (
                collection_id INTEGER,
                font_id INTEGER,
                PRIMARY KEY (collection_id, font_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                name TEXT,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                font_id INTEGER,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deactivated_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def sync_fonts(self, fonts):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get list of font IDs from server
        server_font_ids = [font.get('id') for font in fonts if font.get('id')]
        
        # Insert new fonts or update existing ones (preserving cached/cached_path)
        for font in fonts:
            cursor.execute("""
                INSERT OR IGNORE INTO fonts 
                (id, postscript_name, style_name, full_name, filename_original, 
                 family_id, family_name, extension, file_hash_sha256, last_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                font.get('id'),
                font.get('postscript_name'),
                font.get('style_name'),
                font.get('full_name'),
                font.get('filename_original'),
                font.get('family_id'),
                font.get('family_name'),
                font.get('extension'),
                font.get('file_hash_sha256')
            ))
            
            # Update existing fonts (preserving cached and cached_path)
            cursor.execute("""
                UPDATE fonts SET 
                    postscript_name = ?,
                    style_name = ?,
                    full_name = ?,
                    filename_original = ?,
                    family_id = ?,
                    family_name = ?,
                    extension = ?,
                    file_hash_sha256 = ?,
                    last_synced = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                font.get('postscript_name'),
                font.get('style_name'),
                font.get('full_name'),
                font.get('filename_original'),
                font.get('family_id'),
                font.get('family_name'),
                font.get('extension'),
                font.get('file_hash_sha256'),
                font.get('id')
            ))
        
        # Delete fonts that no longer exist on server
        if server_font_ids:
            placeholders = ','.join('?' * len(server_font_ids))
            cursor.execute(f"""
                DELETE FROM fonts 
                WHERE id NOT IN ({placeholders})
            """, server_font_ids)
        else:
            # If no fonts on server, delete all local fonts
            cursor.execute("DELETE FROM fonts")
        
        conn.commit()
        conn.close()
    
    def sync_collections(self, collections):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get list of collection IDs from server
        server_collection_ids = [c.get('id') for c in collections if isinstance(c, dict) and c.get('id')]
        
        for collection in collections:
            if isinstance(collection, dict):
                cursor.execute("""
                    INSERT OR REPLACE INTO collections 
                    (id, name, description, client_id, last_synced)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    collection.get('id'),
                    collection.get('name'),
                    collection.get('description'),
                    collection.get('client_id')
                ))
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping non-dict collection: {collection}")
        
        # Delete collections that no longer exist on server
        if server_collection_ids:
            placeholders = ','.join('?' * len(server_collection_ids))
            cursor.execute(f"""
                DELETE FROM collections 
                WHERE id NOT IN ({placeholders})
            """, server_collection_ids)
            # Also delete orphaned collection_fonts entries
            cursor.execute(f"""
                DELETE FROM collection_fonts 
                WHERE collection_id NOT IN ({placeholders})
            """, server_collection_ids)
        else:
            cursor.execute("DELETE FROM collections")
            cursor.execute("DELETE FROM collection_fonts")
        
        conn.commit()
        conn.close()
    
    def sync_collection_fonts(self, collection_id, font_ids):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM collection_fonts WHERE collection_id = ?", (collection_id,))
        
        for font_id in font_ids:
            cursor.execute("""
                INSERT INTO collection_fonts (collection_id, font_id)
                VALUES (?, ?)
            """, (collection_id, font_id))
        
        conn.commit()
        conn.close()
    
    def sync_clients(self, clients):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get list of client IDs from server
        server_client_ids = [client.get('id') for client in clients if isinstance(client, dict) and client.get('id')]
        
        for client in clients:
            if isinstance(client, dict):
                cursor.execute("""
                    INSERT OR REPLACE INTO clients 
                    (id, name, last_synced)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (client.get('id'), client.get('name')))
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping non-dict client: {client}")
        
        # Delete clients that no longer exist on server
        if server_client_ids:
            placeholders = ','.join('?' * len(server_client_ids))
            cursor.execute(f"""
                DELETE FROM clients 
                WHERE id NOT IN ({placeholders})
            """, server_client_ids)
        else:
            cursor.execute("DELETE FROM clients")
        
        conn.commit()
        conn.close()
    
    def search_fonts(self, query):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM fonts 
            WHERE postscript_name LIKE ? 
               OR full_name LIKE ? 
               OR family_name LIKE ?
            ORDER BY family_name, postscript_name
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def smart_match_font(self, family=None, style=None, postscript_name=None, full_name=None):
        """Smart font matching inspired by Extensis Font Sense.
        
        Tries multiple matching strategies in priority order:
        1. Exact PostScript name match (most reliable - unique per font)
        2. Family + Style exact match (case-insensitive)
        3. Full name match (case-insensitive)
        4. Family match (case-insensitive) - returns all family members
        5. Fuzzy search fallback
        
        Returns list of matching font dicts, or empty list.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        def fetch_results(cursor):
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Strategy 1: Exact PostScript name match
        if postscript_name:
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE postscript_name COLLATE NOCASE = ?
            """, (postscript_name,))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
        
        # Strategy 2: Family + Style exact match
        if family and style:
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE family_name COLLATE NOCASE = ? AND style_name COLLATE NOCASE = ?
            """, (family, style))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
            
            # Try constructing PostScript name from family+style
            # e.g. family="KFC", style="Regular" -> "KFC-Regular"
            ps_constructed = family.replace(" ", "") + "-" + style.replace(" ", "")
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE postscript_name COLLATE NOCASE = ?
            """, (ps_constructed,))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
        
        # Strategy 3: Full name match
        if full_name:
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE full_name COLLATE NOCASE = ?
            """, (full_name,))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
        
        # Also try "family style" as full_name
        if family and style and not full_name:
            combined = f"{family} {style}"
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE full_name COLLATE NOCASE = ?
            """, (combined,))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
        
        # Strategy 4: Family name match (return all members)
        if family:
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE family_name COLLATE NOCASE = ?
                ORDER BY style_name
            """, (family,))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
        
        # Strategy 5: Fuzzy search on family name
        if family:
            cursor.execute("""
                SELECT * FROM fonts 
                WHERE postscript_name COLLATE NOCASE LIKE ?
                   OR full_name COLLATE NOCASE LIKE ?
                   OR family_name COLLATE NOCASE LIKE ?
                ORDER BY family_name, postscript_name
            """, (f"%{family}%", f"%{family}%", f"%{family}%"))
            results = fetch_results(cursor)
            if results:
                conn.close()
                return results
        
        conn.close()
        return []
    
    def search_font_by_family_and_style(self, family_name, style_name):
        """Search for font by exact family and style name match (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM fonts 
            WHERE family_name COLLATE NOCASE = ? AND style_name COLLATE NOCASE = ?
        """, (family_name, style_name))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_fonts_by_family(self, family_name):
        """Get all fonts belonging to a family (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM fonts 
            WHERE family_name COLLATE NOCASE = ?
            ORDER BY style_name
        """, (family_name,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_all_collections(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM collections ORDER BY name")
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_collection_fonts(self, collection_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.* FROM fonts f
            JOIN collection_fonts cf ON f.id = cf.font_id
            WHERE cf.collection_id = ?
            ORDER BY f.family_name, f.postscript_name
        """, (collection_id,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def mark_font_cached(self, font_id, cached_path):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE fonts SET cached = 1, cached_path = ? WHERE id = ?
        """, (cached_path, font_id))
        
        conn.commit()
        conn.close()
    
    def get_font_by_id(self, font_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM fonts WHERE id = ?", (font_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        
        conn.close()
        return dict(zip(columns, row)) if row else None
    
    def record_activation(self, font_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO activations (font_id, activated_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (font_id,))
        
        conn.commit()
        conn.close()
    
    def get_recent_activations(self, limit=20):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.*, a.activated_at 
            FROM fonts f
            JOIN activations a ON f.id = a.font_id
            WHERE a.deactivated_at IS NULL
            ORDER BY a.activated_at DESC
            LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
