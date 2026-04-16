"""Windows platform-specific implementations for FontDock client."""

import os
import re
import subprocess
import logging
import ctypes
import winreg
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================
# Path configuration
# ============================================================

def get_app_support_dir():
    """FontDock application support directory."""
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "FontDock"


def get_cache_dir():
    """Font cache directory."""
    return get_app_support_dir() / "cache" / "fonts"


def get_fonts_dir():
    """User fonts directory for activation.
    Windows 10 1803+ supports per-user fonts in this directory."""
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / "Microsoft" / "Windows" / "Fonts"


def get_db_path():
    """Local database path."""
    return get_app_support_dir() / "fontdock.db"


def get_log_path():
    """Log file path."""
    return get_app_support_dir() / "fontdock.log"


def get_request_dir():
    """Directory for Adobe script request files."""
    return str(get_app_support_dir() / "requests")


def get_adobe_startup_dir():
    """Base directory for Adobe startup scripts (version-independent)."""
    appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
    return os.path.join(appdata, 'Adobe', 'Startup Scripts CS6')


# ============================================================
# Font activation / deactivation (Windows-specific)
# ============================================================

def _register_font(filename, font_path):
    """Register a font in the Windows registry for per-user installation.
    This makes the font available to applications without admin rights."""
    try:
        # Determine font type for registry value name
        name_without_ext = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1].lower()
        
        # Registry value name format: "Font Name (TrueType)" or "Font Name (OpenType)"
        if ext in ('.ttf', '.ttc'):
            reg_name = f"{name_without_ext} (TrueType)"
        elif ext in ('.otf',):
            reg_name = f"{name_without_ext} (OpenType)"
        else:
            reg_name = f"{name_without_ext} (TrueType)"
        
        # Write to per-user fonts registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts',
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, reg_name, 0, winreg.REG_SZ, str(font_path))
        winreg.CloseKey(key)
        
        # Notify the system about the new font
        # This is equivalent to calling AddFontResource Win32 API
        try:
            gdi32 = ctypes.windll.gdi32
            gdi32.AddFontResourceW(str(font_path))
            # Broadcast WM_FONTCHANGE message
            user32 = ctypes.windll.user32
            user32.SendMessageTimeoutW(
                0xFFFF,  # HWND_BROADCAST
                0x001D,  # WM_FONTCHANGE
                0, 0, 0, 5000, None
            )
        except Exception as e:
            logger.warning(f"AddFontResource notification failed (font still copied): {e}")
        
        logger.info(f"Registered font in registry: {reg_name} -> {font_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to register font in registry: {e}")
        return False


def _unregister_font(filename):
    """Remove a font from the Windows registry."""
    try:
        name_without_ext = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in ('.ttf', '.ttc'):
            reg_name = f"{name_without_ext} (TrueType)"
        elif ext in ('.otf',):
            reg_name = f"{name_without_ext} (OpenType)"
        else:
            reg_name = f"{name_without_ext} (TrueType)"
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts',
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, reg_name)
        winreg.CloseKey(key)
        
        # Notify the system
        try:
            gdi32 = ctypes.windll.gdi32
            gdi32.RemoveFontResourceW(str(get_fonts_dir() / filename))
            user32 = ctypes.windll.user32
            user32.SendMessageTimeoutW(
                0xFFFF, 0x001D, 0, 0, 0, 5000, None
            )
        except Exception:
            pass
        
        logger.info(f"Unregistered font from registry: {reg_name}")
        return True
    
    except FileNotFoundError:
        logger.debug(f"Font not in registry: {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to unregister font: {e}")
        return False


# ============================================================
# Process / app detection (Windows)
# ============================================================

def is_app_running(process_name):
    """Check if an Adobe app is running using PowerShell Get-Process."""
    try:
        # Use PowerShell to check if process exists
        # -ErrorAction SilentlyContinue prevents errors if process not found
        result = subprocess.run(
            ['powershell', '-Command',
             f'Get-Process -Name "{process_name}" -ErrorAction SilentlyContinue | Select-Object -First 1'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and result.stdout.strip() != ''
    except Exception:
        return False


def get_open_documents(app_name, doc_path_property=None):
    """Query Adobe app for open document paths via COM automation.
    
    On Windows, Adobe apps expose COM interfaces that can be queried via PowerShell.
    This is the Windows equivalent of the AppleScript document querying on macOS.
    """
    try:
        # COM ProgIDs for Adobe apps
        COM_PROGIDS = {
            'illustrator': 'Illustrator.Application',
            'photoshop': 'Photoshop.Application',
            'indesign': 'InDesign.Application',
        }
        
        progid = COM_PROGIDS.get(app_name)
        if not progid:
            return []
        
        # Use PowerShell to query COM object for open documents
        script = f'''
try {{
    $app = [System.Runtime.InteropServices.Marshal]::GetActiveObject('{progid}')
    $docs = @()
    foreach ($doc in $app.Documents) {{
        try {{
            $docs += $doc.FullName
        }} catch {{}}
    }}
    $docs -join "`n"
}} catch {{
    # App not running or COM not available
}}
'''
        result = subprocess.run(
            ['powershell', '-Command', script],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout.strip()
        if not output:
            return []
        
        paths = [p.strip() for p in output.split('\n') if p.strip() and os.path.exists(p.strip())]
        return paths
    
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        logger.debug(f"COM document query failed for {app_name}: {e}")
        return None


def get_photoshop_font_names(app_name=None):
    """Get font PostScript names from open Photoshop documents via COM automation.
    
    Uses PowerShell to access the Photoshop COM object and scan text layers.
    This is the Windows equivalent of the AppleScript font scanning on macOS.
    """
    try:
        script = r'''
try {
    $ps = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Photoshop.Application')
    $fontNames = @()
    foreach ($doc in $ps.Documents) {
        foreach ($layer in $doc.Layers) {
            try {
                if ($layer.Kind -eq 2) {  # 2 = psTextLayer
                    $font = $layer.TextItem.Font
                    if ($fontNames -notcontains $font) {
                        $fontNames += $font
                    }
                }
            } catch {}
        }
    }
    $fontNames -join ","
} catch {}
'''
        result = subprocess.run(
            ['powershell', '-Command', script],
            capture_output=True, text=True, timeout=15
        )
        
        if result.returncode != 0:
            return []
        
        output = result.stdout.strip()
        if not output:
            return []
        
        font_names = [f.strip() for f in output.split(',') if f.strip()]
        return font_names
    
    except Exception as e:
        logger.debug(f"Photoshop COM font scan failed: {e}")
        return []


def detect_installed_apps():
    """Auto-detect installed Adobe apps on Windows.
    Scans Program Files and registry for Adobe installations.
    Returns dict: app_name -> {applescript_name, process_pattern, extensions, doc_path_property, bundle_path}"""
    
    APP_CONFIG = {
        'illustrator': {
            'process_pattern': 'Illustrator',
            'extensions': ['.ai'],
            'com_progids': ['Illustrator.Application'],
            'reg_key': r'SOFTWARE\Adobe\Illustrator',
        },
        'indesign': {
            'process_pattern': 'InDesign',
            'extensions': ['.indd', '.indt'],
            'com_progids': ['InDesign.Application'],
            'reg_key': r'SOFTWARE\Adobe\InDesign',
        },
        'photoshop': {
            'process_pattern': 'Photoshop',
            'extensions': ['.psd', '.psb'],
            'com_progids': ['Photoshop.Application'],
            'reg_key': r'SOFTWARE\Adobe\Photoshop',
        },
    }
    
    detected = {}
    
    for app_name, config in APP_CONFIG.items():
        # Check if app is installed by looking for COM ProgID in registry
        installed = False
        display_name = config['process_pattern']  # fallback
        
        try:
            # Check registry for installed Adobe apps
            key_path = config['reg_key']
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf'SOFTWARE\{key_path}', 0,
                                     winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                winreg.CloseKey(key)
                installed = True
            except FileNotFoundError:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf'SOFTWARE\WOW6432Node\{key_path}', 0,
                                         winreg.KEY_READ)
                    winreg.CloseKey(key)
                    installed = True
                except FileNotFoundError:
                    pass
            
            # Also check Program Files as fallback
            if not installed:
                program_files = os.environ.get('ProgramFiles', r'C:\Program Files')
                program_files_x86 = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
                
                for pf in [program_files, program_files_x86]:
                    adobe_dir = os.path.join(pf, 'Adobe')
                    if os.path.isdir(adobe_dir):
                        for entry in os.listdir(adobe_dir):
                            if app_name.capitalize() in entry:
                                installed = True
                                break
                    if installed:
                        break
        
        except Exception as e:
            logger.debug(f"Registry check failed for {app_name}: {e}")
        
        if installed:
            # Try to get the actual display name from the registry
            try:
                uninstall_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                    0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                )
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(uninstall_key, i)
                        subkey = winreg.OpenKey(uninstall_key, subkey_name)
                        try:
                            display_val = winreg.QueryValueEx(subkey, 'DisplayName')[0]
                            if app_name.capitalize() in display_val and 'Adobe' in display_val:
                                display_name = display_val
                                break
                        except FileNotFoundError:
                            pass
                        winreg.CloseKey(subkey)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(uninstall_key)
            except Exception:
                pass
            
            detected[app_name] = {
                'applescript_name': display_name,  # reused field name for cross-platform compat
                'process_pattern': config['process_pattern'],
                'extensions': config['extensions'],
                'doc_path_property': None,  # Windows uses COM, not AppleScript properties
                'bundle_path': None,
            }
            
            logger.info(f"App watcher: detected {app_name} -> {display_name}")
    
    return detected


# ============================================================
# Font extraction from files
# ============================================================

def extract_fonts_from_file(file_path):
    """Extract font PostScript names from Adobe document files.
    
    On Windows, we use Python's built-in file reading instead of the
    macOS `strings` command. Reads raw bytes and searches for patterns.
    """
    font_names = set()
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # Read file as bytes and decode to string for pattern matching
        with open(file_path, 'rb') as f:
            raw = f.read()
        
        # Try multiple encodings to extract readable strings
        content_parts = []
        
        # ASCII/Latin-1 strings
        try:
            ascii_strings = re.findall(rb'[\x20-\x7e]{4,}', raw)
            content_parts.append('\n'.join(s.decode('ascii', errors='ignore') for s in ascii_strings))
        except Exception:
            pass
        
        # UTF-16 strings (common in Adobe files)
        try:
            utf16_strings = re.findall(rb'(?:[\x20-\x7e]\x00){4,}', raw)
            content_parts.append('\n'.join(s.decode('utf-16-le', errors='ignore') for s in utf16_strings))
        except Exception:
            pass
        
        content = '\n'.join(content_parts)
        
        if ext in ('.ai', '.indd', '.indt'):
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
            # PSD font extraction - look for font family names in resource blocks
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
