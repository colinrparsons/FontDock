import os
import logging
from pathlib import Path

APP_NAME = "FontDock"
SERVER_URL = "http://localhost:9998"
LOCAL_API_PORT = 8765

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
CACHE_DIR = APP_SUPPORT_DIR / "cache" / "fonts"
DB_PATH = APP_SUPPORT_DIR / "fontdock.db"
LOG_PATH = APP_SUPPORT_DIR / "fontdock.log"

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
