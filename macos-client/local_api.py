from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import re
import os
import subprocess
from config import LOCAL_API_PORT
from font_manager import FontManager


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
        """Activate font by exact family and style name match - most reliable method"""
        if not self.font_manager:
            raise RuntimeError("Font manager not initialized")
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Searching by family/style: '{family_name}' / '{style_name}'")
        fonts = self.font_manager.db.search_font_by_family_and_style(family_name, style_name)
        logger.info(f"Family/style search returned {len(fonts)} results")
        
        if not fonts:
            raise ValueError(f"Font '{family_name} {style_name}' not found")
        
        if len(fonts) > 1:
            raise ValueError(f"Ambiguous font '{family_name} {style_name}' - {len(fonts)} matches found")
        
        font = fonts[0]
        logger.info(f"Activating font: {font['postscript_name']}")
        return self.font_manager.activate_font(font['id'])
    
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
        """Extract font PostScript names from Adobe document files by parsing the file content.
        .ai files are PDF-based and contain font entries in both XML metadata and PDF structures.
        .indd/.indt files contain XMP metadata with stFnt:fontName entries.
        .psd files contain font resource blocks.
        """
        font_names = set()
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in ('.ai', '.indd', '.indt'):
                # .ai and .indd files both contain XMP XML metadata with font info
                result = subprocess.run(
                    ['strings', file_path],
                    capture_output=True, text=True, timeout=10
                )
                content = result.stdout
                
                # Pattern 1: stFnt:fontName="PostScriptName" (XMP XML metadata)
                for match in re.finditer(r'stFnt:fontName="([^"]+)"', content):
                    font_names.add(match.group(1))
                
                # Also match <stFnt:fontName>PostScriptName</stFnt:fontName> (InDesign format)
                for match in re.finditer(r'<stFnt:fontName>([^<]+)</stFnt:fontName>', content):
                    font_names.add(match.group(1))
                
                # Pattern 2: /BaseFont/XXXXXX+PostScriptName or /BaseFont/PostScriptName
                # The XXXXXX+ prefix is a font subset indicator - strip it (PDF-based .ai only)
                for match in re.finditer(r'/BaseFont/([A-Z]{6}\+)?([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)', content):
                    name = match.group(2)
                    if name not in ('Symbol', 'ZapfDingbats', 'Identity-H'):
                        font_names.add(name)
                
                # Pattern 3: /FontName/XXXXXX+PostScriptName (font descriptors)
                for match in re.finditer(r'/FontName/([A-Z]{6}\+)?([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)', content):
                    name = match.group(2)
                    if name not in ('Symbol', 'ZapfDingbats', 'Identity-H'):
                        font_names.add(name)
            
            elif ext in ('.psd', '.psb'):
                # PSD/PSB files store font info in binary resource blocks
                # Try both ASCII and UTF-16 strings
                for encoding_args in [[], ['-e', 'l']]:
                    result = subprocess.run(
                        ['strings'] + encoding_args + [file_path],
                        capture_output=True, text=True, timeout=10
                    )
                    content = result.stdout
                    
                    # Look for font family names in PSD font resource blocks
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and len(line) > 2 and re.match(r'^[A-Z][a-z]', line):
                            if any(w in line.lower() for w in ['bold', 'italic', 'light', 'medium',
                                                                 'condensed', 'roman', 'regular',
                                                                 'black', 'heavy', 'thin', 'ultra']):
                                font_names.add(line)
            
            else:
                return []
        
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error extracting fonts from {file_path}: {e}")
            return []
        
        # Filter out common system/default fonts that don't need activation
        skip_fonts = {'ArialMT', 'TimesNewRomanPSMT', 'CourierNewPSMT',
                      'Arial-BoldMT', 'Arial-ItalicMT', 'Helvetica',
                      'Helvetica-Bold', 'Courier', 'Times-Roman',
                      'Symbol', 'ZapfDingbats'}
        
        return sorted(font_names - skip_fonts)


class RequestFileWatcher:
    """Watches for request files from Adobe scripts (Illustrator/Photoshop)
    that can't make HTTP requests and instead write .json files to disk."""
    
    REQUEST_DIR = os.path.expanduser("~/Library/Application Support/FontDock/requests")
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
                            data = json.load(f)
                        
                        file_path = data.get('file_path', '')
                        app_name = data.get('app', 'unknown')
                        font_names_from_app = data.get('font_names', [])
                        
                        logger.info(f"Request file watcher: processing {filename} from {app_name}")
                        logger.info(f"  File path: {file_path}")
                        
                        # Determine font names to activate:
                        # - Photoshop sends font_names directly (DOM works in PS)
                        # - Illustrator only sends file_path (DOM fails with GFKU)
                        font_names = []
                        if font_names_from_app:
                            font_names = font_names_from_app
                            logger.info(f"  Using {len(font_names)} font names from {app_name} DOM: {font_names}")
                        elif file_path and os.path.exists(file_path):
                            font_names = AdobeBridgeHandler.extract_fonts_from_file(file_path)
                            logger.info(f"  Extracted {len(font_names)} fonts from file: {font_names}")
                        else:
                            logger.warning(f"  No font names and file not found: {file_path}")
                        
                        if font_names:
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
    and auto-activates their fonts. Uses AppleScript to query open docs
    since Illustrator 2026 has no ExtendScript event system.
    
    Auto-detects installed Adobe app versions - no hardcoded version numbers."""
    
    POLL_INTERVAL = 5  # seconds between checks
    
    # App discovery config - no version numbers hardcoded
    APP_CONFIG = {
        'illustrator': {
            'app_folder_pattern': 'Adobe Illustrator*',
            'app_bundle_pattern': 'Adobe Illustrator*.app',
            'process_pattern': 'Adobe Illustrator',
            'extensions': ['.ai'],
            'doc_path_property': 'file path',  # AppleScript property for doc path
        },
        'indesign': {
            'app_folder_pattern': 'Adobe InDesign*',
            'app_bundle_pattern': 'Adobe InDesign*.app',
            'process_pattern': 'Adobe InDesign',
            'extensions': ['.indd', '.indt'],
            'doc_path_property': 'full name',  # InDesign uses 'full name' not 'file path'
        },
        'photoshop': {
            'app_folder_pattern': 'Adobe Photoshop*',
            'app_bundle_pattern': 'Adobe Photoshop*.app',
            'process_pattern': 'Adobe Photoshop',
            'extensions': ['.psd', '.psb'],
            'doc_path_property': 'file path',  # Photoshop uses 'file path'
        },
    }
    
    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager
        self.thread = None
        self._running = False
        self._known_docs = {}  # app_name -> set of file paths
        self._detected_apps = {}  # app_name -> {applescript_name, process_pattern, extensions}
        self._detect_installed_apps()
    
    def _detect_installed_apps(self):
        """Auto-detect installed Adobe apps and their AppleScript names.
        Scans /Applications for Adobe Illustrator/Photoshop installations."""
        import glob
        import logging
        logger = logging.getLogger(__name__)
        
        for app_name, config in self.APP_CONFIG.items():
            # Find the latest installed version
            app_folders = sorted(
                glob.glob(f'/Applications/{config["app_folder_pattern"]}'),
                reverse=True  # newest version first
            )
            
            if not app_folders:
                logger.info(f"App watcher: {app_name} not found in /Applications")
                continue
            
            # Use the latest version found
            latest_folder = app_folders[0]
            
            # Find the .app bundle inside
            app_bundles = sorted(
                glob.glob(f'{latest_folder}/{config["app_bundle_pattern"]}'),
                reverse=True
            )
            
            if not app_bundles:
                logger.info(f"App watcher: no .app bundle found in {latest_folder}")
                continue
            
            # Extract the AppleScript name from the app's Info.plist
            # This is the actual display/process name, which may include a version
            # e.g., Illustrator = "Adobe Illustrator", Photoshop = "Adobe Photoshop 2026"
            display_name = None
            try:
                info_plist = f'{app_bundles[0]}/Contents/Info.plist'
                if os.path.exists(info_plist):
                    result = subprocess.run(
                        ['defaults', 'read', info_plist, 'CFBundleDisplayName'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        display_name = result.stdout.strip()
            except:
                pass
            
            if not display_name:
                # Fallback: strip .app from bundle filename
                bundle_name = os.path.basename(app_bundles[0])
                display_name = bundle_name.replace('.app', '')
            
            self._detected_apps[app_name] = {
                'applescript_name': display_name,
                'process_pattern': config['process_pattern'],
                'extensions': config['extensions'],
                'doc_path_property': config['doc_path_property'],
                'bundle_path': app_bundles[0],
            }
            
            logger.info(f"App watcher: detected {app_name} -> {display_name} at {app_bundles[0]}")
        
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
        """Check if an Adobe app is running using System Events.
        Uses AppleScript System Events which does NOT launch apps,
        unlike 'tell application "X"' which does."""
        try:
            script = f'tell application "System Events" to (name of processes) contains "{applescript_name}"'
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and 'true' in result.stdout.lower()
        except:
            return False
    
    def _get_open_documents(self, app_name, app_info):
        """Query Adobe app for open document paths via AppleScript.
        Uses System Events to verify the app is running before targeting it,
        preventing accidental app launches."""
        try:
            as_name = app_info['applescript_name']
            doc_prop = app_info['doc_path_property']
            # Use System Events to check running first, then target the app
            # This prevents 'tell application "X"' from launching the app
            script = f'''
tell application "System Events"
    set isRunning to (name of processes) contains "{as_name}"
end tell
if isRunning then
    tell application "{as_name}"
        set docPaths to {{}}
        repeat with d in documents
            try
                set end of docPaths to ({doc_prop} of d) as text
            end try
        end repeat
        return docPaths
    end tell
else
    return {{}}
end if'''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return None
            
            output = result.stdout.strip()
            if not output:
                return []
            
            # Parse output - contains "file Macintosh HD:Users:..." entries
            # Also may contain stderr warnings on separate lines
            clean_paths = []
            for line in output.split('\n'):
                line = line.strip()
                # Look for Mac-style paths from file path output
                if 'Macintosh HD' in line:
                    # Extract the path part after "file "
                    idx = line.find('Macintosh HD')
                    mac_path = line[idx:]
                    # Convert Mac path to POSIX: Macintosh HD:Users:... -> /Users/...
                    posix = mac_path.replace('Macintosh HD:', '/', 1).replace(':', '/')
                    if os.path.exists(posix):
                        clean_paths.append(posix)
                elif line.startswith('/'):
                    if os.path.exists(line):
                        clean_paths.append(line)
            
            return clean_paths
        
        except subprocess.TimeoutExpired:
            return None
        except Exception:
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
        """Get font PostScript names from open Photoshop documents via AppleScript.
        Scans top-level text layers for their font property."""
        try:
            # Use document index instead of 'repeat with doc in documents'
            # which causes Internal Error 9999 in Photoshop AppleScript
            script = f'''
tell application "System Events"
    set isRunning to (name of processes) contains "{as_name}"
end tell
if isRunning then
    tell application "{as_name}"
        set fontNames to {{}}
        set docCount to count of documents
        repeat with d from 1 to docCount
            set layerCount to count of layers of document d
            repeat with i from 1 to layerCount
                try
                    set layerKind to kind of layer i of document d
                    if layerKind is text layer then
                        set fn to font of text object of layer i of document d as text
                        if fontNames does not contain fn then
                            set end of fontNames to fn
                        end if
                    end if
                end try
            end repeat
        end repeat
        return fontNames
    end tell
else
    return {{}}
end if'''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode != 0:
                return []
            
            output = result.stdout.strip()
            if not output or output == '':
                return []
            
            # Parse comma-separated font names from AppleScript output
            font_names = [f.strip() for f in output.split(',') if f.strip()]
            return font_names
        
        except Exception:
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
