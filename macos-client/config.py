import os
import logging
import sys
import re
from datetime import datetime, timedelta

# Import our local platform package (not Python's built-in platform module)
# sys.path[0] is the script directory, ensuring our platform/ is found first
if sys.platform == 'darwin':
    from fontdock_platform.macos import (
        get_app_support_dir,
        get_cache_dir,
        get_db_path,
        get_log_path,
    )
elif sys.platform == 'win32':
    from fontdock_platform.windows import (
        get_app_support_dir,
        get_cache_dir,
        get_db_path,
        get_log_path,
    )

APP_NAME = "FontDock"
LOCAL_API_PORT = 8765

# Read server URL from settings.json if available, otherwise use default
_SETTINGS_FILE = get_app_support_dir() / "settings.json"
if _SETTINGS_FILE.exists():
    try:
        import json as _json
        with open(_SETTINGS_FILE, 'r') as _f:
            _settings = _json.load(_f)
        SERVER_URL = _settings.get('server_url', 'http://localhost:9998')
    except Exception:
        SERVER_URL = 'http://localhost:9998'
else:
    SERVER_URL = 'http://localhost:9998'

APP_SUPPORT_DIR = get_app_support_dir()
CACHE_DIR = get_cache_dir()
DB_PATH = get_db_path()
LOG_PATH = get_log_path()

KEYRING_SERVICE = "FontDock"
KEYRING_USERNAME = "auth_token"

os.makedirs(APP_SUPPORT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

def _prune_old_log_entries(log_path, max_age_days=30):
    """Remove log entries older than max_age_days on startup."""
    if not os.path.exists(log_path):
        return
    
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
        
        cutoff = datetime.now() - timedelta(days=max_age_days)
        cutoff_str = cutoff.strftime('%Y-%m-%d')
        
        # Keep lines that are newer than cutoff, or non-timestamped lines
        kept = []
        for line in lines:
            # Log format: "2026-04-20 19:44:06,200 - ..."
            match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
            if match:
                if match.group(1) >= cutoff_str:
                    kept.append(line)
            else:
                kept.append(line)
        
        if len(kept) < len(lines):
            with open(log_path, 'w') as f:
                f.writelines(kept)
    except Exception:
        pass  # Don't crash if log pruning fails


def setup_logging():
    # Prune entries older than 30 days before setting up the handler
    _prune_old_log_entries(LOG_PATH, max_age_days=30)
    
    from logging.handlers import RotatingFileHandler
    
    # RotatingFileHandler: max 5MB per file, keep 1 backup
    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=5*1024*1024, backupCount=1
    )
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )
    logging.info(f"Logging initialized. Log file: {LOG_PATH}")
