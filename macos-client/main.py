#!/usr/bin/env python3
import sys
import logging
from PyQt5.QtWidgets import QApplication
from config import setup_logging
from gui import MainWindow
from api_client import FontDockAPI
from database import LocalDatabase
from font_manager import FontManager
from local_api import LocalAPIServer

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("FontDock Client starting...")
    api = FontDockAPI()
    db = LocalDatabase()
    font_manager = FontManager(api, db)
    
    local_api = LocalAPIServer(font_manager)
    local_api.start()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    exit_code = app.exec_()
    
    local_api.stop()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
