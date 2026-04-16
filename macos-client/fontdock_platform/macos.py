"""macOS platform-specific implementations for FontDock client."""

import os
import re
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================
# Path configuration
# ============================================================

def get_app_support_dir():
    """FontDock application support directory."""
    return Path.home() / "Library" / "Application Support" / "FontDock"


def get_cache_dir():
    """Font cache directory."""
    return get_app_support_dir() / "cache" / "fonts"


def get_fonts_dir():
    """User fonts directory for activation."""
    return Path.home() / "Library" / "Fonts"


def get_db_path():
    """Local database path."""
    return get_app_support_dir() / "fontdock.db"


def get_log_path():
    """Log file path."""
    return get_app_support_dir() / "fontdock.log"


def get_request_dir():
    """Directory for Adobe script request files."""
    return os.path.expanduser("~/Library/Application Support/FontDock/requests")


def get_adobe_startup_dir():
    """Base directory for Adobe startup scripts (version-independent)."""
    return os.path.expanduser("~/Library/Application Support/Adobe/Startup Scripts CS6")


# ============================================================
# Process / app detection
# ============================================================

def is_app_running(applescript_name):
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
    except Exception:
        return False


def get_open_documents(applescript_name, doc_path_property):
    """Query Adobe app for open document paths via AppleScript.
    Uses System Events to verify the app is running before targeting it,
    preventing accidental app launches."""
    try:
        as_name = applescript_name
        doc_prop = doc_path_property
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
        clean_paths = []
        for line in output.split('\n'):
            line = line.strip()
            if 'Macintosh HD' in line:
                idx = line.find('Macintosh HD')
                mac_path = line[idx:]
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


def get_photoshop_font_names(applescript_name):
    """Get font PostScript names from open Photoshop documents via AppleScript.
    Scans top-level text layers for their font property."""
    try:
        as_name = applescript_name
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
        
        font_names = [f.strip() for f in output.split(',') if f.strip()]
        return font_names
    
    except Exception:
        return []


def detect_installed_apps():
    """Auto-detect installed Adobe apps and their AppleScript names.
    Scans /Applications for Adobe Illustrator/Photoshop/InDesign installations.
    Returns dict: app_name -> {applescript_name, process_pattern, extensions, doc_path_property, bundle_path}"""
    import glob
    
    APP_CONFIG = {
        'illustrator': {
            'app_folder_pattern': 'Adobe Illustrator*',
            'app_bundle_pattern': 'Adobe Illustrator*.app',
            'process_pattern': 'Adobe Illustrator',
            'extensions': ['.ai'],
            'doc_path_property': 'file path',
        },
        'indesign': {
            'app_folder_pattern': 'Adobe InDesign*',
            'app_bundle_pattern': 'Adobe InDesign*.app',
            'process_pattern': 'Adobe InDesign',
            'extensions': ['.indd', '.indt'],
            'doc_path_property': 'full name',
        },
        'photoshop': {
            'app_folder_pattern': 'Adobe Photoshop*',
            'app_bundle_pattern': 'Adobe Photoshop*.app',
            'process_pattern': 'Adobe Photoshop',
            'extensions': ['.psd', '.psb'],
            'doc_path_property': 'file path',
        },
    }
    
    detected = {}
    
    for app_name, config in APP_CONFIG.items():
        app_folders = sorted(
            glob.glob(f'/Applications/{config["app_folder_pattern"]}'),
            reverse=True
        )
        
        if not app_folders:
            logger.info(f"App watcher: {app_name} not found in /Applications")
            continue
        
        latest_folder = app_folders[0]
        app_bundles = sorted(
            glob.glob(f'{latest_folder}/{config["app_bundle_pattern"]}'),
            reverse=True
        )
        
        if not app_bundles:
            logger.info(f"App watcher: no .app bundle found in {latest_folder}")
            continue
        
        # Extract the AppleScript name from the app's Info.plist
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
        except Exception:
            pass
        
        if not display_name:
            bundle_name = os.path.basename(app_bundles[0])
            display_name = bundle_name.replace('.app', '')
        
        detected[app_name] = {
            'applescript_name': display_name,
            'process_pattern': config['process_pattern'],
            'extensions': config['extensions'],
            'doc_path_property': config['doc_path_property'],
            'bundle_path': app_bundles[0],
        }
        
        logger.info(f"App watcher: detected {app_name} -> {display_name} at {app_bundles[0]}")
    
    return detected


# ============================================================
# Font extraction from files
# ============================================================

def extract_fonts_from_file(file_path):
    """Extract font PostScript names from Adobe document files by parsing the file content.
    .ai files are PDF-based and contain font entries in both XML metadata and PDF structures.
    .indd/.indt files contain XMP metadata with stFnt:fontName entries.
    .psd files contain font resource blocks."""
    font_names = set()
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext in ('.ai', '.indd', '.indt'):
            result = subprocess.run(
                ['strings', file_path],
                capture_output=True, text=True, timeout=10
            )
            content = result.stdout
            
            # Pattern 1: stFnt:fontName="PostScriptName" (XMP XML metadata)
            for match in re.finditer(r'stFnt:fontName="([^"]+)"', content):
                font_names.add(match.group(1))
            
            # Also match <stFnt:fontName>PostScriptName</stFnt:fontName>
            for match in re.finditer(r'<stFnt:fontName>([^<]+)</stFnt:fontName>', content):
                font_names.add(match.group(1))
            
            # Pattern 2: /BaseFont/XXXXXX+PostScriptName or /BaseFont/PostScriptName
            for match in re.finditer(r'/BaseFont/([A-Z]{6}\+)?([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)', content):
                name = match.group(2)
                if name not in ('Symbol', 'ZapfDingbats', 'Identity-H'):
                    font_names.add(name)
            
            # Pattern 3: /FontName/XXXXXX+PostScriptName
            for match in re.finditer(r'/FontName/([A-Z]{6}\+)?([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)', content):
                name = match.group(2)
                if name not in ('Symbol', 'ZapfDingbats', 'Identity-H'):
                    font_names.add(name)
        
        elif ext in ('.psd', '.psb'):
            for encoding_args in [[], ['-e', 'l']]:
                result = subprocess.run(
                    ['strings'] + encoding_args + [file_path],
                    capture_output=True, text=True, timeout=10
                )
                content = result.stdout
                
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
        logger.error(f"Error extracting fonts from {file_path}: {e}")
        return []
    
    # Filter out common system/default fonts
    skip_fonts = {'ArialMT', 'TimesNewRomanPSMT', 'CourierNewPSMT',
                  'Arial-BoldMT', 'Arial-ItalicMT', 'Helvetica',
                  'Helvetica-Bold', 'Courier', 'Times-Roman',
                  'Symbol', 'ZapfDingbats'}
    
    return sorted(font_names - skip_fonts)
