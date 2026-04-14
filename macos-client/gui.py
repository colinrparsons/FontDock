import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTabWidget, QListWidget,
    QMessageBox, QDialog, QFormLayout, QListWidgetItem, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from api_client import FontDockAPI
from database import LocalDatabase
from font_manager import FontManager
from config import APP_SUPPORT_DIR
from http_server import FontDockHTTPServer


class SyncThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, font_manager):
        super().__init__()
        self.font_manager = font_manager
    
    def run(self):
        try:
            result = self.font_manager.sync_metadata()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DownloadThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, font_manager):
        super().__init__()
        self.font_manager = font_manager
    
    def run(self):
        try:
            def progress_callback(current, total, filename):
                self.progress.emit(current, total, filename)
            
            result = self.font_manager.download_all_fonts(progress_callback)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ActivateThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, font_manager, font_id):
        super().__init__()
        self.font_manager = font_manager
        self.font_id = font_id
    
    def run(self):
        try:
            result = self.font_manager.activate_font(self.font_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FontDock Settings")
        self.setModal(True)
        self.setMinimumWidth(600)  # Make window wider
        self.setMinimumHeight(300)  # Make window taller
        self.settings_file = APP_SUPPORT_DIR / "settings.json"
        self.settings_saved = False
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        from PyQt5.QtWidgets import QSpinBox, QCheckBox
        from animated_toggle import AnimatedToggle
        layout = QFormLayout()
        
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://localhost:9998")
        self.server_url_input.setMinimumWidth(450)  # Wide enough for full text
        
        self.font_size_input = QSpinBox()
        self.font_size_input.setMinimum(8)
        self.font_size_input.setMaximum(72)
        self.font_size_input.setValue(14)
        self.font_size_input.setSuffix(" pt")
        
        self.app_font_size_input = QSpinBox()
        self.app_font_size_input.setMinimum(8)
        self.app_font_size_input.setMaximum(24)
        self.app_font_size_input.setValue(12)
        self.app_font_size_input.setSuffix(" pt")
        
        self.dark_mode_checkbox = QCheckBox()
        self.dark_mode_checkbox.setText("Enable Dark Mode")
        
        self.collapse_families_toggle = AnimatedToggle()
        collapse_layout = QHBoxLayout()
        collapse_label = QLabel("Collapse Families by Default")
        collapse_layout.addWidget(collapse_label)
        collapse_layout.addWidget(self.collapse_families_toggle)
        collapse_layout.addStretch()
        
        self.preview_text_input = QLineEdit()
        self.preview_text_input.setPlaceholderText("The quick brown fox jumps over the lazy dog")
        self.preview_text_input.setMinimumWidth(450)  # Wide enough for full sentence
        
        # Server URL with test button
        server_layout = QHBoxLayout()
        server_layout.addWidget(self.server_url_input)
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        server_layout.addWidget(self.test_button)
        
        layout.addRow("Server URL:", server_layout)
        layout.addRow("Font Preview Size:", self.font_size_input)
        layout.addRow("App Font Size:", self.app_font_size_input)
        layout.addRow("Preview Text:", self.preview_text_input)
        layout.addRow("", self.dark_mode_checkbox)
        layout.addRow("", collapse_layout)
        
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        
        # Make both buttons have the same appearance
        self.save_button.setAutoDefault(False)
        self.save_button.setDefault(False)
        
        self.save_button.clicked.connect(self.save_and_accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def load_settings(self):
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                self.server_url_input.setText(settings.get('server_url', 'http://localhost:9998'))
                self.font_size_input.setValue(settings.get('font_size', 14))
                self.app_font_size_input.setValue(settings.get('app_font_size', 12))
                self.preview_text_input.setText(settings.get('preview_text', 'The quick brown fox jumps over the lazy dog'))
                self.dark_mode_checkbox.setChecked(settings.get('dark_mode', False))
                self.collapse_families_toggle.setChecked(settings.get('collapse_families', True))
        else:
            self.server_url_input.setText('http://localhost:9998')
            self.font_size_input.setValue(14)
            self.app_font_size_input.setValue(12)
            self.preview_text_input.setText('The quick brown fox jumps over the lazy dog')
            self.dark_mode_checkbox.setChecked(False)
            self.collapse_families_toggle.setChecked(True)  # Default to collapsed
    
    def test_connection(self):
        """Test connection to server."""
        import requests
        server_url = self.server_url_input.text().strip()
        
        if not server_url:
            QMessageBox.warning(self, "Error", "Please enter a server URL")
            return
        
        try:
            # Test health endpoint
            response = requests.get(f"{server_url}/health", timeout=5)
            if response.status_code == 200:
                QMessageBox.information(
                    self, 
                    "Connection Successful", 
                    f"✓ Connected to FontDock server\n\nServer: {server_url}\nStatus: {response.json().get('status', 'unknown')}"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "Connection Failed", 
                    f"Server responded with status code: {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self, 
                "Connection Failed", 
                f"Cannot connect to server at:\n{server_url}\n\nPlease check:\n• Server is running\n• URL is correct\n• Network connection"
            )
        except requests.exceptions.Timeout:
            QMessageBox.critical(
                self, 
                "Connection Timeout", 
                f"Connection to server timed out:\n{server_url}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"Error connecting to server:\n{str(e)}"
            )
    
    def save_and_accept(self):
        settings = {
            'server_url': self.server_url_input.text(),
            'font_size': self.font_size_input.value(),
            'app_font_size': self.app_font_size_input.value(),
            'preview_text': self.preview_text_input.text(),
            'dark_mode': self.dark_mode_checkbox.isChecked(),
            'collapse_families': self.collapse_families_toggle.isChecked()
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Signal that settings were saved
        self.settings_saved = True
        self.accept()
    
    def get_server_url(self):
        return self.server_url_input.text()
    
    def get_font_size(self):
        return self.font_size_input.value()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FontDock Login")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.settings_file = APP_SUPPORT_DIR / "settings.json"
        self.setup_ui()
        self.load_server_url()
    
    def setup_ui(self):
        layout = QFormLayout()
        
        # Server URL with test button
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://192.168.0.48:8000")
        server_layout = QHBoxLayout()
        server_layout.addWidget(self.server_url_input)
        self.test_button = QPushButton("Test")
        self.test_button.clicked.connect(self.test_connection)
        server_layout.addWidget(self.test_button)
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        layout.addRow("Server URL:", server_layout)
        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.cancel_button = QPushButton("Cancel")
        
        self.login_button.clicked.connect(self.save_and_login)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def load_server_url(self):
        """Load server URL from settings."""
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                self.server_url_input.setText(settings.get('server_url', 'http://localhost:9998'))
        else:
            self.server_url_input.setText('http://localhost:9998')
    
    def test_connection(self):
        """Test connection to server."""
        import requests
        server_url = self.server_url_input.text().strip()
        
        if not server_url:
            QMessageBox.warning(self, "Error", "Please enter a server URL")
            return
        
        try:
            response = requests.get(f"{server_url}/health", timeout=5)
            if response.status_code == 200:
                QMessageBox.information(
                    self, 
                    "Connection Successful", 
                    f"✓ Connected to FontDock server\n\nServer: {server_url}\nStatus: {response.json().get('status', 'unknown')}"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "Connection Failed", 
                    f"Server responded with status code: {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self, 
                "Connection Failed", 
                f"Cannot connect to server at:\n{server_url}\n\nPlease check:\n• Server is running\n• URL is correct\n• Network connection"
            )
        except requests.exceptions.Timeout:
            QMessageBox.critical(
                self, 
                "Connection Timeout", 
                f"Connection to server timed out:\n{server_url}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"Error connecting to server:\n{str(e)}"
            )
    
    def save_and_login(self):
        """Save server URL and proceed with login."""
        server_url = self.server_url_input.text().strip()
        
        # Save server URL to settings
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        settings['server_url'] = server_url
        
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Update config
        import config
        config.SERVER_URL = server_url
        
        self.accept()
    
    def get_credentials(self):
        return self.username_input.text(), self.password_input.text()
    
    def get_server_url(self):
        return self.server_url_input.text().strip()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FontDock Client")
        self.setGeometry(100, 100, 1200, 800)
        
        # Load button icons
        from PyQt5.QtGui import QIcon
        assets_dir = Path(__file__).parent / "assets"
        self.add_icon = QIcon(str(assets_dir / "add.png"))
        self.delete_icon = QIcon(str(assets_dir / "delete.png"))
        
        # Create menu bar
        self.create_menu_bar()
        
        self.load_server_url()
        
        self.api = FontDockAPI()
        self.db = LocalDatabase()
        self.font_manager = FontManager(self.api, self.db)
        
        # Start HTTP server for InDesign integration
        self.http_server = FontDockHTTPServer(port=8765, callback=self.handle_indesign_request)
        self.http_server.start()
        
        # Apply settings (dark mode, font size)
        self.apply_settings()
        
        if not self.api.token:
            self.show_login()
        else:
            self.setup_ui()
            self.sync_metadata()
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        # Clear Cache action
        clear_cache_action = tools_menu.addAction('Clear Cache & Database')
        clear_cache_action.triggered.connect(self.clear_cache)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = help_menu.addAction('About FontDock')
        about_action.triggered.connect(self.show_about)
    
    def clear_cache(self):
        """Clear local cache and database."""
        reply = QMessageBox.question(
            self,
            'Clear Cache & Database',
            'This will delete all local font data and cache.\n\n'
            'You will need to sync again to download fonts.\n\n'
            'Are you sure you want to continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                import shutil
                import time
                
                # Clear authentication token
                self.api.clear_token()
                
                # Set db to None to release any references
                self.db = None
                
                # Give a moment for any pending operations to complete
                time.sleep(0.5)
                
                # Delete database file
                db_file = APP_SUPPORT_DIR / "fontdock.db"
                if db_file.exists():
                    db_file.unlink()
                
                # Delete cache directory
                cache_dir = APP_SUPPORT_DIR / "cache"
                if cache_dir.exists():
                    shutil.rmtree(cache_dir)
                
                QMessageBox.information(
                    self,
                    'Cache Cleared',
                    'Local cache, database, and login credentials have been cleared.\n\n'
                    'The application will now restart and you will need to login again.'
                )
                
                # Restart the application
                import sys
                from PyQt5.QtWidgets import QApplication
                QApplication.quit()
                os.execl(sys.executable, sys.executable, *sys.argv)
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    'Error',
                    f'Failed to clear cache:\n{str(e)}'
                )
    
    def show_about(self):
        """Show the About dialog."""
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("About FontDock")
        about_dialog.setFixedSize(450, 350)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)
        
        # Add top spacing
        layout.addSpacing(10)
        
        # Title
        title = QLabel("<h1 style='margin: 0;'>FontDock</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(5)
        
        # Version
        version = QLabel("<h3 style='margin: 0; font-weight: normal;'>Version 1.0.0</h3>")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        layout.addSpacing(30)
        
        # Description
        description = QLabel("Professional Font Management System")
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        layout.addSpacing(35)
        
        # Author
        author = QLabel("<b>Developed by:</b>")
        author.setAlignment(Qt.AlignCenter)
        layout.addWidget(author)
        
        layout.addSpacing(5)
        
        author_name = QLabel("Colin Parsons")
        author_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_name)
        
        layout.addSpacing(25)
        
        # Copyright
        copyright_text = QLabel("Copyright © 2026 Colin Parsons")
        copyright_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_text)
        
        layout.addSpacing(25)
        
        # License
        license_text = QLabel("<small>Licensed under the MIT License</small>")
        license_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_text)
        
        # Close button
        layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(about_dialog.accept)
        close_button.setFixedWidth(100)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addSpacing(10)
        
        about_dialog.setLayout(layout)
        about_dialog.exec_()
    
    def load_server_url(self):
        settings_file = APP_SUPPORT_DIR / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                server_url = settings.get('server_url', 'http://localhost:9998')
                import config
                config.SERVER_URL = server_url
    
    def get_font_preview_size(self):
        """Get font preview size from settings."""
        settings_file = APP_SUPPORT_DIR / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get('font_size', 14)
        return 14
    
    def get_collapse_families_setting(self):
        """Get collapse families by default setting."""
        settings_file = APP_SUPPORT_DIR / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get('collapse_families', True)
        return True  # Default to collapsed
    
    def get_preview_text(self):
        """Get preview text from settings."""
        settings_file = APP_SUPPORT_DIR / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get('preview_text', 'The quick brown fox jumps over the lazy dog')
        return 'The quick brown fox jumps over the lazy dog'
    
    def apply_settings(self):
        """Apply dark mode and app font size settings."""
        settings_file = APP_SUPPORT_DIR / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                
                # Apply dark mode
                dark_mode = settings.get('dark_mode', False)
                if dark_mode:
                    # Set application palette for selection colors
                    from PyQt5.QtGui import QPalette, QColor
                    palette = QPalette()
                    palette.setColor(QPalette.Highlight, QColor(0, 188, 212))  # Cyan
                    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
                    palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(0, 188, 212))
                    palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(255, 255, 255))
                    QApplication.instance().setPalette(palette)
                    
                    self.setStyleSheet("""
                        QMainWindow, QDialog, QWidget {
                            background-color: #1f1f1f;
                            color: #ffffff;
                        }
                        QListWidget {
                            background-color: #2a2a2a;
                            color: #ffffff;
                            border: 1px solid #3a3a3a;
                            outline: none;
                            selection-background-color: #4dd0e1;
                        }
                        QListWidget::item {
                            border: none;
                            padding: 2px;
                        }
                        QListWidget::item:selected {
                            background-color: #4dd0e1;
                            color: #ffffff;
                        }
                        QListWidget::item:selected:!active {
                            background-color: #4dd0e1;
                            color: #ffffff;
                        }
                        QListWidget::item:hover {
                            background-color: #26a69a;
                        }
                        QListWidget:focus {
                            outline: none;
                        }
                        QPushButton {
                            background-color: #00bcd4;
                            color: #ffffff;
                            border: none;
                            padding: 5px 15px;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #00acc1;
                        }
                        QLineEdit, QSpinBox {
                            background-color: #2a2a2a;
                            color: #ffffff;
                            border: 1px solid #3a3a3a;
                            padding: 5px;
                            border-radius: 4px;
                        }
                        QLineEdit:focus, QSpinBox:focus {
                            border: 1px solid rgba(0, 188, 212, 0.5);
                        }
                        QLabel {
                            color: #ffffff;
                        }
                        QTabWidget::pane {
                            background-color: #1f1f1f;
                            border: 1px solid #3a3a3a;
                        }
                        QTabBar::tab {
                            background-color: #2a2a2a;
                            color: #ffffff;
                            padding: 8px 16px;
                            border: 1px solid #3a3a3a;
                        }
                        QTabBar::tab:selected {
                            background-color: #00bcd4;
                        }
                        QStatusBar {
                            background-color: #2a2a2a;
                            color: #ffffff;
                        }
                    """)
                else:
                    self.setStyleSheet("")  # Reset to default
                
                # Apply app font size
                app_font_size = settings.get('app_font_size', 12)
                from PyQt5.QtGui import QFont
                app_font = QFont()
                app_font.setPointSize(app_font_size)
                QApplication.instance().setFont(app_font)
    
    def show_login(self):
        # Clear any existing token first to force fresh login
        self.api.clear_token()
        
        dialog = LoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Update server URL from login dialog
            server_url = dialog.get_server_url()
            self.api.server_url = server_url
            
            username, password = dialog.get_credentials()
            try:
                self.api.login(username, password)
                self.setup_ui()
                self.sync_metadata()
            except Exception as e:
                QMessageBox.critical(self, "Login Failed", str(e))
                # Clear token on failed login
                self.api.clear_token()
                self.close()
        else:
            self.close()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Add status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        top_bar = QHBoxLayout()
        
        # Add FontDock logo
        from PyQt5.QtSvg import QSvgWidget
        from PyQt5.QtCore import QByteArray
        logo_svg = QByteArray(b'''
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <rect width="40" height="40" rx="8" fill="#00bcd4"/>
            <text x="20" y="28" text-anchor="middle" fill="white" font-family="-apple-system, sans-serif" font-size="20" font-weight="bold">F</text>
            <path d="M28 12 L32 8 M28 12 L32 16" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
        ''')
        logo = QSvgWidget()
        logo.load(logo_svg)
        logo.setFixedSize(40, 40)
        top_bar.addWidget(logo)
        
        # Add FontDock title
        title_label = QLabel("FontDock")
        from PyQt5.QtGui import QFont
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        top_bar.addWidget(title_label)
        
        # Add spacer
        top_bar.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search fonts...")
        self.search_input.textChanged.connect(self.on_search)
        
        self.sync_button = QPushButton("Sync")
        self.sync_button.clicked.connect(self.sync_metadata)
        
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.show_settings)
        
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.on_logout)
        
        top_bar.addWidget(self.search_input)
        top_bar.addWidget(self.sync_button)
        top_bar.addWidget(self.settings_button)
        top_bar.addWidget(self.logout_button)
        
        layout.addLayout(top_bar)
        
        self.tabs = QTabWidget()
        
        self.fonts_tab = QWidget()
        self.collections_tab = QWidget()
        self.clients_tab = QWidget()
        self.recent_tab = QWidget()
        
        self.setup_fonts_tab()
        self.setup_collections_tab()
        self.setup_clients_tab()
        self.setup_recent_tab()
        
        self.tabs.addTab(self.fonts_tab, "Fonts")
        self.tabs.addTab(self.collections_tab, "Collections")
        self.tabs.addTab(self.clients_tab, "Clients")
        self.tabs.addTab(self.recent_tab, "Recent")
        
        # Refresh icons when switching tabs (to show fonts activated via InDesign)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        central_widget.setLayout(layout)
    
    def setup_fonts_tab(self):
        layout = QVBoxLayout()
        
        self.fonts_list = QListWidget()
        self.fonts_list.setSelectionMode(QListWidget.ExtendedSelection)  # Enable multi-select
        self.fonts_list.setSpacing(2)  # Add spacing between items
        self.fonts_list.itemDoubleClicked.connect(self.on_font_activate)
        
        button_layout = QHBoxLayout()
        activate_button = QPushButton(self.add_icon, "Activate Selected")
        activate_button.clicked.connect(self.on_font_activate_button)
        
        deactivate_button = QPushButton(self.delete_icon, "Deactivate Selected")
        deactivate_button.clicked.connect(self.on_font_deactivate_button)
        
        button_layout.addWidget(activate_button)
        button_layout.addWidget(deactivate_button)
        
        layout.addWidget(self.fonts_list)
        layout.addLayout(button_layout)
        
        self.fonts_tab.setLayout(layout)
        
        self.load_all_fonts()
    
    def setup_collections_tab(self):
        from PyQt5.QtWidgets import QSplitter
        layout = QVBoxLayout()
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Top section: Collections list
        collections_widget = QWidget()
        collections_layout = QVBoxLayout()
        collections_layout.addWidget(QLabel("Collections:"))
        self.collections_list = QListWidget()
        self.collections_list.setSpacing(2)  # Add spacing between items
        self.collections_list.itemClicked.connect(self.on_collection_selected)
        self.collections_list.setMaximumHeight(150)  # Compact height
        collections_layout.addWidget(self.collections_list)
        collections_widget.setLayout(collections_layout)
        
        # Bottom section: Collection fonts with family grouping
        fonts_widget = QWidget()
        fonts_layout = QVBoxLayout()
        fonts_layout.addWidget(QLabel("Fonts in Selected Collection:"))
        self.collection_fonts_list = QListWidget()
        self.collection_fonts_list.setSpacing(2)  # Add spacing between items
        self.collection_fonts_list.itemClicked.connect(self.on_collection_font_clicked)
        fonts_layout.addWidget(self.collection_fonts_list)
        
        button_layout = QHBoxLayout()
        activate_collection_button = QPushButton(self.add_icon, "Activate Collection")
        activate_collection_button.clicked.connect(self.on_collection_activate)
        deactivate_collection_button = QPushButton(self.delete_icon, "Deactivate Collection")
        deactivate_collection_button.clicked.connect(self.on_collection_deactivate)
        button_layout.addWidget(activate_collection_button)
        button_layout.addWidget(deactivate_collection_button)
        fonts_layout.addLayout(button_layout)
        
        fonts_widget.setLayout(fonts_layout)
        
        # Add to splitter
        splitter.addWidget(collections_widget)
        splitter.addWidget(fonts_widget)
        splitter.setStretchFactor(0, 1)  # Collections list gets less space
        splitter.setStretchFactor(1, 3)  # Fonts list gets more space
        
        layout.addWidget(splitter)
        self.collections_tab.setLayout(layout)
        
        self.load_collections()
    
    def setup_clients_tab(self):
        from PyQt5.QtWidgets import QSplitter
        layout = QVBoxLayout()
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)
        
        # Top section: Clients list
        clients_widget = QWidget()
        clients_layout = QVBoxLayout()
        clients_layout.addWidget(QLabel("Clients:"))
        self.clients_list = QListWidget()
        self.clients_list.setSpacing(2)  # Add spacing between items
        self.clients_list.itemClicked.connect(self.on_client_selected)
        self.clients_list.setMaximumHeight(150)  # Compact height
        clients_layout.addWidget(self.clients_list)
        clients_widget.setLayout(clients_layout)
        
        # Bottom section: Client fonts with family grouping
        fonts_widget = QWidget()
        fonts_layout = QVBoxLayout()
        fonts_layout.addWidget(QLabel("Fonts for Selected Client:"))
        self.client_fonts_list = QListWidget()
        self.client_fonts_list.setSpacing(2)  # Add spacing between items
        self.client_fonts_list.itemClicked.connect(self.on_client_font_clicked)
        fonts_layout.addWidget(self.client_fonts_list)
        
        button_layout = QHBoxLayout()
        activate_client_button = QPushButton(self.add_icon, "Activate Client")
        activate_client_button.clicked.connect(self.on_client_activate)
        deactivate_client_button = QPushButton(self.delete_icon, "Deactivate Client")
        deactivate_client_button.clicked.connect(self.on_client_deactivate)
        button_layout.addWidget(activate_client_button)
        button_layout.addWidget(deactivate_client_button)
        fonts_layout.addLayout(button_layout)
        
        fonts_widget.setLayout(fonts_layout)
        
        # Add to splitter
        splitter.addWidget(clients_widget)
        splitter.addWidget(fonts_widget)
        splitter.setStretchFactor(0, 1)  # Clients list gets less space
        splitter.setStretchFactor(1, 3)  # Fonts list gets more space
        
        layout.addWidget(splitter)
        self.clients_tab.setLayout(layout)
        
        self.load_clients()
    
    def setup_recent_tab(self):
        layout = QVBoxLayout()
        
        self.recent_list = QListWidget()
        
        layout.addWidget(QLabel("Recently Activated:"))
        layout.addWidget(self.recent_list)
        
        self.recent_tab.setLayout(layout)
        
        self.load_recent()
    
    def load_all_fonts(self):
        """Load all fonts grouped by family with preview text."""
        # Check if families should be collapsed by default
        collapse_by_default = self.get_collapse_families_setting()
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, postscript_name, style_name, family_name, filename_original, extension, cached_path
            FROM fonts 
            ORDER BY family_name, style_name
        """)
        
        from collections import defaultdict
        from PyQt5.QtGui import QFont, QFontDatabase
        families = defaultdict(list)
        
        for row in cursor.fetchall():
            font_id, ps_name, style_name, family_name, filename, extension, cached_path = row
            family = family_name or 'Unknown Family'
            families[family].append({
                'id': font_id,
                'ps_name': ps_name,
                'style_name': style_name,
                'filename': filename,
                'extension': extension,
                'cached_path': cached_path
            })
        
        conn.close()
        
        # Track loaded fonts to avoid duplicates
        loaded_fonts = {}
        
        self.fonts_list.clear()
        for family_name in sorted(families.keys()):
            fonts = families[family_name]
            format_type = 'TrueType' if fonts[0]['extension'] in ['.ttf', '.ttc'] else 'OpenType' if fonts[0]['extension'] == '.otf' else 'Unknown'
            
            family_item = QListWidgetItem(f"▶ {family_name} ({len(fonts)} styles) - {format_type}")
            family_item.setData(Qt.UserRole, None)
            family_item.setData(Qt.UserRole + 1, family_name)
            family_item.setBackground(Qt.lightGray)
            self.fonts_list.addItem(family_item)
            
            for font in fonts:
                style = font['style_name'] or 'Regular'
                font_format = 'TrueType' if font['extension'] in ['.ttf', '.ttc'] else 'OpenType' if font['extension'] == '.otf' else font['extension']
                
                # Check if font is activated (exists in ~/Library/Fonts/)
                user_fonts_dir = Path.home() / "Library" / "Fonts"
                is_activated = (user_fonts_dir / font['filename']).exists()
                
                # Create preview text in actual font with consistent indentation
                preview_text = self.get_preview_text()
                item_text = f"    {preview_text}    {style}    {font_format}"
                item = QListWidgetItem(item_text)
                
                # Add status icon
                from PyQt5.QtGui import QIcon
                icon_path = "assets/active.svg" if is_activated else "assets/inactive.svg"
                if os.path.exists(icon_path):
                    item.setIcon(QIcon(icon_path))
                
                item.setData(Qt.UserRole, font['id'])
                item.setData(Qt.UserRole + 1, None)
                item.setData(Qt.UserRole + 2, font['cached_path'])
                
                # Load and apply the actual font if cached
                if font['cached_path'] and os.path.exists(font['cached_path']):
                    # Load each font file (Qt handles duplicates internally)
                    font_id_qt = QFontDatabase.addApplicationFont(font['cached_path'])
                    if font_id_qt != -1:
                        # Get all font families from this file
                        font_families_qt = QFontDatabase.applicationFontFamilies(font_id_qt)
                        if font_families_qt:
                            font_size = self.get_font_preview_size()
                            # Use the first family from the file
                            custom_font = QFont(font_families_qt[0], font_size)
                            
                            # Set the exact style using PostScript name if available
                            if font['ps_name']:
                                # Try to use the PostScript name for exact matching
                                custom_font.setFamily(font_families_qt[0])
                                custom_font.setStyleName(style)
                            
                            item.setFont(custom_font)
                
                # Hide based on setting (True = collapsed, False = expanded)
                self.fonts_list.addItem(item)
                item.setHidden(collapse_by_default)
        
        # Disconnect and reconnect to avoid duplicate connections
        try:
            self.fonts_list.itemClicked.disconnect(self.on_font_list_clicked)
        except:
            pass
        self.fonts_list.itemClicked.connect(self.on_font_list_clicked)
    
    def on_search(self, text):
        if len(text) == 0:
            self.load_all_fonts()
            return
        
        if len(text) < 2:
            return
        
        results = self.db.search_fonts(text)
        self.fonts_list.clear()
        
        for font in results:
            item_text = f"{font.get('postscript_name', 'Unknown')} - {font.get('family_name', 'Unknown Family')}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, font['id'])
            self.fonts_list.addItem(item)
    
    def on_font_list_clicked(self, item):
        """Toggle family expansion when clicking family header."""
        family_name = item.data(Qt.UserRole + 1)
        if family_name:
            # Check if Cmd/Ctrl is held for activation/deactivation
            from PyQt5.QtWidgets import QApplication
            modifiers = QApplication.keyboardModifiers()
            from PyQt5.QtCore import Qt as QtCore
            
            if modifiers & QtCore.ControlModifier or modifiers & QtCore.MetaModifier:
                # Cmd/Ctrl+Click on family = activate/deactivate all fonts in family
                self.toggle_family_activation(item)
            else:
                # Normal click = expand/collapse
                is_expanded = item.text().startswith("▼")
                new_icon = "▶" if is_expanded else "▼"
                item.setText(item.text().replace("▶" if not is_expanded else "▼", new_icon, 1))
                
                current_index = self.fonts_list.row(item)
                i = current_index + 1
                while i < self.fonts_list.count():
                    next_item = self.fonts_list.item(i)
                    if next_item.data(Qt.UserRole + 1):
                        break
                    next_item.setHidden(is_expanded)
                    i += 1
    
    def toggle_family_activation(self, family_item):
        """Activate or deactivate all fonts in a family."""
        family_name = family_item.data(Qt.UserRole + 1)
        if not family_name:
            return
        
        # Collect all font IDs in this family
        font_ids = []
        current_index = self.fonts_list.row(family_item)
        i = current_index + 1
        while i < self.fonts_list.count():
            next_item = self.fonts_list.item(i)
            if next_item.data(Qt.UserRole + 1):  # Hit next family
                break
            font_id = next_item.data(Qt.UserRole)
            if font_id:
                font_ids.append(font_id)
            i += 1
        
        if not font_ids:
            return
        
        # Check if any are active
        any_active = any(self.font_manager.is_font_active(fid) for fid in font_ids)
        
        try:
            if any_active:
                # Deactivate all
                for font_id in font_ids:
                    self.font_manager.deactivate_font(font_id)
                self.status_bar.showMessage(f"Deactivated {len(font_ids)} fonts in {family_name}", 3000)
            else:
                # Activate all
                for font_id in font_ids:
                    self.font_manager.activate_font(font_id)
                self.status_bar.showMessage(f"Activated {len(font_ids)} fonts in {family_name}", 3000)
            
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}", 5000)
    
    def on_font_activate(self, item=None):
        """Toggle font activation/deactivation on double-click."""
        if not item:
            item = self.fonts_list.currentItem()
        
        if not item:
            return
        
        font_id = item.data(Qt.UserRole)
        if not font_id:
            return
        
        # Check if font is already active
        is_active = self.font_manager.is_font_active(font_id)
        
        if is_active:
            # Deactivate
            try:
                result = self.font_manager.deactivate_font(font_id)
                self.status_bar.showMessage(result.get('message', 'Font deactivated'), 3000)
                self.reload_all_tabs()  # Reload all tabs to sync status
            except Exception as e:
                QMessageBox.critical(self, "Deactivation Failed", str(e))
        else:
            # Activate
            self.activate_thread = ActivateThread(self.font_manager, font_id)
            self.activate_thread.finished.connect(self.on_activate_finished)
            self.activate_thread.error.connect(self.on_activate_error)
            self.activate_thread.start()
            
            self.progress = QProgressDialog("Activating font...", None, 0, 0, self)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.show()
    
    def on_font_activate_button(self):
        """Activate selected font(s) or family (button click)."""
        selected_items = self.fonts_list.selectedItems()
        if not selected_items:
            return
        
        # Collect all font IDs from selected items (including fonts within selected families)
        font_ids = []
        for item in selected_items:
            family_name = item.data(Qt.UserRole + 1)
            if family_name:
                # This is a family header - get all fonts in this family
                current_index = self.fonts_list.row(item)
                i = current_index + 1
                while i < self.fonts_list.count():
                    next_item = self.fonts_list.item(i)
                    if next_item.data(Qt.UserRole + 1):  # Hit next family
                        break
                    font_id = next_item.data(Qt.UserRole)
                    if font_id:
                        font_ids.append(font_id)
                    i += 1
            else:
                # This is an individual font
                font_id = item.data(Qt.UserRole)
                if font_id:
                    font_ids.append(font_id)
        
        if not font_ids:
            self.status_bar.showMessage("No fonts to activate", 3000)
            return
        
        # Activate all selected fonts
        try:
            activated = 0
            for font_id in font_ids:
                self.font_manager.activate_font(font_id)
                activated += 1
            
            self.status_bar.showMessage(f"Activated {activated} font(s)", 3000)
            self.load_recent()
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Activation failed: {str(e)}", 5000)
    
    def on_font_deactivate_button(self):
        """Deactivate selected font(s) or family (button click)."""
        selected_items = self.fonts_list.selectedItems()
        if not selected_items:
            return
        
        # Collect all font IDs from selected items (including fonts within selected families)
        font_ids = []
        for item in selected_items:
            family_name = item.data(Qt.UserRole + 1)
            if family_name:
                # This is a family header - get all fonts in this family
                current_index = self.fonts_list.row(item)
                i = current_index + 1
                while i < self.fonts_list.count():
                    next_item = self.fonts_list.item(i)
                    if next_item.data(Qt.UserRole + 1):  # Hit next family
                        break
                    font_id = next_item.data(Qt.UserRole)
                    if font_id:
                        font_ids.append(font_id)
                    i += 1
            else:
                # This is an individual font
                font_id = item.data(Qt.UserRole)
                if font_id:
                    font_ids.append(font_id)
        
        if not font_ids:
            self.status_bar.showMessage("No fonts to deactivate", 3000)
            return
        
        # Deactivate all selected fonts
        try:
            deactivated = 0
            for font_id in font_ids:
                self.font_manager.deactivate_font(font_id)
                deactivated += 1
            
            self.status_bar.showMessage(f"Deactivated {deactivated} font(s)", 3000)
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Deactivation failed: {str(e)}", 5000)
    
    def on_activate_finished(self, result):
        self.progress.close()
        self.status_bar.showMessage(result.get('message', 'Font activated'), 3000)
        self.load_recent()
        # Reload all tabs to sync activation status
        self.reload_all_tabs()
    
    def on_activate_error(self, error):
        self.progress.close()
        QMessageBox.critical(self, "Activation Failed", error)
    
    def reload_all_tabs(self):
        """Reload all tabs to sync activation status across the UI."""
        # Get current tab index to avoid disrupting the active tab
        current_tab_index = self.tabs.currentIndex()
        
        # Tab indices: 0=Fonts, 1=Collections, 2=Clients, 3=Recent
        
        # Always reload Fonts tab (index 0)
        if current_tab_index != 0:
            self.load_all_fonts()
        else:
            # If Fonts tab is active, just update icons without rebuilding
            self.update_fonts_tab_icons()
        
        # Reload Collections tab if a collection is selected (index 1)
        if current_tab_index != 1:
            current_collection = self.collections_list.currentItem()
            if current_collection:
                self.on_collection_selected(current_collection)
        else:
            # If Collections tab is active, just update icons
            self.update_collection_fonts_icons()
        
        # Reload Clients tab if a client is selected (index 2)
        if current_tab_index != 2:
            current_client = self.clients_list.currentItem()
            if current_client:
                self.on_client_selected(current_client)
        else:
            # If Clients tab is active, just update icons
            self.update_client_fonts_icons()
    
    def on_tab_changed(self, index):
        """Refresh icons when switching tabs to show updated activation status."""
        tab_name = self.tabs.tabText(index)
        if tab_name == "Fonts":
            self.update_fonts_tab_icons()
        elif tab_name == "Collections":
            self.update_collection_fonts_icons()
        elif tab_name == "Clients":
            self.update_client_fonts_icons()
    
    def update_fonts_tab_icons(self):
        """Update only the activation icons in Fonts tab without rebuilding."""
        from PyQt5.QtGui import QIcon
        active_icon_path = Path(__file__).parent / "assets" / "active.svg"
        inactive_icon_path = Path(__file__).parent / "assets" / "inactive.svg"
        active_icon = QIcon(str(active_icon_path))
        inactive_icon = QIcon(str(inactive_icon_path))
        
        for i in range(self.fonts_list.count()):
            item = self.fonts_list.item(i)
            font_id = item.data(Qt.UserRole)
            if font_id:  # Only update actual fonts, not family headers
                is_active = self.font_manager.is_font_active(font_id)
                item.setIcon(active_icon if is_active else inactive_icon)
    
    def update_collection_fonts_icons(self):
        """Update only the activation icons in Collections tab without rebuilding."""
        from PyQt5.QtGui import QIcon
        active_icon_path = Path(__file__).parent / "assets" / "active.svg"
        inactive_icon_path = Path(__file__).parent / "assets" / "inactive.svg"
        active_icon = QIcon(str(active_icon_path))
        inactive_icon = QIcon(str(inactive_icon_path))
        
        for i in range(self.collection_fonts_list.count()):
            item = self.collection_fonts_list.item(i)
            item_type = item.data(Qt.UserRole + 1)
            if item_type == 'font':
                font_id = item.data(Qt.UserRole)
                if font_id:
                    is_active = self.font_manager.is_font_active(font_id)
                    item.setIcon(active_icon if is_active else inactive_icon)
    
    def update_client_fonts_icons(self):
        """Update only the activation icons in Clients tab without rebuilding."""
        from PyQt5.QtGui import QIcon
        active_icon_path = Path(__file__).parent / "assets" / "active.svg"
        inactive_icon_path = Path(__file__).parent / "assets" / "inactive.svg"
        active_icon = QIcon(str(active_icon_path))
        inactive_icon = QIcon(str(inactive_icon_path))
        
        for i in range(self.client_fonts_list.count()):
            item = self.client_fonts_list.item(i)
            font_id = item.data(Qt.UserRole)
            if font_id:  # Only update actual fonts, not family headers
                is_active = self.font_manager.is_font_active(font_id)
                item.setIcon(active_icon if is_active else inactive_icon)
    
    def load_clients(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM clients ORDER BY name")
        clients = cursor.fetchall()
        conn.close()
        
        self.clients_list.clear()
        for client_id, name in clients:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, client_id)
            self.clients_list.addItem(item)
    
    def on_client_selected(self, item):
        client_id = item.data(Qt.UserRole)
        client_name = item.text()
        
        try:
            import requests
            from collections import defaultdict
            from PyQt5.QtGui import QFont, QFontDatabase
            
            # Check if families should be collapsed by default
            collapse_by_default = self.get_collapse_families_setting()
            
            # Fetch fonts from the client_fonts association table
            response = requests.get(
                f"{self.api.server_url}/api/fonts",
                params={"page_size": 1000},
                headers=self.api.get_headers()
            )
            response.raise_for_status()
            data = response.json()
            all_fonts = data.get('items', [])
            
            # Filter fonts that have this client_id in their clients array
            client_fonts = [f for f in all_fonts if client_id in f.get('client_ids', [])]
            
            self.client_fonts_list.clear()
            if not client_fonts:
                self.client_fonts_list.addItem(f"No fonts assigned to {client_name}")
                return
            
            # Group by family
            families = defaultdict(list)
            for font in client_fonts:
                family = font.get('family_name', 'Unknown Family')
                families[family].append(font)
            
            # Display with family grouping
            for family_name in sorted(families.keys()):
                fonts = families[family_name]
                ext = fonts[0].get('extension', '')
                format_type = 'TrueType' if ext in ['.ttf', '.ttc'] else 'OpenType' if ext == '.otf' else 'Unknown'
                
                # Family header
                family_item = QListWidgetItem(f"▶ {family_name} ({len(fonts)} styles) - {format_type}")
                family_item.setData(Qt.UserRole, None)
                family_item.setData(Qt.UserRole + 1, family_name)
                family_item.setBackground(Qt.lightGray)
                self.client_fonts_list.addItem(family_item)
                
                # Font styles
                for font in fonts:
                    # Get cached path from local DB
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT cached_path FROM fonts WHERE id = ?", (font['id'],))
                    result = cursor.fetchone()
                    conn.close()
                    
                    cached_path = result[0] if result else None
                    style = font.get('style_name', 'Regular')
                    font_format = 'TrueType' if ext in ['.ttf', '.ttc'] else 'OpenType' if ext == '.otf' else ext
                    
                    # Check if font is activated
                    user_fonts_dir = Path.home() / "Library" / "Fonts"
                    filename = font.get('filename_original', '')
                    is_activated = (user_fonts_dir / filename).exists() if filename else False
                    
                    preview_text = self.get_preview_text()
                    item_text = f"{preview_text}    {style}    {font_format}"
                    font_item = QListWidgetItem(item_text)
                    
                    # Add status icon
                    from PyQt5.QtGui import QIcon
                    icon_path = "assets/active.svg" if is_activated else "assets/inactive.svg"
                    if os.path.exists(icon_path):
                        font_item.setIcon(QIcon(icon_path))
                    
                    font_item.setData(Qt.UserRole, font['id'])
                    font_item.setData(Qt.UserRole + 1, None)
                    
                    # Apply font preview if cached
                    if cached_path and os.path.exists(cached_path):
                        font_id_qt = QFontDatabase.addApplicationFont(cached_path)
                        if font_id_qt != -1:
                            font_families_qt = QFontDatabase.applicationFontFamilies(font_id_qt)
                            if font_families_qt:
                                font_size = self.get_font_preview_size()
                                custom_font = QFont(font_families_qt[0], font_size)
                                custom_font.setStyleName(style)
                                font_item.setFont(custom_font)
                    
                    self.client_fonts_list.addItem(font_item)
                    font_item.setHidden(collapse_by_default)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load client fonts: {str(e)}")
    
    def on_client_font_clicked(self, item):
        """Toggle family expansion when clicking family header in client fonts."""
        family_name = item.data(Qt.UserRole + 1)
        if family_name:
            is_expanded = item.text().startswith("▼")
            new_icon = "▶" if is_expanded else "▼"
            item.setText(item.text().replace("▶" if not is_expanded else "▼", new_icon, 1))
            
            current_index = self.client_fonts_list.row(item)
            i = current_index + 1
            while i < self.client_fonts_list.count():
                next_item = self.client_fonts_list.item(i)
                if next_item.data(Qt.UserRole + 1):
                    break
                next_item.setHidden(is_expanded)
                i += 1
    
    def on_client_activate(self):
        """Activate all fonts for the selected client."""
        current_item = self.clients_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Client Selected", "Please select a client first")
            return
        
        client_name = current_item.text()
        
        # Get all font IDs for this client
        font_ids = []
        for i in range(self.client_fonts_list.count()):
            font_id = self.client_fonts_list.item(i).data(Qt.UserRole)
            if font_id:  # Skip family headers (they have None as font_id)
                font_ids.append(font_id)
        
        if not font_ids:
            QMessageBox.information(self, "No Fonts", f"No fonts assigned to {client_name}")
            return
        
        try:
            activated = 0
            for font_id in font_ids:
                self.font_manager.activate_font(font_id)
                activated += 1
            
            self.status_bar.showMessage(f"Activated {activated} fonts for {client_name}", 3000)
            self.load_recent()
            # Reload all tabs to sync status
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Activation failed: {str(e)}", 5000)
    
    def on_client_deactivate(self):
        """Deactivate all fonts for the selected client."""
        current_item = self.clients_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Client Selected", "Please select a client first")
            return
        
        client_name = current_item.text()
        
        # Get all font IDs for this client
        font_ids = []
        for i in range(self.client_fonts_list.count()):
            font_id = self.client_fonts_list.item(i).data(Qt.UserRole)
            if font_id:  # Skip family headers (they have None as font_id)
                font_ids.append(font_id)
        
        if not font_ids:
            QMessageBox.information(self, "No Fonts", f"No fonts assigned to {client_name}")
            return
        
        try:
            deactivated = 0
            for font_id in font_ids:
                self.font_manager.deactivate_font(font_id)
                deactivated += 1
            
            self.status_bar.showMessage(f"Deactivated {deactivated} fonts for {client_name}", 3000)
            # Reload all tabs to sync status
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Deactivation failed: {str(e)}", 5000)
    
    def load_collections(self):
        collections = self.db.get_all_collections()
        self.collections_list.clear()
        
        for collection in collections:
            item = QListWidgetItem(collection['name'])
            item.setData(Qt.UserRole, collection['id'])
            self.collections_list.addItem(item)
    
    def on_collection_selected(self, item):
        collection_id = item.data(Qt.UserRole)
        collection_name = item.text()
        
        self.collection_fonts_list.clear()
        
        # Get collection's client
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_id FROM collections WHERE id = ?
        """, (collection_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            # No client assigned, show fonts directly grouped by family
            cursor.execute("""
                SELECT f.id, f.postscript_name, f.style_name, f.family_name
                FROM fonts f
                JOIN collection_fonts cf ON f.id = cf.font_id
                WHERE cf.collection_id = ?
                ORDER BY family_name, style_name
            """, (collection_id,))
            fonts = cursor.fetchall()
            conn.close()
            
            if not fonts:
                return
            
            self._show_fonts_by_family(fonts)
            return
        
        client_id = result[0]
        
        # Get client name
        cursor.execute("SELECT name FROM clients WHERE id = ?", (client_id,))
        client_result = cursor.fetchone()
        client_name = client_result[0] if client_result else "Unknown Client"
        conn.close()
        
        # Show client as a collapsible header
        from PyQt5.QtGui import QFont
        client_item = QListWidgetItem(f"▶ {client_name}")
        client_item.setData(Qt.UserRole, None)
        client_item.setData(Qt.UserRole + 1, 'client')  # Mark as client header
        client_item.setData(Qt.UserRole + 2, client_id)  # Store client ID
        client_item.setData(Qt.UserRole + 3, collection_id)  # Store collection ID
        font = QFont()
        font.setBold(True)
        client_item.setFont(font)
        self.collection_fonts_list.addItem(client_item)
    
    def _show_fonts_by_family(self, fonts):
        """Helper to show fonts grouped by family"""
        try:
            from collections import defaultdict
            from PyQt5.QtGui import QFont, QIcon
            
            # Check if families should be collapsed by default
            collapse_by_default = self.get_collapse_families_setting()
            
            # Group fonts by family
            families = defaultdict(list)
            for font in fonts:
                family_name = font[3] or 'Unknown'
                families[family_name].append(font)
            
            # Load SVG icons
            active_icon = QIcon(str(Path(__file__).parent / "assets" / "active.svg"))
            inactive_icon = QIcon(str(Path(__file__).parent / "assets" / "inactive.svg"))
            
            # Add family groups
            for family_name in sorted(families.keys()):
                family_fonts = families[family_name]
                
                # Add family header
                family_item = QListWidgetItem(f"    ▶ {family_name} ({len(family_fonts)} styles)")
                family_item.setData(Qt.UserRole, None)
                family_item.setData(Qt.UserRole + 1, 'family')  # Mark as family header
                family_item.setData(Qt.UserRole + 2, family_name)  # Store family name
                font = QFont()
                font.setBold(True)
                family_item.setFont(font)
                family_item.setHidden(collapse_by_default)
                self.collection_fonts_list.addItem(family_item)
                
                # Add individual fonts (initially hidden)
                for font_data in family_fonts:
                    font_id, postscript_name, style_name, _ = font_data
                    is_active = self.font_manager.is_font_active(font_id)
                    
                    # Use status icon
                    icon = active_icon if is_active else inactive_icon
                    
                    font_item = QListWidgetItem(icon, f"        {style_name or postscript_name or 'Unknown'}")
                    font_item.setData(Qt.UserRole, font_id)
                    font_item.setData(Qt.UserRole + 1, 'font')  # Mark as font
                    font_item.setData(Qt.UserRole + 2, family_name)  # Store family name
                    font_item.setHidden(collapse_by_default)
                    
                    # Apply font preview size from settings
                    font = QFont()
                    font.setPointSize(self.get_font_preview_size())
                    font_item.setFont(font)
                    
                    self.collection_fonts_list.addItem(font_item)
        
        except Exception as e:
            self.status_bar.showMessage(f"Error loading fonts: {str(e)}", 5000)
    
    def on_collection_font_clicked(self, item):
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type == 'client':
            # Toggle client expansion - load and show families
            client_id = item.data(Qt.UserRole + 2)
            collection_id = item.data(Qt.UserRole + 3)
            client_name = item.text().strip().replace("▶ ", "").replace("▼ ", "")
            is_expanded = item.text().strip().startswith("▼")
            
            # Update header icon
            if is_expanded:
                # Collapse - remove all families and fonts, just show client
                item.setText(f"▶ {client_name}")
                # Remove all items except the client header
                items_to_remove = []
                for i in range(self.collection_fonts_list.count()):
                    list_item = self.collection_fonts_list.item(i)
                    if list_item != item:
                        items_to_remove.append(i)
                
                # Remove in reverse order to maintain indices
                for i in reversed(items_to_remove):
                    self.collection_fonts_list.takeItem(i)
            else:
                # Expand - load and show families
                item.setText(f"▼ {client_name}")
                
                # Load fonts for this collection
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f.id, f.postscript_name, f.style_name, f.family_name
                    FROM fonts f
                    JOIN collection_fonts cf ON f.id = cf.font_id
                    WHERE cf.collection_id = ?
                    ORDER BY family_name, style_name
                """, (collection_id,))
                fonts = cursor.fetchall()
                conn.close()
                
                print(f"DEBUG: Found {len(fonts)} fonts for collection {collection_id}")
                
                if fonts:
                    # Add fonts grouped by family
                    from collections import defaultdict
                    from PyQt5.QtGui import QFont, QIcon
                    
                    families = defaultdict(list)
                    for font in fonts:
                        family_name = font[3] or 'Unknown'
                        families[family_name].append(font)
                    
                    # Load SVG icons
                    active_icon = QIcon(str(Path(__file__).parent / "assets" / "active.svg"))
                    inactive_icon = QIcon(str(Path(__file__).parent / "assets" / "inactive.svg"))
                    
                    # Add family groups
                    for family_name in sorted(families.keys()):
                        family_fonts = families[family_name]
                        
                        # Add family header
                        family_item = QListWidgetItem(f"    ▶ {family_name} ({len(family_fonts)} styles)")
                        family_item.setData(Qt.UserRole, None)
                        family_item.setData(Qt.UserRole + 1, 'family')
                        family_item.setData(Qt.UserRole + 2, family_name)
                        font = QFont()
                        font.setBold(True)
                        family_item.setFont(font)
                        self.collection_fonts_list.addItem(family_item)
                        
                        # Add individual fonts (initially hidden)
                        for font_data in family_fonts:
                            font_id, postscript_name, style_name, _ = font_data
                            is_active = self.font_manager.is_font_active(font_id)
                            
                            icon = active_icon if is_active else inactive_icon
                            
                            # Get font type from database
                            font_db_entry = self.db.get_font_by_id(font_id)
                            extension = font_db_entry.get('extension', '') if font_db_entry else ''
                            font_type = 'TrueType' if extension in ['.ttf', '.ttc'] else 'OpenType' if extension == '.otf' else extension
                            
                            preview_text = self.get_preview_text()
                            display_style = style_name or postscript_name or 'Unknown'
                            font_item = QListWidgetItem(icon, f"        {preview_text}    {display_style}    {font_type}")
                            font_item.setData(Qt.UserRole, font_id)
                            font_item.setData(Qt.UserRole + 1, 'font')
                            font_item.setData(Qt.UserRole + 2, family_name)
                            font_item.setToolTip(f"{display_style}")  # Show font name on hover
                            font_item.setHidden(True)  # Start collapsed
                            
                            # Load and apply the actual font if cached
                            font_db_entry = self.db.get_font_by_id(font_id)
                            if font_db_entry and font_db_entry.get('cached_path') and os.path.exists(font_db_entry['cached_path']):
                                from PyQt5.QtGui import QFontDatabase
                                font_id_qt = QFontDatabase.addApplicationFont(font_db_entry['cached_path'])
                                if font_id_qt != -1:
                                    font_families_qt = QFontDatabase.applicationFontFamilies(font_id_qt)
                                    if font_families_qt:
                                        font_size = self.get_font_preview_size()
                                        custom_font = QFont(font_families_qt[0], font_size)
                                        if style_name:
                                            custom_font.setStyleName(style_name)
                                        font_item.setFont(custom_font)
                                    else:
                                        font = QFont()
                                        font.setPointSize(self.get_font_preview_size())
                                        font_item.setFont(font)
                                else:
                                    font = QFont()
                                    font.setPointSize(self.get_font_preview_size())
                                    font_item.setFont(font)
                            else:
                                font = QFont()
                                font.setPointSize(self.get_font_preview_size())
                                font_item.setFont(font)
                            
                            self.collection_fonts_list.addItem(font_item)
                else:
                    # No fonts found
                    no_fonts_item = QListWidgetItem("    (No fonts in this collection)")
                    from PyQt5.QtGui import QFont
                    font = QFont()
                    font.setItalic(True)
                    no_fonts_item.setFont(font)
                    self.collection_fonts_list.addItem(no_fonts_item)
                    self.status_bar.showMessage("No fonts found in collection", 3000)
        
        elif item_type == 'family':
            # Toggle family expansion
            family_name = item.data(Qt.UserRole + 2)
            is_expanded = item.text().strip().startswith("▼")
            
            # Update header icon
            if is_expanded:
                item.setText(item.text().replace("▼", "▶"))
            else:
                item.setText(item.text().replace("▶", "▼"))
            
            # Toggle visibility of family fonts
            for i in range(self.collection_fonts_list.count()):
                list_item = self.collection_fonts_list.item(i)
                if list_item.data(Qt.UserRole + 1) == 'font':
                    if list_item.data(Qt.UserRole + 2) == family_name:
                        list_item.setHidden(is_expanded)
        
        elif item_type == 'font':
            # Toggle font activation
            font_id = item.data(Qt.UserRole)
            if font_id:
                is_active = self.font_manager.is_font_active(font_id)
                print(f"DEBUG: Font {font_id} is_active={is_active}")
                
                try:
                    if is_active:
                        result = self.font_manager.deactivate_font(font_id)
                        print(f"DEBUG: Deactivation result: {result}")
                        self.status_bar.showMessage(result.get('message', 'Font deactivated'), 2000)
                    else:
                        result = self.font_manager.activate_font(font_id)
                        print(f"DEBUG: Activation result: {result}")
                        self.status_bar.showMessage(result.get('message', 'Font activated'), 2000)
                    
                    # Reload all tabs to sync status
                    self.reload_all_tabs()
                except Exception as e:
                    print(f"DEBUG: Error during activation/deactivation: {e}")
                    self.status_bar.showMessage(f"Error: {str(e)}", 5000)
    
    def on_collection_activate(self):
        current_item = self.collections_list.currentItem()
        if not current_item:
            return
        
        collection_id = current_item.data(Qt.UserRole)
        collection_name = current_item.text()
        
        # Get all font IDs for this collection
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id
            FROM fonts f
            JOIN collection_fonts cf ON f.id = cf.font_id
            WHERE cf.collection_id = ?
        """, (collection_id,))
        fonts = cursor.fetchall()
        conn.close()
        
        font_ids = [f[0] for f in fonts]
        
        if not font_ids:
            QMessageBox.information(self, "No Fonts", f"No fonts in collection {collection_name}")
            return
        
        try:
            activated = 0
            for font_id in font_ids:
                self.font_manager.activate_font(font_id)
                activated += 1
            
            self.status_bar.showMessage(f"Activated {activated} fonts from {collection_name}", 3000)
            self.load_recent()
            # Reload all tabs to sync status
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Activation failed: {str(e)}", 5000)
    
    def on_collection_deactivate(self):
        current_item = self.collections_list.currentItem()
        if not current_item:
            return
        
        collection_id = current_item.data(Qt.UserRole)
        collection_name = current_item.text()
        
        # Get all font IDs for this collection
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id
            FROM fonts f
            JOIN collection_fonts cf ON f.id = cf.font_id
            WHERE cf.collection_id = ?
        """, (collection_id,))
        fonts = cursor.fetchall()
        conn.close()
        
        font_ids = [f[0] for f in fonts]
        
        if not font_ids:
            QMessageBox.information(self, "No Fonts", f"No fonts in collection {collection_name}")
            return
        
        try:
            deactivated = 0
            for font_id in font_ids:
                self.font_manager.deactivate_font(font_id)
                deactivated += 1
            
            self.status_bar.showMessage(f"Deactivated {deactivated} fonts from {collection_name}", 3000)
            # Reload all tabs to sync status
            self.reload_all_tabs()
        except Exception as e:
            self.status_bar.showMessage(f"Deactivation failed: {str(e)}", 5000)
    
    def load_recent(self):
        recent = self.db.get_recent_activations()
        self.recent_list.clear()
        
        for font in recent:
            item_text = f"{font.get('postscript_name', 'Unknown')} - {font.get('activated_at', '')}"
            self.recent_list.addItem(item_text)
    
    def sync_metadata(self):
        self.status_bar.showMessage("Syncing metadata...")
        self.sync_button.setEnabled(False)
        
        self.sync_thread = SyncThread(self.font_manager)
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.error.connect(self.on_sync_error)
        self.sync_thread.start()
    
    def on_sync_finished(self, result):
        self.load_collections()
        self.load_clients()  # Reload clients list to show new clients
        
        # Auto-download fonts in background if there are new ones
        if result['fonts'] > 0:
            self.status_bar.showMessage(f"Synced {result['fonts']} fonts. Downloading...")
            self.download_all_fonts()
        else:
            self.status_bar.showMessage(f"Sync complete: {result['fonts']} fonts, {result['collections']} collections, {result['clients']} clients", 3000)
            self.sync_button.setEnabled(True)
    
    def on_sync_error(self, error):
        self.status_bar.showMessage(f"Sync failed: {error}", 5000)
        self.sync_button.setEnabled(True)
    
    def download_all_fonts(self):
        self.download_thread = DownloadThread(self.font_manager)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()
    
    def on_download_progress(self, current, total, filename):
        percent = int((current / total) * 100)
        self.status_bar.showMessage(f"Downloading fonts: {current}/{total} ({percent}%) - {filename}")
    
    def on_download_finished(self, result):
        self.status_bar.showMessage(
            f"Download complete: {result['downloaded']} downloaded, "
            f"{result['skipped']} cached, {result['failed']} failed", 
            5000
        )
        self.sync_button.setEnabled(True)
        self.load_all_fonts()
        self.load_recent()
    
    def on_download_error(self, error):
        self.status_bar.showMessage(f"Download failed: {error}", 5000)
        self.sync_button.setEnabled(True)
    
    def handle_indesign_request(self, data):
        """Handle font request from InDesign."""
        from PyQt5.QtCore import QMetaObject, Q_ARG
        
        # Use QMetaObject.invokeMethod to safely call from HTTP thread to GUI thread
        QMetaObject.invokeMethod(
            self, 
            "_process_indesign_request",
            Qt.QueuedConnection,
            Q_ARG(object, data)
        )
    
    def _process_indesign_request(self, data):
        """Process InDesign font request in the GUI thread."""
        doc_name = data.get('document_name', 'Unknown Document')
        missing_fonts = data.get('missing_fonts', [])
        all_fonts = data.get('all_fonts', [])
        auto_activate = data.get('auto_activate', False)
        
        if not missing_fonts:
            if not auto_activate:
                QMessageBox.information(
                    self,
                    "No Missing Fonts",
                    f"Document: {doc_name}\n\nAll fonts are available!"
                )
            return
        
        # Try to match missing fonts with fonts in the database
        matched_fonts = []
        unmatched_fonts = []
        
        for font_name in missing_fonts:
            # Try exact match first (PostScript name or family name)
            matches = self.find_font_matches(font_name)
            if matches:
                matched_fonts.extend(matches)
            else:
                unmatched_fonts.append(font_name)
        
        # Auto-activate mode: activate silently without dialog
        if auto_activate and matched_fonts:
            activated = 0
            for font_id, ps_name, family_name, style_name in matched_fonts:
                try:
                    self.font_manager.activate_font(font_id)
                    activated += 1
                except Exception as e:
                    print(f"Failed to activate {ps_name}: {e}")
            
            self.reload_all_tabs()
            
            # Show brief status message
            self.status_bar.showMessage(
                f"InDesign: Activated {activated}/{len(missing_fonts)} fonts for {doc_name}",
                5000
            )
            
            # Only show dialog if some fonts couldn't be found
            if unmatched_fonts:
                self.show_indesign_font_dialog(doc_name, matched_fonts, unmatched_fonts, all_fonts)
        else:
            # Manual mode or no matches: show dialog
            self.show_indesign_font_dialog(doc_name, matched_fonts, unmatched_fonts, all_fonts)
    
    def find_font_matches(self, font_name):
        """Find fonts in the database that match the given name."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Try exact PostScript name match
        cursor.execute(
            "SELECT id, ps_name, family_name, style_name FROM fonts WHERE ps_name = ?",
            (font_name,)
        )
        results = cursor.fetchall()
        
        if not results:
            # Try family name match
            cursor.execute(
                "SELECT id, ps_name, family_name, style_name FROM fonts WHERE family_name LIKE ?",
                (f"%{font_name}%",)
            )
            results = cursor.fetchall()
        
        conn.close()
        return results
    
    def show_indesign_font_dialog(self, doc_name, matched_fonts, unmatched_fonts, all_fonts):
        """Show dialog with InDesign font request results."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"InDesign Font Request - {doc_name}")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Document info
        layout.addWidget(QLabel(f"<b>Document:</b> {doc_name}"))
        layout.addWidget(QLabel(f"<b>Total fonts used:</b> {len(all_fonts)}"))
        layout.addWidget(QLabel(f"<b>Missing fonts:</b> {len(matched_fonts) + len(unmatched_fonts)}"))
        
        # Matched fonts
        if matched_fonts:
            layout.addWidget(QLabel(f"\n<b>Found {len(matched_fonts)} font(s) in library:</b>"))
            matched_list = QListWidget()
            for font_id, ps_name, family_name, style_name in matched_fonts:
                matched_list.addItem(f"✓ {ps_name} ({family_name} - {style_name})")
            layout.addWidget(matched_list)
            
            # Activate button
            activate_btn = QPushButton(f"Activate {len(matched_fonts)} Font(s)")
            activate_btn.clicked.connect(lambda: self.activate_indesign_fonts(matched_fonts, dialog))
            layout.addWidget(activate_btn)
        
        # Unmatched fonts
        if unmatched_fonts:
            layout.addWidget(QLabel(f"\n<b>Not found ({len(unmatched_fonts)} font(s)):</b>"))
            unmatched_list = QListWidget()
            for font_name in unmatched_fonts:
                unmatched_list.addItem(f"✗ {font_name}")
            layout.addWidget(unmatched_list)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def activate_indesign_fonts(self, fonts, dialog):
        """Activate fonts requested from InDesign."""
        activated = 0
        failed = 0
        
        for font_id, ps_name, family_name, style_name in fonts:
            try:
                self.font_manager.activate_font(font_id)
                activated += 1
            except Exception as e:
                failed += 1
                print(f"Failed to activate {ps_name}: {e}")
        
        self.reload_all_tabs()
        
        QMessageBox.information(
            self,
            "Fonts Activated",
            f"Activated {activated} font(s)\n" +
            (f"Failed: {failed}" if failed > 0 else "")
        )
        
        dialog.accept()
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            server_url = dialog.get_server_url()
            import config
            config.SERVER_URL = server_url
            self.api.server_url = server_url
            
            # Reload fonts if settings were saved (font size may have changed)
            if dialog.settings_saved:
                # Apply settings
                self.apply_settings()
                self.load_all_fonts()
                
                # Reload currently selected client if on Clients tab
                current_client = self.clients_list.currentItem()
                if current_client:
                    self.on_client_selected(current_client)
                
                # Reload currently selected collection if on Collections tab
                current_collection = self.collections_list.currentItem()
                if current_collection:
                    self.on_collection_selected(current_collection)
                
                self.status_bar.showMessage("Settings saved!", 3000)
    
    def on_logout(self):
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.api.clear_token()
            QMessageBox.information(self, "Logged Out", "You have been logged out successfully")
            self.close()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
