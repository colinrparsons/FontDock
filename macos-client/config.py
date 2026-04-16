import os
import logging
import sys

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

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Logging initialized. Log file: {LOG_PATH}")
