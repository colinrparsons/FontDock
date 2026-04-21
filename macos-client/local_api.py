from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import threading
import re
import os
import subprocess
from config import LOCAL_API_PORT
from font_manager import FontManager

if sys.platform == 'darwin':
    from fontdock_platform.macos import (
        is_app_running as _is_app_running_mac,
        get_open_documents as _get_open_documents_mac,
        get_photoshop_font_names as _get_ps_fonts_mac,
        detect_installed_apps as _detect_apps_mac,
        extract_fonts_from_file as _extract_fonts_mac,
        get_request_dir as _get_request_dir_mac,
    )
elif sys.platform == 'win32':
    from fontdock_platform.windows import (
        is_app_running as _is_app_running_win,
        get_open_documents as _get_open_documents_win,
        get_photoshop_font_names as _get_ps_fonts_win,
        detect_installed_apps as _detect_apps_win,
        extract_fonts_from_file as _extract_fonts_win,
        get_request_dir as _get_request_dir_win,
    )


class AdobeBridgeHandler(BaseHTTPRequestHandler):
    font_manager = None
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'fontdock-client'}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/activate-file':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                file_path = data.get('file_path', '')
                
                if not file_path or not os.path.exists(file_path):
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'File not found: {file_path}'}).encode('utf-8'))
                    return
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"activate-file: parsing '{file_path}'")
                
                # Extract font names from the file
                font_names = self.extract_fonts_from_file(file_path)
                logger.info(f"activate-file: found {len(font_names)} fonts: {font_names}")
                
                if not font_names:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'fonts_found': 0, 'results': []}).encode('utf-8'))
                    return
                
                # Activate each font
                results = []
                for font_name in font_names:
                    try:
                        result = self.activate_font_by_name(font_name)
                        results.append(result)
                    except Exception as e:
                        results.append({
                            'font_name': font_name,
                            'success': False,
                            'error': str(e)
                        })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'fonts_found': len(font_names),
                    'font_names': font_names,
                    'results': results
                }).encode('utf-8'))
            
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        
        elif self.path == '/open-fonts':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                # Support both old format (font names) and new format (family/style pairs)
                font_list = data.get('fonts', [])
                
                results = []
                for font_item in font_list:
                    try:
                        # New format: {"family": "...", "style": "..."}
                        if isinstance(font_item, dict):
                            family = font_item.get('family')
                            style = font_item.get('style')
                            result = self.activate_font_by_family_style(family, style)
                        # Old format: "Font Name"
                        else:
                            result = self.activate_font_by_name(font_item)
                        results.append(result)
                    except Exception as e:
                        error_name = font_item if isinstance(font_item, str) else f"{font_item.get('family')} {font_item.get('style')}"
                        results.append({
                            'font_name': error_name,
                            'success': False,
                            'error': str(e)
                        })
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode('utf-8'))
            
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def activate_font_by_family_style(self, family_name, style_name):
        """Activate fonts using smart multi-field matching.
        InDesign reports family+style; we try PostScript name, family+style,
        full_name, family match, and fuzzy fallback in priority order."""
        if not self.font_manager:
            raise RuntimeError("Font manager not initialized")
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Smart matching family='{family_name}' style='{style_name}'")
        
        # Use smart matching - tries PostScript, family+style, full_name, family, fuzzy
        matched_fonts = self.font_manager.db.smart_match_font(
            family=family_name,
            style=style_name
        )
        logger.info(f"  Smart match returned {len(matched_fonts)} fonts")
        
        if not matched_fonts:
            raise ValueError(f"Font family '{family_name}' style '{style_name}' not found")
        
        # If only one specific style matched (not the whole family), activate just that
        # If the whole family matched, activate all members
        # Determine if we got a family-wide match vs a specific style match
        specific_matches = [f for f in matched_fonts 
                           if f.get('style_name', '').lower() == style_name.lower()]
        
        # If we matched the whole family (strategy 4/5), activate all members
        # If we matched a specific font (strategy 1/2/3), just activate that one
        if specific_matches and len(matched_fonts) > len(specific_matches):
            # Family-wide match - activate all
            fonts_to_activate = matched_fonts
            logger.info(f"  Family-wide match: activating all {len(fonts_to_activate)} fonts")
        elif specific_matches:
            # Specific style match - activate just the requested style
            fonts_to_activate = specific_matches
            logger.info(f"  Specific style match: activating {len(fonts_to_activate)} font(s)")
        else:
            # No exact style match but found family - activate all
            fonts_to_activate = matched_fonts
            logger.info(f"  Family match (no exact style): activating all {len(fonts_to_activate)} fonts")
        
        # Activate fonts
        results = []
        for font in fonts_to_activate:
            try:
                result = self.font_manager.activate_font(font['id'])
                logger.info(f"  Activated: {font['postscript_name']} - success={result.get('success', False)}")
                results.append(result)
            except Exception as e:
                logger.warning(f"  Failed to activate {font['postscript_name']}: {e}")
        
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(f"  Activation complete: {success_count}/{len(fonts_to_activate)} fonts activated")
        return {'success': success_count > 0, 'family': family_name, 'activated': success_count, 'total': len(fonts_to_activate)}
    
    def activate_font_by_name(self, font_name):
        if not self.font_manager:
            raise RuntimeError("Font manager not initialized")
        
        import logging
        logger = logging.getLogger(__name__)
        
        # Try exact match first
        logger.info(f"Searching for font: '{font_name}'")
        fonts = self.font_manager.db.search_fonts(font_name)
        logger.info(f"Exact search returned {len(fonts)} results")
        
        # Helvetica Neue weight code mappings
        helvetica_weight_map = {
            '25 Ultra Light': 'UltLt',
            '35 Thin': 'Th',
            '45 Light': 'Lt',
            '46 Light Italic': 'LtIt',
            '55 Roman': 'Roman',
            '56 Italic': 'It',
            '65 Medium': 'Md',
            '66 Medium Italic': 'MdIt',
            '75 Bold': 'Bd',
            '76 Bold Italic': 'BdIt',
            '85 Heavy': 'Hv',
            '95 Black': 'Blk',
            '67 Medium Condensed': 'MdCn',
            '77 Bold Condensed': 'BdCn',
            '57 Condensed': 'Cn',
        }
        
        # If no exact match, try to match by converting to PostScript-style name
        # e.g., "Costa Display Wave Regular" -> "CostaDisplay-WaveRegular"
        if not fonts:
            # Split into family and style parts
            # Common patterns: "Family Style", "Family Multi Word Style"
            # Try different split points to find the right family/style boundary
            words = font_name.split()
            
            # Try splitting at different positions
            for split_pos in range(len(words) - 1, 0, -1):
                family_part = " ".join(words[:split_pos])
                style_part = " ".join(words[split_pos:])
                
                # Check if this is a Helvetica Neue font with weight code
                if "Helvetica Neue" in family_part and style_part in helvetica_weight_map:
                    # Use the abbreviated PostScript style name
                    ps_style = helvetica_weight_map[style_part]
                    ps_name = family_part.replace(" ", "") + "-" + ps_style
                    logger.info(f"Trying Helvetica weight mapping: '{ps_name}'")
                    fonts = self.font_manager.db.search_fonts(ps_name)
                    logger.info(f"Helvetica search returned {len(fonts)} results")
                    if fonts:
                        break
                
                # Convert to PostScript format: FamilyName-StyleName
                ps_name = family_part.replace(" ", "") + "-" + style_part.replace(" ", "")
                logger.info(f"Trying PostScript format: '{ps_name}'")
                fonts = self.font_manager.db.search_fonts(ps_name)
                logger.info(f"PostScript search returned {len(fonts)} results")
                
                if fonts:
                    break
        
        if not fonts:
            raise ValueError(f"Font '{font_name}' not found")
        
        if len(fonts) > 1:
            raise ValueError(f"Ambiguous font name '{font_name}' - {len(fonts)} matches found")
        
        font = fonts[0]
        logger.info(f"Activating font: {font['postscript_name']}")
        return self.font_manager.activate_font(font['id'])
    
    def log_message(self, format, *args):
        pass
    
    @staticmethod
    def extract_fonts_from_file(file_path):
        """Extract font PostScript names from Adobe document files.
        Delegates to platform-specific implementation."""
        if sys.platform == 'darwin':
            return _extract_fonts_mac(file_path)
        elif sys.platform == 'win32':
            return _extract_fonts_win(file_path)
        return []


class RequestFileWatcher:
    """Watches for request files from Adobe scripts (Illustrator/Photoshop)
    that can't make HTTP requests and instead write .json files to disk."""
    
    if sys.platform == 'darwin':
        REQUEST_DIR = _get_request_dir_mac()
    elif sys.platform == 'win32':
        REQUEST_DIR = _get_request_dir_win()
    else:
        REQUEST_DIR = os.path.expanduser("~/FontDock/requests")
    POLL_INTERVAL = 2  # seconds
    
    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager
        self.thread = None
        self._running = False
    
    def start(self):
        # Ensure request directory exists
        os.makedirs(self.REQUEST_DIR, exist_ok=True)
        
        self._running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        
        print(f"Request file watcher started - watching {self.REQUEST_DIR}")
    
    def stop(self):
        self._running = False
    
    def _watch_loop(self):
        import logging
        logger = logging.getLogger(__name__)
        
        while self._running:
            try:
                # Scan for request files
                for filename in os.listdir(self.REQUEST_DIR):
                    if not filename.endswith('.json'):
                        continue
                    
                    filepath = os.path.join(self.REQUEST_DIR, filename)
                    try:
                        with open(filepath, 'r') as f:
                            raw_content = f.read()
                        logger.info(f"  Raw request content: {raw_content[:500]}")
                        try:
                            data = json.loads(raw_content)
                        except json.JSONDecodeError as je:
                            logger.error(f"  Invalid JSON in request file: {je}")
                            os.remove(filepath)
                            continue
                        logger.info(f"  Parsed keys: {list(data.keys())}")
                        
                        file_path = data.get('file_path', '') or data.get('document_path', '')
                        app_name = data.get('app', 'unknown')
                        font_names_from_app = data.get('font_names', [])
                        fonts_with_style = data.get('fonts', [])  # InDesign sends [{family, style}]
                        
                        logger.info(f"Request file watcher: processing {filename} from {app_name}")
                        logger.info(f"  File path: {file_path}")
                        
                        # Determine font names to activate:
                        # - Photoshop sends font_names directly (DOM works in PS)
                        # - Illustrator only sends file_path (DOM fails with GFKU)
                        # - InDesign sends fonts array with {family, style} objects
                        font_names = []
                        if font_names_from_app:
                            font_names = font_names_from_app
                            logger.info(f"  Using {len(font_names)} font names from {app_name} DOM: {font_names}")
                        elif fonts_with_style:
                            # InDesign format: convert {family, style} to "family style" strings
                            for f in fonts_with_style:
                                family = f.get('family', '')
                                style = f.get('style', '')
                                if family and style:
                                    font_names.append(f"{family} {style}")
                                elif family:
                                    font_names.append(family)
                            logger.info(f"  Using {len(font_names)} font names from InDesign: {font_names}")
                        elif file_path and os.path.exists(file_path):
                            font_names = AdobeBridgeHandler.extract_fonts_from_file(file_path)
                            logger.info(f"  Extracted {len(font_names)} fonts from file: {font_names}")
                        else:
                            logger.warning(f"  No font names and file not found: {file_path}")
                        
                        if fonts_with_style:
                            # InDesign: activate using family+style lookup directly
                            for f in fonts_with_style:
                                family = f.get('family', '')
                                style = f.get('style', '')
                                try:
                                    result = self._activate_font_by_family_style(family, style)
                                    logger.info(f"  Activated: {family} {style} - success={result}")
                                except Exception as e:
                                    logger.warning(f"  Failed to activate '{family} {style}': {e}")
                        elif font_names:
                            for font_name in font_names:
                                try:
                                    result = self._activate_font(font_name)
                                    logger.info(f"  Activated: {font_name} - success={result}")
                                except Exception as e:
                                    logger.warning(f"  Failed to activate '{font_name}': {e}")
                        
                        # Remove processed request file
                        os.remove(filepath)
                        logger.info(f"  Processed and removed {filename}")
                        
                    except Exception as e:
                        logger.error(f"Error processing request file {filename}: {e}")
                        # Move bad files aside instead of leaving them
                        try:
                            error_path = filepath + '.error'
                            os.rename(filepath, error_path)
                        except:
                            pass
            
            except Exception as e:
                logger.error(f"Request file watcher error: {e}")
            
            # Poll interval
            threading.Event().wait(self.POLL_INTERVAL)
    
    def _activate_font_by_family_style(self, family, style):
        """Activate fonts using smart multi-field matching.
        InDesign reports family+style; we try PostScript name, family+style,
        full_name, family match, and fuzzy fallback in priority order."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Smart matching family='{family}' style='{style}'")
        
        # Use smart matching - tries PostScript, family+style, full_name, family, fuzzy
        matched_fonts = self.font_manager.db.smart_match_font(
            family=family,
            style=style
        )
        logger.info(f"  Smart match returned {len(matched_fonts)} fonts")
        
        if not matched_fonts:
            raise ValueError(f"Font family '{family}' style '{style}' not found")
        
        # Determine if we got a family-wide match vs a specific style match
        specific_matches = [f for f in matched_fonts 
                           if f.get('style_name', '').lower() == style.lower()]
        
        if specific_matches and len(matched_fonts) > len(specific_matches):
            # Family-wide match - activate all
            fonts_to_activate = matched_fonts
            logger.info(f"  Family-wide match: activating all {len(fonts_to_activate)} fonts")
        elif specific_matches:
            # Specific style match - activate just the requested style
            fonts_to_activate = specific_matches
            logger.info(f"  Specific style match: activating {len(fonts_to_activate)} font(s)")
        else:
            # No exact style match but found family - activate all
            fonts_to_activate = matched_fonts
            logger.info(f"  Family match (no exact style): activating all {len(fonts_to_activate)} fonts")
        
        # Activate fonts
        results = []
        for font in fonts_to_activate:
            try:
                result = self.font_manager.activate_font(font['id'])
                logger.info(f"  Activated: {font['postscript_name']} - success={result.get('success', False)}")
                results.append(result)
            except Exception as e:
                logger.warning(f"  Failed to activate {font['postscript_name']}: {e}")
        
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(f"  Activation complete: {success_count}/{len(fonts_to_activate)} fonts activated")
        return {'success': success_count > 0, 'family': family, 'activated': success_count, 'total': len(fonts_to_activate)}
    
    def _activate_font(self, font_name):
        """Activate a font using font_manager directly.
        Uses first match if multiple found - PostScript names should be unique
        but search may return partial matches."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Searching for font: '{font_name}'")
        fonts = self.font_manager.db.search_fonts(font_name)
        logger.info(f"Search returned {len(fonts)} results")
        
        if not fonts:
            raise ValueError(f"Font '{font_name}' not found")
        
        if len(fonts) > 1:
            # Try exact postscript_name match first
            exact = [f for f in fonts if f['postscript_name'] == font_name]
            if exact:
                font = exact[0]
            else:
                # Use first match with a warning
                font = fonts[0]
                logger.warning(f"Multiple matches for '{font_name}', using first: {font['postscript_name']}")
        else:
            font = fonts[0]
        
        logger.info(f"Activating font: {font['postscript_name']}")
        return self.font_manager.activate_font(font['id'])


class AdobeAppWatcher:
    """Watches Adobe Illustrator and Photoshop for newly opened documents
    and auto-activates their fonts.
    
    On macOS: Uses AppleScript to query open docs.
    On Windows: Uses PowerShell/COM automation.
    Auto-detects installed Adobe app versions - no hardcoded version numbers."""
    
    POLL_INTERVAL = 5  # seconds between checks
    
    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager
        self.thread = None
        self._running = False
        self._known_docs = {}  # app_name -> set of file paths
        self._detected_apps = {}  # app_name -> {applescript_name, process_pattern, extensions}
        self._detect_installed_apps()
    
    def _detect_installed_apps(self):
        """Auto-detect installed Adobe apps using platform-specific detection."""
        import logging
        logger = logging.getLogger(__name__)
        
        if sys.platform == 'darwin':
            self._detected_apps = _detect_apps_mac()
        elif sys.platform == 'win32':
            self._detected_apps = _detect_apps_win()
        
        if self._detected_apps:
            detected_names = [v['applescript_name'] for v in self._detected_apps.values()]
            print(f"Adobe app watcher: detected apps: {', '.join(detected_names)}")
        else:
            print("Adobe app watcher: no Adobe apps detected")
    
    def start(self):
        if not self._detected_apps:
            print("Adobe app watcher: no apps to watch, skipping")
            return
        
        self._running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        print("Adobe app watcher started - auto-activation active")
    
    def stop(self):
        self._running = False
    
    def _watch_loop(self):
        import logging
        logger = logging.getLogger(__name__)
        
        while self._running:
            try:
                for app_name, app_info in self._detected_apps.items():
                    try:
                        # Check if app is running (System Events won't launch apps)
                        if not self._is_app_running(app_info['applescript_name']):
                            # Clear known docs when app quits
                            self._known_docs.pop(app_name, None)
                            continue
                        
                        # Get list of open document paths
                        open_docs = self._get_open_documents(app_name, app_info)
                        
                        if open_docs is None:
                            continue  # AppleScript failed
                        
                        # Get previously known docs for this app
                        known = self._known_docs.get(app_name, set())
                        
                        # Find new documents
                        new_docs = [d for d in open_docs if d not in known]
                        
                        if new_docs:
                            for doc_path in new_docs:
                                ext = os.path.splitext(doc_path)[1].lower()
                                if ext in app_info['extensions']:
                                    logger.info(f"Auto-activate: new {app_name} document: {doc_path}")
                                    self._process_document(doc_path, app_name)
                            
                            # Update known docs
                            self._known_docs[app_name] = set(open_docs)
                        elif known != set(open_docs):
                            # Some docs were closed, update tracking
                            self._known_docs[app_name] = set(open_docs)

                    
                    except Exception as e:
                        logger.debug(f"App watcher error for {app_name}: {e}")
            
            except Exception as e:
                logger.error(f"Adobe app watcher error: {e}")
            
            threading.Event().wait(self.POLL_INTERVAL)
    
    def _is_app_running(self, applescript_name):
        """Check if an Adobe app is running. Platform-specific implementation."""
        if sys.platform == 'darwin':
            return _is_app_running_mac(applescript_name)
        elif sys.platform == 'win32':
            return _is_app_running_win(applescript_name)
        return False
    
    def _get_open_documents(self, app_name, app_info):
        """Query Adobe app for open document paths. Platform-specific implementation."""
        if sys.platform == 'darwin':
            return _get_open_documents_mac(
                app_info['applescript_name'],
                app_info['doc_path_property']
            )
        elif sys.platform == 'win32':
            return _get_open_documents_win(app_name)
        return None
    
    def _process_document(self, file_path, app_name):
        """Extract fonts from a document and activate them.
        For Photoshop: triggers the ExtendScript via AppleScript (DOM can read fonts).
        For Illustrator/InDesign: parses the file on disk directly."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            if app_name == 'photoshop':
                # Photoshop's do javascript doesn't work in PS 2026.
                # Instead, use AppleScript to scan text layers for font names directly.
                as_name = self._detected_apps.get('photoshop', {}).get('applescript_name', 'Adobe Photoshop 2026')
                font_names = self._get_photoshop_font_names(as_name)
                if font_names:
                    logger.info(f"  Found {len(font_names)} fonts via Photoshop AppleScript: {font_names}")
                    for font_name in font_names:
                        try:
                            fonts = self.font_manager.db.search_fonts(font_name)
                            if not fonts:
                                logger.warning(f"  Font not found: {font_name}")
                                continue
                            if len(fonts) > 1:
                                exact = [f for f in fonts if f['postscript_name'] == font_name]
                                font = exact[0] if exact else fonts[0]
                            else:
                                font = fonts[0]
                            result = self.font_manager.activate_font(font['id'])
                            logger.info(f"  Activated: {font_name} - success={result.get('success', False)}")
                        except Exception as e:
                            logger.warning(f"  Failed to activate '{font_name}': {e}")
                else:
                    # Fallback: try file parsing (less reliable for PSD)
                    logger.info(f"  Could not get fonts from Photoshop AppleScript, trying file parsing")
                    self._activate_fonts_from_file(file_path)
            else:
                # Illustrator/InDesign: parse the file on disk
                self._activate_fonts_from_file(file_path)
        
        except Exception as e:
            logger.error(f"  Error processing document {file_path}: {e}")
    
    def _get_photoshop_font_names(self, as_name):
        """Get font PostScript names from open Photoshop documents. Platform-specific."""
        if sys.platform == 'darwin':
            return _get_ps_fonts_mac(as_name)
        elif sys.platform == 'win32':
            return _get_ps_fonts_win(as_name)
        return []
    
    def _activate_fonts_from_file(self, file_path):
        """Extract fonts from a file on disk and activate them"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            font_names = AdobeBridgeHandler.extract_fonts_from_file(file_path)
            logger.info(f"  Found {len(font_names)} fonts in {os.path.basename(file_path)}: {font_names}")
            
            for font_name in font_names:
                try:
                    fonts = self.font_manager.db.search_fonts(font_name)
                    
                    if not fonts:
                        logger.warning(f"  Font not found: {font_name}")
                        continue
                    
                    if len(fonts) > 1:
                        exact = [f for f in fonts if f['postscript_name'] == font_name]
                        font = exact[0] if exact else fonts[0]
                    else:
                        font = fonts[0]
                    
                    result = self.font_manager.activate_font(font['id'])
                    logger.info(f"  Activated: {font_name} - success={result.get('success', False)}")
                
                except Exception as e:
                    logger.warning(f"  Failed to activate '{font_name}': {e}")
        
        except Exception as e:
            logger.error(f"  Error extracting fonts from {file_path}: {e}")


class LocalAPIServer:
    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager
        self.server = None
        self.thread = None
        self.file_watcher = None
        self.app_watcher = None
    
    def start(self):
        AdobeBridgeHandler.font_manager = self.font_manager
        
        self.server = HTTPServer(('127.0.0.1', LOCAL_API_PORT), AdobeBridgeHandler)
        
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        
        print(f"Local API server started on http://127.0.0.1:{LOCAL_API_PORT}")
        
        # Start the file watcher for manual script triggers
        self.file_watcher = RequestFileWatcher(self.font_manager)
        self.file_watcher.start()
        
        # Start the app watcher for auto-activation (Illustrator/Photoshop)
        self.app_watcher = AdobeAppWatcher(self.font_manager)
        self.app_watcher.start()
    
    def stop(self):
        if self.app_watcher:
            self.app_watcher.stop()
        if self.file_watcher:
            self.file_watcher.stop()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
