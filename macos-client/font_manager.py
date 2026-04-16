import os
import sys
import subprocess
import logging
import requests
from pathlib import Path
from config import CACHE_DIR
from api_client import FontDockAPI
from database import LocalDatabase

if sys.platform == 'darwin':
    from fontdock_platform.macos import get_fonts_dir
elif sys.platform == 'win32':
    from fontdock_platform.windows import get_fonts_dir, _register_font, _unregister_font

logger = logging.getLogger(__name__)


class FontManager:
    def __init__(self, api_client: FontDockAPI, db: LocalDatabase):
        self.api = api_client
        self.db = db
    
    def download_font(self, font_id):
        font = self.db.get_font_by_id(font_id)
        if not font:
            raise ValueError(f"Font {font_id} not found in local database")
        
        if font.get('cached') and os.path.exists(font.get('cached_path', '')):
            logger.debug(f"Font {font_id} already cached at {font.get('cached_path')}")
            return font['cached_path']
        
        filename = font.get('filename_original') or f"font_{font_id}{font.get('extension', '.ttf')}"
        cache_path = CACHE_DIR / filename
        
        # If cache file exists but DB doesn't know about it, use it
        if cache_path.exists():
            try:
                # Verify file is readable
                with open(cache_path, 'rb') as f:
                    f.read(1)
                self.db.mark_font_cached(font_id, str(cache_path))
                logger.info(f"Font {font_id} using existing cache file {cache_path}")
                return str(cache_path)
            except PermissionError:
                logger.warning(f"Cache file {cache_path} exists but locked, will re-download")
        
        logger.info(f"Downloading font {font_id}: {font.get('filename_original')}")
        try:
            content = self.api.download_font(font_id)
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot download font — server unreachable. Font '{filename}' is not cached locally.")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Cannot download font — server timed out. Font '{filename}' is not cached locally.")
        except Exception as e:
            raise RuntimeError(f"Cannot download font '{filename}': {e}")
        
        try:
            with open(cache_path, 'wb') as f:
                f.write(content)
        except PermissionError:
            # File is locked - try writing to a temp name and rename
            import tempfile
            tmp_path = CACHE_DIR / f"{filename}.tmp"
            with open(tmp_path, 'wb') as f:
                f.write(content)
            # Try to replace (may still fail if locked)
            try:
                os.replace(tmp_path, cache_path)
            except PermissionError:
                # Use the tmp file as the cache path instead
                cache_path = tmp_path
                logger.warning(f"Font {font_id} cached to alternate path {cache_path}")
        
        self.db.mark_font_cached(font_id, str(cache_path))
        logger.info(f"Font {font_id} cached to {cache_path}")
        
        return str(cache_path)
    
    def download_all_fonts(self, progress_callback=None):
        """Download all fonts with progress tracking."""
        logger.info("Starting download of all fonts")
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename_original, cached FROM fonts")
        fonts = cursor.fetchall()
        conn.close()
        
        total = len(fonts)
        downloaded = 0
        skipped = 0
        failed = 0
        
        for i, (font_id, filename, cached) in enumerate(fonts):
            try:
                if progress_callback:
                    progress_callback(i + 1, total, filename)
                
                if cached:
                    skipped += 1
                    logger.debug(f"Skipping already cached font {font_id}")
                else:
                    self.download_font(font_id)
                    downloaded += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to download font {font_id}: {e}")
        
        result = {
            'total': total,
            'downloaded': downloaded,
            'skipped': skipped,
            'failed': failed
        }
        logger.info(f"Download complete: {result}")
        return result
    
    def is_font_active(self, font_id):
        """Check if a font is currently activated."""
        font = self.db.get_font_by_id(font_id)
        if not font:
            return False
        
        user_fonts_dir = get_fonts_dir()
        filename = font.get('filename_original')
        if not filename:
            return False
        
        font_path = user_fonts_dir / filename
        exists = font_path.exists()
        logger.debug(f"Font {font_id} ({filename}) active check: {exists} (path: {font_path})")
        return exists
    
    def activate_font(self, font_id):
        """Activate font by copying to user fonts directory."""
        import shutil
        
        font_path = self.download_font(font_id)
        font = self.db.get_font_by_id(font_id)
        
        try:
            # Copy font to user's Fonts directory
            user_fonts_dir = get_fonts_dir()
            user_fonts_dir.mkdir(parents=True, exist_ok=True)
            
            filename = font.get('filename_original') or os.path.basename(font_path)
            dest_path = user_fonts_dir / filename
            
            # Copy the font file (skip if already exists and readable)
            if dest_path.exists():
                try:
                    with open(dest_path, 'rb') as f:
                        f.read(1)
                    logger.info(f"Font {font_id} already at {dest_path}, skipping copy")
                except PermissionError:
                    logger.warning(f"Font {font_id} at {dest_path} exists but locked, skipping")
            else:
                shutil.copy2(font_path, dest_path)
                logger.info(f"Font {font_id} copied to {dest_path}")
            
            # On Windows, also register in registry for proper font discovery
            if sys.platform == 'win32':
                _register_font(filename, str(dest_path))
            
            # Record activation
            self.db.record_activation(font_id)
            
            return {
                'success': True,
                'font_id': font_id,
                'path': str(dest_path),
                'name': font.get('postscript_name', font.get('filename_original')),
                'message': f'Font activated: {filename}'
            }
        
        except Exception as e:
            logger.error(f"Font activation failed: {e}")
            raise RuntimeError(f"Font activation failed: {str(e)}")
    
    def deactivate_font(self, font_id):
        """Deactivate font by removing from user fonts directory."""
        font = self.db.get_font_by_id(font_id)
        if not font:
            raise ValueError(f"Font {font_id} not found")
        
        try:
            # Remove font from user's Fonts directory
            user_fonts_dir = get_fonts_dir()
            filename = font.get('filename_original')
            if not filename:
                raise ValueError(f"Cannot deactivate font {font_id}: no filename found")
            
            font_path = user_fonts_dir / filename
            
            if font_path.exists():
                os.remove(font_path)
                logger.info(f"Font {font_id} removed from {font_path}")
                message = f'Font deactivated: {filename}'
            else:
                logger.info(f"Font {font_id} already inactive")
                message = f'Font already inactive: {filename}'
            
            # On Windows, also unregister from registry
            if sys.platform == 'win32':
                _unregister_font(filename)
            
            return {
                'success': True,
                'font_id': font_id,
                'name': font.get('postscript_name', filename),
                'message': message
            }
        
        except Exception as e:
            logger.error(f"Font deactivation failed: {e}")
            raise RuntimeError(f"Font deactivation failed: {str(e)}")
    
    def activate_collection(self, collection_id):
        fonts = self.db.get_collection_fonts(collection_id)
        results = []
        
        for font in fonts:
            try:
                result = self.activate_font(font['id'])
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'font_id': font['id'],
                    'error': str(e)
                })
        
        return results
    
    def sync_metadata(self):
        logger.info("Starting metadata sync")
        try:
            logger.info("Fetching fonts...")
            fonts_data = self.api.get_fonts()
            logger.info(f"Syncing {len(fonts_data.get('items', []))} fonts to database")
            self.db.sync_fonts(fonts_data.get('items', []))
            
            logger.info("Fetching collections...")
            collections_response = self.api.get_collections()
            collections_data = collections_response.get('items', [])
            logger.debug(f"Collections count: {len(collections_data)}")
            
            if len(collections_data) > 0:
                logger.info(f"Syncing {len(collections_data)} collections to database")
                self.db.sync_collections(collections_data)
                
                logger.info("Fetching collection fonts...")
                for collection in collections_data:
                    logger.debug(f"Fetching fonts for collection {collection.get('id')}: {collection.get('name')}")
                    try:
                        collection_fonts = self.api.get_collection_fonts(collection['id'])
                        font_ids = [f['id'] for f in collection_fonts]
                        self.db.sync_collection_fonts(collection['id'], font_ids)
                    except Exception as e:
                        logger.warning(f"Failed to fetch fonts for collection {collection.get('id')}: {e}")
            else:
                logger.info("No collections to sync")
            
            logger.info("Fetching clients...")
            clients_response = self.api.get_clients()
            clients_data = clients_response.get('items', [])
            logger.debug(f"Clients count: {len(clients_data)}")
            
            if len(clients_data) > 0:
                logger.info(f"Syncing {len(clients_data)} clients to database")
                self.db.sync_clients(clients_data)
            else:
                logger.info("No clients to sync")
            
            result = {
                'fonts': len(fonts_data.get('items', [])),
                'collections': len(collections_data),
                'clients': len(clients_data)
            }
            logger.info(f"Metadata sync complete: {result}")
            return result
        except Exception as e:
            logger.error(f"Metadata sync failed: {e}", exc_info=True)
            raise
