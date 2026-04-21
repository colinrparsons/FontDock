import sys
import os
import json
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTabWidget, QListWidget,
    QMessageBox, QDialog, QFormLayout, QListWidgetItem, QProgressDialog,
    QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from api_client import FontDockAPI
from database import LocalDatabase
from font_manager import FontManager
from config import APP_SUPPORT_DIR, LOG_PATH
from http_server import FontDockHTTPServer

if sys.platform == 'darwin':
    from fontdock_platform.macos import get_fonts_dir
elif sys.platform == 'win32':
    from fontdock_platform.windows import get_fonts_dir


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
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)
        self.settings_file = APP_SUPPORT_DIR / "settings.json"
        self.settings_saved = False
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        from PyQt5.QtWidgets import QSpinBox, QCheckBox, QGroupBox
        from animated_toggle import AnimatedToggle
        
        main_layout = QVBoxLayout()
        
        # ── Server Group ──────────────────────────
        server_group = QGroupBox("Server")
        server_layout = QFormLayout()
        
        # Address + Port instead of full URL
        addr_layout = QHBoxLayout()
        self.server_address_input = QLineEdit()
        self.server_address_input.setPlaceholderText("192.168.0.48")
        self.server_address_input.setMinimumWidth(200)
        
        self.server_port_input = QLineEdit()
        self.server_port_input.setPlaceholderText("8000")
        self.server_port_input.setMaxLength(5)
        self.server_port_input.setMaximumWidth(80)
        
        addr_layout.addWidget(self.server_address_input)
        addr_layout.addWidget(QLabel("Port:"))
        addr_layout.addWidget(self.server_port_input)
        server_layout.addRow("Address:", addr_layout)
        
        # Test connection button + inline result label
        test_layout = QHBoxLayout()
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        test_layout.addWidget(self.test_button)
        test_layout.addWidget(self.test_result_label, 1)
        server_layout.addRow("", test_layout)
        
        # Last known good connection info
        self.last_good_label = QLabel("")
        self.last_good_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        server_layout.addRow("", self.last_good_label)
        
        server_group.setLayout(server_layout)
        main_layout.addWidget(server_group)
        
        # ── Sync Group ─────────────────────────────
        sync_group = QGroupBox("Sync")
        sync_layout = QFormLayout()
        
        self.collapse_families_toggle = AnimatedToggle()
        collapse_layout = QHBoxLayout()
        collapse_label = QLabel("Collapse Families by Default")
        collapse_layout.addWidget(collapse_label)
        collapse_layout.addWidget(self.collapse_families_toggle)
        collapse_layout.addStretch()
        sync_layout.addRow("", collapse_layout)
        
        sync_group.setLayout(sync_layout)
        main_layout.addWidget(sync_group)
        
        # ── Appearance Group ───────────────────────
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout()
        
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
        
        appearance_layout.addRow("Font Preview Size:", self.font_size_input)
        appearance_layout.addRow("App Font Size:", self.app_font_size_input)
        appearance_layout.addRow("", self.dark_mode_checkbox)
        
        appearance_group.setLayout(appearance_layout)
        main_layout.addWidget(appearance_group)
        
        # ── Buttons ────────────────────────────────
        main_layout.addStretch()
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        
        self.save_button.setAutoDefault(False)
        self.save_button.setDefault(False)
        
        self.save_button.clicked.connect(self.save_and_accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def _parse_url(self, url):
        """Parse a URL like http://192.168.0.48:8000 into (address, port)."""
        url = url.strip()
        # Remove protocol prefix
        for prefix in ['https://', 'http://']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        # Split address:port
        if ':' in url:
            parts = url.split(':', 1)
            return parts[0], parts[1]
        return url, '8000'
    
    def _build_url(self):
        """Build a full URL from address and port fields."""
        addr = self.server_address_input.text().strip()
        port = self.server_port_input.text().strip() or '8000'
        if not addr:
            return ''
        return f"http://{addr}:{port}"
    
    def load_settings(self):
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                url = settings.get('server_url', 'http://localhost:9998')
                addr, port = self._parse_url(url)
                self.server_address_input.setText(addr)
                self.server_port_input.setText(port)
                self.font_size_input.setValue(settings.get('font_size', 14))
                self.app_font_size_input.setValue(settings.get('app_font_size', 12))
                self.dark_mode_checkbox.setChecked(settings.get('dark_mode', False))
                self.collapse_families_toggle.setChecked(settings.get('collapse_families', True))
                
                # Show last known good URL
                last_good = settings.get('last_known_good_url', '')
                if last_good:
                    self.last_good_label.setText(f"Last known good: {last_good}")
        else:
            self.server_address_input.setText('localhost')
            self.server_port_input.setText('9998')
            self.font_size_input.setValue(14)
            self.app_font_size_input.setValue(12)
            self.dark_mode_checkbox.setChecked(False)
            self.collapse_families_toggle.setChecked(True)
    
    def test_connection(self):
        """Test connection with multi-check and inline result."""
        import requests
        server_url = self._build_url()
        
        if not server_url:
            self.test_result_label.setText("❌ Enter server address")
            self.test_result_label.setStyleSheet("color: #ef4444;")
            return
        
        self.test_result_label.setText("Testing...")
        self.test_result_label.setStyleSheet("color: #f97316;")
        QApplication.processEvents()
        
        try:
            # Check 1: Health endpoint
            response = requests.get(f"{server_url}/health", timeout=5)
            if response.status_code != 200:
                self.test_result_label.setText(f"❌ Server responded with status {response.status_code}")
                self.test_result_label.setStyleSheet("color: #ef4444;")
                return
            
            # Check 2: Font API availability
            font_count = None
            try:
                font_response = requests.get(
                    f"{server_url}/api/fonts",
                    params={"limit": 1},
                    timeout=5
                )
                if font_response.status_code == 200:
                    data = font_response.json()
                    font_count = data.get('total', None)
            except Exception:
                pass
            
            # Build result message
            msg = f"✅ Connected"
            if font_count is not None:
                msg += f" — {font_count} fonts available"
            self.test_result_label.setText(msg)
            self.test_result_label.setStyleSheet("color: #22c55e;")
            
            # Update last known good
            self.last_good_label.setText(f"Last known good: {server_url}")
            
        except requests.exceptions.ConnectionError:
            self.test_result_label.setText("❌ Cannot reach server — check address and network")
            self.test_result_label.setStyleSheet("color: #ef4444;")
        except requests.exceptions.Timeout:
            self.test_result_label.setText("❌ Connection timed out")
            self.test_result_label.setStyleSheet("color: #ef4444;")
        except Exception as e:
            self.test_result_label.setText(f"❌ Error: {str(e)}")
            self.test_result_label.setStyleSheet("color: #ef4444;")
    
    def save_and_accept(self):
        server_url = self._build_url()
        
        # Load existing settings to preserve keys we don't edit
        settings = {}
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        
        settings['server_url'] = server_url
        settings['server_address'] = self.server_address_input.text().strip()
        settings['server_port'] = self.server_port_input.text().strip() or '8000'
        settings['font_size'] = self.font_size_input.value()
        settings['app_font_size'] = self.app_font_size_input.value()
        settings['dark_mode'] = self.dark_mode_checkbox.isChecked()
        settings['collapse_families'] = self.collapse_families_toggle.isChecked()
        
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        self.settings_saved = True
        self.accept()
    
    def get_server_url(self):
        return self._build_url()
    
    def get_font_size(self):
        return self.font_size_input.value()


class LoginDialog(QDialog):
    OFFLINE_RESULT = 3  # Custom result code for offline mode
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FontDock Login")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.settings_file = APP_SUPPORT_DIR / "settings.json"
        self.setup_ui()
        self.load_server_url()
        self.load_last_username()
    
    def _parse_url(self, url):
        url = url.strip()
        for prefix in ['https://', 'http://']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        if ':' in url:
            parts = url.split(':', 1)
            return parts[0], parts[1]
        return url, '8000'
    
    def _build_url(self):
        addr = self.server_address_input.text().strip()
        port = self.server_port_input.text().strip() or '8000'
        if not addr:
            return ''
        return f"http://{addr}:{port}"
    
    def setup_ui(self):
        layout = QFormLayout()
        
        # Server address + port
        addr_layout = QHBoxLayout()
        self.server_address_input = QLineEdit()
        self.server_address_input.setPlaceholderText("192.168.0.48")
        self.server_address_input.setMinimumWidth(200)
        
        self.server_port_input = QLineEdit()
        self.server_port_input.setPlaceholderText("8000")
        self.server_port_input.setMaxLength(5)
        self.server_port_input.setMaximumWidth(80)
        
        self.test_button = QPushButton("Test")
        self.test_button.clicked.connect(self.test_connection)
        
        addr_layout.addWidget(self.server_address_input)
        addr_layout.addWidget(QLabel("Port:"))
        addr_layout.addWidget(self.server_port_input)
        addr_layout.addWidget(self.test_button)
        
        # Inline test result
        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        
        layout.addRow("Server:", addr_layout)
        layout.addRow("", self.test_result_label)
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.offline_button = QPushButton("Work Offline")
        self.cancel_button = QPushButton("Cancel")
        
        self.login_button.clicked.connect(self.save_and_login)
        self.offline_button.clicked.connect(self.work_offline)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.offline_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def load_server_url(self):
        """Load server URL from settings."""
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                url = settings.get('server_url', 'http://localhost:9998')
                addr, port = self._parse_url(url)
                self.server_address_input.setText(addr)
                self.server_port_input.setText(port)
        else:
            self.server_address_input.setText('localhost')
            self.server_port_input.setText('9998')
    
    def load_last_username(self):
        """Pre-fill username from last successful login."""
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                last_user = settings.get('last_username', '')
                if last_user:
                    self.username_input.setText(last_user)
    
    def test_connection(self):
        """Test connection with inline result."""
        import requests
        server_url = self._build_url()
        
        if not server_url:
            self.test_result_label.setText("❌ Enter server address")
            self.test_result_label.setStyleSheet("color: #ef4444;")
            return
        
        self.test_result_label.setText("Testing...")
        self.test_result_label.setStyleSheet("color: #f97316;")
        QApplication.processEvents()
        
        try:
            response = requests.get(f"{server_url}/health", timeout=5)
            if response.status_code == 200:
                # Also check font count
                font_count = None
                try:
                    font_response = requests.get(
                        f"{server_url}/api/fonts",
                        params={"limit": 1},
                        timeout=5
                    )
                    if font_response.status_code == 200:
                        data = font_response.json()
                        font_count = data.get('total', None)
                except Exception:
                    pass
                
                msg = "✅ Connected"
                if font_count is not None:
                    msg += f" — {font_count} fonts available"
                self.test_result_label.setText(msg)
                self.test_result_label.setStyleSheet("color: #22c55e;")
            else:
                self.test_result_label.setText(f"❌ Server error: {response.status_code}")
                self.test_result_label.setStyleSheet("color: #ef4444;")
        except requests.exceptions.ConnectionError:
            self.test_result_label.setText("❌ Cannot reach server")
            self.test_result_label.setStyleSheet("color: #ef4444;")
        except requests.exceptions.Timeout:
            self.test_result_label.setText("❌ Connection timed out")
            self.test_result_label.setStyleSheet("color: #ef4444;")
        except Exception as e:
            self.test_result_label.setText(f"❌ Error: {str(e)}")
            self.test_result_label.setStyleSheet("color: #ef4444;")
    
    def save_and_login(self):
        """Save server URL and proceed with login."""
        server_url = self._build_url()
        
        # Save server URL to settings
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        settings['server_url'] = server_url
        settings['server_address'] = self.server_address_input.text().strip()
        settings['server_port'] = self.server_port_input.text().strip() or '8000'
        settings['last_username'] = self.username_input.text().strip()
        
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Update config
        import config
        config.SERVER_URL = server_url
        
        self.accept()
    
    def work_offline(self):
        """Save server URL and launch in offline mode."""
        server_url = self._build_url()
        
        # Save server URL to settings
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        settings['server_url'] = server_url
        settings['server_address'] = self.server_address_input.text().strip()
        settings['server_port'] = self.server_port_input.text().strip() or '8000'
        
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Update config
        import config
        config.SERVER_URL = server_url
        
        self.done(self.OFFLINE_RESULT)
    
    def get_credentials(self):
        return self.username_input.text(), self.password_input.text()
    
    def get_server_url(self):
        return self._build_url()


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
        
        # Don't show window yet - will show after successful login
        self.login_successful = False
        
        if not self.api.token:
            self.login_successful = self.show_login()
        else:
            self.setup_ui()
            # Try to sync, but work offline if server is unreachable
            try:
                self.sync_metadata()
            except Exception as e:
                self._set_connection_state("disconnected")
                self.status_bar.showMessage(f"Working offline — server unreachable: {e}", 5000)
                # Still load fonts from local DB
                self.load_all_fonts()
                self.load_recent()
            self.login_successful = True
    
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
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle('Clear Cache & Database')
        msg.setText('Are you sure you want to clear the cache and database?')
        msg.setInformativeText(
            'This will remove all cached fonts. You will not be able to work offline '
            'or activate fonts until you connect to the server and sync again.'
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        reply = msg.exec_()
        
        if reply == QMessageBox.Yes:
            # Second confirmation
            reply2 = QMessageBox.warning(
                self,
                'Confirm Clear Cache',
                'Are you sure? This cannot be undone.',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply2 != QMessageBox.Yes:
                return
            
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
                        QComboBox {
                            background-color: #2a2a2a;
                            color: #ffffff;
                            border: 1px solid #3a3a3a;
                            padding: 3px 8px;
                            border-radius: 4px;
                        }
                        QComboBox::drop-down {
                            border: none;
                        }
                        QComboBox QAbstractItemView {
                            background-color: #2a2a2a;
                            color: #ffffff;
                            selection-background-color: #4dd0e1;
                        }
                        QCheckBox {
                            color: #ffffff;
                            spacing: 5px;
                        }
                        QCheckBox::indicator {
                            width: 16px;
                            height: 16px;
                            border: 1px solid #666666;
                            border-radius: 3px;
                            background-color: #2a2a2a;
                        }
                        QCheckBox::indicator:checked {
                            background-color: #00bcd4;
                            border-color: #00bcd4;
                        }
                        QGroupBox {
                            color: #ffffff;
                            border: 1px solid #3a3a3a;
                            border-radius: 6px;
                            margin-top: 12px;
                            padding-top: 16px;
                            font-weight: bold;
                        }
                        QGroupBox::title {
                            subcontrol-origin: margin;
                            left: 12px;
                            padding: 0 6px;
                        }
                    """)
                else:
                    self.setStyleSheet("")  # Reset to default
                    # Light mode: status bar labels in black
                    if hasattr(self, 'last_sync_label'):
                        self.last_sync_label.setStyleSheet("color: #000000; padding: 0 8px;")
                    if hasattr(self, 'cache_count_label'):
                        self.cache_count_label.setStyleSheet("color: #000000; padding: 0 8px;")
                
                # Dark mode: status bar labels in white
                if dark_mode:
                    if hasattr(self, 'last_sync_label'):
                        self.last_sync_label.setStyleSheet("color: #ffffff; padding: 0 8px;")
                    if hasattr(self, 'cache_count_label'):
                        self.cache_count_label.setStyleSheet("color: #ffffff; padding: 0 8px;")
                
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
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # Update server URL from login dialog
            server_url = dialog.get_server_url()
            self.api.server_url = server_url
            
            username, password = dialog.get_credentials()
            try:
                self.api.login(username, password)
                self.setup_ui()
                self.sync_metadata()
                return True  # Login successful
            except Exception as e:
                QMessageBox.critical(self, "Login Failed", str(e))
                # Clear token on failed login
                self.api.clear_token()
                self.close()
                return False  # Login failed
        elif result == LoginDialog.OFFLINE_RESULT:
            # Work offline - no server authentication
            server_url = dialog.get_server_url()
            self.api.server_url = server_url
            self.setup_ui()
            self._set_connection_state("disconnected")
            self.status_bar.showMessage("Working offline — no server connection", 5000)
            # Load fonts from local DB
            self.load_all_fonts()
            self.load_recent()
            return True
        else:
            self.close()
            return False  # Login cancelled
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Add status bar with permanent indicators
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Connection state indicator
        self.connection_label = QLabel("● Disconnected")
        self.connection_label.setStyleSheet("color: #ef4444; font-weight: bold; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        # Last sync indicator
        self.last_sync_label = QLabel("Last sync: never")
        # Determine status bar text color based on current dark mode setting
        settings_file = APP_SUPPORT_DIR / "settings.json"
        _status_color = "#ffffff"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as _f:
                    _s = json.load(_f)
                if not _s.get('dark_mode', False):
                    _status_color = "#000000"
            except Exception:
                _status_color = "#000000"
        else:
            _status_color = "#000000"
        
        self.last_sync_label.setStyleSheet(f"color: {_status_color}; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.last_sync_label)
        
        # Cache count indicator
        self.cache_count_label = QLabel("0 fonts cached")
        self.cache_count_label.setStyleSheet(f"color: {_status_color}; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.cache_count_label)
        
        # Timer to refresh "last sync" relative time
        from PyQt5.QtCore import QTimer
        self._sync_refresh_timer = QTimer()
        self._sync_refresh_timer.timeout.connect(self._refresh_sync_time)
        self._sync_refresh_timer.start(60000)  # Every 60s
        
        # Store last sync time
        self._last_sync_time = None
        self._load_last_sync_time()
        
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
        self.system_fonts_tab = QWidget()
        self.logs_tab = QWidget()
        
        self.setup_fonts_tab()
        self.setup_collections_tab()
        self.setup_clients_tab()
        self.setup_recent_tab()
        self.setup_system_fonts_tab()
        self.setup_logs_tab()
        
        self.tabs.addTab(self.fonts_tab, "Fonts")
        self.tabs.addTab(self.collections_tab, "Collections")
        self.tabs.addTab(self.clients_tab, "Clients")
        self.tabs.addTab(self.recent_tab, "Recent")
        self.tabs.addTab(self.system_fonts_tab, "System Fonts")
        self.tabs.addTab(self.logs_tab, "Logs")
        
        # Refresh icons when switching tabs (to show fonts activated via InDesign)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        central_widget.setLayout(layout)
    
    def setup_fonts_tab(self):
        layout = QVBoxLayout()
        
        # Preview text bar (Feature 5)
        preview_bar = QHBoxLayout()
        preview_label = QLabel("Preview:")
        self.preview_input = QLineEdit()
        self.preview_input.setText(self.get_preview_text())
        self.preview_input.setPlaceholderText("Type custom preview text...")
        self.preview_input.textChanged.connect(self.on_preview_text_changed)
        
        self.preview_preset_combo = QComboBox()
        self.preview_preset_combo.setMinimumWidth(160)
        self._load_preview_presets()
        self.preview_preset_combo.currentTextChanged.connect(self.on_preset_selected)
        
        save_preset_btn = QPushButton("Save Preset")
        save_preset_btn.clicked.connect(self.on_save_preset)
        
        preview_bar.addWidget(preview_label)
        preview_bar.addWidget(self.preview_input, 1)
        preview_bar.addWidget(self.preview_preset_combo)
        preview_bar.addWidget(save_preset_btn)
        layout.addLayout(preview_bar)
        
        # Filter bar (Feature 2)
        filter_bar = QHBoxLayout()
        self.filter_active_cb = QCheckBox("Activated Only")
        self.filter_active_cb.stateChanged.connect(self.apply_filters)
        self.filter_recent_cb = QCheckBox("Recently Used")
        self.filter_recent_cb.stateChanged.connect(self.apply_filters)
        filter_bar.addWidget(QLabel("Filters:"))
        filter_bar.addWidget(self.filter_active_cb)
        filter_bar.addWidget(self.filter_recent_cb)
        
        filter_bar.addWidget(QLabel("Collection:"))
        self.filter_collection_combo = QComboBox()
        self.filter_collection_combo.setMinimumWidth(150)
        self.filter_collection_combo.addItem("All", None)
        collections = self.db.get_all_collections()
        for coll in collections:
            self.filter_collection_combo.addItem(coll['name'], coll['id'])
        self.filter_collection_combo.currentIndexChanged.connect(self.apply_filters)
        filter_bar.addWidget(self.filter_collection_combo)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)
        
        self.fonts_list = QListWidget()
        self.fonts_list.setSelectionMode(QListWidget.ExtendedSelection)  # Enable multi-select
        self.fonts_list.setSpacing(2)  # Add spacing between items
        self.fonts_list.itemDoubleClicked.connect(self.on_font_activate)
        
        button_layout = QHBoxLayout()
        activate_button = QPushButton(self.add_icon, "Activate Selected")
        activate_button.clicked.connect(self.on_font_activate_button)
        
        deactivate_button = QPushButton(self.delete_icon, "Deactivate Selected")
        deactivate_button.clicked.connect(self.on_font_deactivate_button)
        
        compare_button = QPushButton("Compare")
        compare_button.clicked.connect(self.on_compare_fonts)
        
        button_layout.addWidget(activate_button)
        button_layout.addWidget(deactivate_button)
        button_layout.addWidget(compare_button)
        
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
    
    def setup_system_fonts_tab(self):
        """Tab showing all system-installed fonts (not FontDock-managed)."""
        layout = QVBoxLayout()
        
        # Search bar for system fonts
        sys_search_bar = QHBoxLayout()
        self.system_font_search = QLineEdit()
        self.system_font_search.setPlaceholderText("Search system fonts...")
        self.system_font_search.textChanged.connect(self.on_system_font_search)
        sys_search_bar.addWidget(self.system_font_search)
        layout.addLayout(sys_search_bar)
        
        # Info label
        info_label = QLabel("System-installed fonts — available to all applications. Not managed by FontDock.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #9ca3af; font-style: italic; padding: 4px;")
        layout.addWidget(info_label)
        
        self.system_fonts_list = QListWidget()
        self.system_fonts_list.setSelectionMode(QListWidget.SingleSelection)
        self.system_fonts_list.setSpacing(2)
        layout.addWidget(self.system_fonts_list)
        
        # Count label
        self.system_font_count_label = QLabel("")
        self.system_font_count_label.setStyleSheet("color: #9ca3af; padding: 4px;")
        layout.addWidget(self.system_font_count_label)
        
        self.system_fonts_tab.setLayout(layout)
        
        # Load system fonts
        self._system_font_families = []
        self._load_system_fonts()
    
    def setup_logs_tab(self):
        """Tab showing the FontDock log file contents."""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_logs)
        toolbar.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        toolbar.addWidget(clear_btn)
        
        # Log level filter
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(self.refresh_logs)
        toolbar.addWidget(QLabel("Level:"))
        toolbar.addWidget(self.log_level_combo)
        
        toolbar.addStretch()
        
        # Log file path label
        self.log_path_label = QLabel(f"Log file: {LOG_PATH}")
        self.log_path_label.setStyleSheet("color: #9ca3af; font-style: italic; padding: 4px;")
        self.log_path_label.setWordWrap(True)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.log_path_label)
        
        # Log text display
        from PyQt5.QtWidgets import QTextEdit
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setFontFamily("Menlo")
        self.log_text.setFontPointSize(10)
        layout.addWidget(self.log_text)
        
        self.logs_tab.setLayout(layout)
        
        # Initial load
        self.refresh_logs()
    
    def refresh_logs(self):
        """Read and display the log file, filtering by selected level."""
        try:
            level_filter = self.log_level_combo.currentText()
            
            if not LOG_PATH.exists():
                self.log_text.setPlainText("No log file found.")
                return
            
            with open(LOG_PATH, 'r') as f:
                lines = f.readlines()
            
            # Keep last 2000 lines to avoid memory issues
            if len(lines) > 2000:
                lines = lines[-2000:]
            
            # Filter by log level
            if level_filter != "All":
                filtered = []
                for line in lines:
                    if f" - {level_filter} - " in line:
                        filtered.append(line)
                lines = filtered
            
            self.log_text.setPlainText(''.join(lines))
            
            # Auto-scroll to bottom
            from PyQt5.QtGui import QTextCursor
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)
            
        except Exception as e:
            self.log_text.setPlainText(f"Error reading log file: {e}")
    
    def clear_log(self):
        """Clear the log file contents."""
        reply = QMessageBox.warning(
            self,
            'Clear Log File',
            'Are you sure you want to clear the log file?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                with open(LOG_PATH, 'w') as f:
                    f.write('')
                self.refresh_logs()
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to clear log: {e}')

    def _load_system_fonts(self):
        """Enumerate system fonts using QFontDatabase and populate the list."""
        from PyQt5.QtGui import QFontDatabase, QFont, QIcon
        
        self.system_fonts_list.clear()
        font_db = QFontDatabase()
        families = font_db.families()
        
        # Sort families
        families = sorted(families)
        self._system_font_families = families
        
        collapse_by_default = self.get_collapse_families_setting()
        preview_text = self.preview_input.text() if hasattr(self, 'preview_input') else "The quick brown fox jumps over the lazy dog"
        font_size = self.get_font_preview_size()
        
        # Icon for individual style items only (green = available/installed)
        assets_dir = Path(__file__).parent / "assets"
        sys_icon = QIcon(str(assets_dir / "active.svg"))
        
        for family in families:
            # Get styles for this family
            styles = font_db.styles(family)
            style_count = len(styles)
            
            # Create family header — NO icon (same as Fonts tab, triangle is in the text)
            arrow = "▶" if collapse_by_default else "▼"
            family_text = f"{arrow} {family} ({style_count} style{'s' if style_count != 1 else ''})"
            family_item = QListWidgetItem(family_text)
            family_item.setData(Qt.UserRole, None)       # No font ID (system font)
            family_item.setData(Qt.UserRole + 1, family) # family name (marks as header)
            family_item.setBackground(Qt.lightGray)
            family_font = QFont()
            family_font.setBold(True)
            family_item.setFont(family_font)
            self.system_fonts_list.addItem(family_item)
            
            # Add individual styles
            for style in sorted(styles):
                style_text = f"    {preview_text}    {style}    [System]"
                style_item = QListWidgetItem(sys_icon, style_text)
                style_item.setData(Qt.UserRole, family)       # family name for reference
                style_item.setData(Qt.UserRole + 1, None)     # None = not a header
                style_item.setData(Qt.UserRole + 2, style)
                
                # Apply the actual font
                try:
                    custom_font = font_db.font(family, style, font_size)
                    style_item.setFont(custom_font)
                except Exception:
                    pass
                
                self.system_fonts_list.addItem(style_item)
                # Set hidden AFTER adding to ensure it takes effect
                style_item.setHidden(collapse_by_default)
        
        self.system_font_count_label.setText(f"{len(families)} font families installed on system")
        
        # Connect click handler for expand/collapse
        try:
            self.system_fonts_list.itemClicked.disconnect(self._on_system_font_clicked)
        except Exception:
            pass
        self.system_fonts_list.itemClicked.connect(self._on_system_font_clicked)
    
    def _on_system_font_clicked(self, item):
        """Toggle expand/collapse of system font family."""
        family_name = item.data(Qt.UserRole + 1)
        if not family_name:
            return
        
        is_expanded = item.text().startswith("▼")
        
        if is_expanded:
            item.setText(item.text().replace("▼", "▶"))
        else:
            item.setText(item.text().replace("▶", "▼"))
        
        # Toggle visibility of child styles
        row = self.system_fonts_list.row(item)
        for i in range(row + 1, self.system_fonts_list.count()):
            child = self.system_fonts_list.item(i)
            if child.data(Qt.UserRole + 1) is not None:  # Next family header
                break
            child.setHidden(is_expanded)
    
    def on_system_font_search(self, text):
        """Filter system fonts by search text."""
        if len(text) < 2:
            # Reset to collapse setting
            collapse = self.get_collapse_families_setting()
            for i in range(self.system_fonts_list.count()):
                item = self.system_fonts_list.item(i)
                family = item.data(Qt.UserRole + 1)
                if family:  # Family header
                    item.setHidden(False)
                    arrow = "▶" if collapse else "▼"
                    current = item.text()
                    if current.startswith("▶") or current.startswith("▼"):
                        current = arrow + current[1:]
                    item.setText(current)
                else:
                    item.setHidden(collapse)
            return
        
        text_lower = text.lower()
        for i in range(self.system_fonts_list.count()):
            item = self.system_fonts_list.item(i)
            family = item.data(Qt.UserRole + 1)
            if family:
                matches = text_lower in family.lower()
                item.setHidden(not matches)
                # If matching, auto-expand styles
                if matches:
                    item.setText(item.text().replace("▶", "▼"))
                    for j in range(i + 1, self.system_fonts_list.count()):
                        child = self.system_fonts_list.item(j)
                        if child.data(Qt.UserRole + 1) is not None:
                            break
                        child.setHidden(False)
                else:
                    item.setText(item.text().replace("▼", "▶"))
    
    def load_all_fonts(self):
        """Load all fonts grouped by family with preview text, status icons, and state badges."""
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
        from PyQt5.QtGui import QFont, QFontDatabase, QIcon
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
        
        # Load all status icons once
        assets_dir = Path(__file__).parent / "assets"
        active_icon = QIcon(str(assets_dir / "active.svg"))
        inactive_icon = QIcon(str(assets_dir / "inactive.svg"))
        cached_icon = QIcon(str(assets_dir / "cached.svg"))
        remote_icon = QIcon(str(assets_dir / "remote.svg"))
        
        # Get preview text from inline input if available, else settings
        preview_text = self.preview_input.text() if hasattr(self, 'preview_input') else self.get_preview_text()
        
        # Get filter data
        active_font_ids = set()
        if hasattr(self, 'filter_active_cb') and self.filter_active_cb.isChecked():
            for i in range(self.fonts_list.count() if self.fonts_list.count() > 0 else 0):
                pass  # Will filter after loading
        
        recent_font_ids = set()
        if hasattr(self, 'filter_recent_cb') and self.filter_recent_cb.isChecked():
            recent = self.db.get_recent_activations()
            recent_font_ids = set(f.get('id') for f in recent)
        
        collection_font_ids = None
        if hasattr(self, 'filter_collection_combo'):
            coll_data = self.filter_collection_combo.currentData()
            if coll_data is not None:
                coll_fonts = self.db.get_collection_fonts(coll_data)
                collection_font_ids = set(f['id'] for f in coll_fonts)
        
        self.fonts_list.clear()
        for family_name in sorted(families.keys()):
            fonts = families[family_name]
            format_type = 'TrueType' if fonts[0]['extension'] in ['.ttf', '.ttc'] else 'OpenType' if fonts[0]['extension'] == '.otf' else 'Unknown'
            
            # Count active fonts in family
            user_fonts_dir = get_fonts_dir()
            active_count = sum(1 for f in fonts if (user_fonts_dir / f['filename']).exists())
            total_count = len(fonts)
            
            collapse_icon = "▼" if not collapse_by_default else "▶"
            family_item = QListWidgetItem(f"{collapse_icon} {family_name} ({active_count}/{total_count} active) - {format_type}")
            family_item.setData(Qt.UserRole, None)
            family_item.setData(Qt.UserRole + 1, family_name)
            family_item.setBackground(Qt.lightGray)
            self.fonts_list.addItem(family_item)
            
            for font in fonts:
                style = font['style_name'] or 'Regular'
                font_format = 'TrueType' if font['extension'] in ['.ttf', '.ttc'] else 'OpenType' if font['extension'] == '.otf' else font['extension']
                
                # Determine font state (Feature 4)
                is_activated = (user_fonts_dir / font['filename']).exists()
                is_cached = font['cached_path'] and os.path.exists(font['cached_path'])
                
                if is_activated:
                    state_tag = "Local"
                    state_icon = active_icon
                elif is_cached:
                    state_tag = "Cached"
                    state_icon = cached_icon
                else:
                    state_tag = "Remote"
                    state_icon = remote_icon
                
                # Apply filters
                should_hide = False
                if hasattr(self, 'filter_active_cb') and self.filter_active_cb.isChecked():
                    if not is_activated:
                        should_hide = True
                if hasattr(self, 'filter_recent_cb') and self.filter_recent_cb.isChecked():
                    if font['id'] not in recent_font_ids:
                        should_hide = True
                if collection_font_ids is not None:
                    if font['id'] not in collection_font_ids:
                        should_hide = True
                
                # Create preview text with state badge
                item_text = f"    {preview_text}    {style}    {font_format}    [{state_tag}]"
                item = QListWidgetItem(item_text)
                
                # Set status icon
                item.setIcon(state_icon)
                
                item.setData(Qt.UserRole, font['id'])
                item.setData(Qt.UserRole + 1, None)
                item.setData(Qt.UserRole + 2, font['cached_path'])
                item.setData(Qt.UserRole + 3, state_tag)  # Store state for filtering
                
                # Load and apply the actual font if cached
                if font['cached_path'] and os.path.exists(font['cached_path']):
                    font_id_qt = QFontDatabase.addApplicationFont(font['cached_path'])
                    if font_id_qt != -1:
                        font_families_qt = QFontDatabase.applicationFontFamilies(font_id_qt)
                        if font_families_qt:
                            font_size = self.get_font_preview_size()
                            custom_font = QFont(font_families_qt[0], font_size)
                            if font['ps_name']:
                                custom_font.setFamily(font_families_qt[0])
                                custom_font.setStyleName(style)
                            item.setFont(custom_font)
                
                # Hide based on filter or collapse setting
                self.fonts_list.addItem(item)
                # If any filter is active, show matching fonts (override collapse)
                any_filter_active = (
                    (hasattr(self, 'filter_active_cb') and self.filter_active_cb.isChecked()) or
                    (hasattr(self, 'filter_recent_cb') and self.filter_recent_cb.isChecked()) or
                    collection_font_ids is not None
                )
                if should_hide:
                    item.setHidden(True)
                elif any_filter_active:
                    item.setHidden(False)  # Show matching items even if collapsed by default
                else:
                    item.setHidden(collapse_by_default)
        
        # If filtering, auto-expand family headers with visible children and hide empty ones
        if (hasattr(self, 'filter_active_cb') and self.filter_active_cb.isChecked()) or \
           (hasattr(self, 'filter_recent_cb') and self.filter_recent_cb.isChecked()) or \
           collection_font_ids is not None:
            self._hide_empty_families()
            self._expand_families_with_visible_children()
        
        # Disconnect and reconnect to avoid duplicate connections
        try:
            self.fonts_list.itemClicked.disconnect(self.on_font_list_clicked)
        except:
            pass
        self.fonts_list.itemClicked.connect(self.on_font_list_clicked)
    
    def _hide_empty_families(self):
        """Hide family headers that have no visible children."""
        for i in range(self.fonts_list.count()):
            item = self.fonts_list.item(i)
            family_name = item.data(Qt.UserRole + 1)
            if family_name:
                # Check if any child fonts are visible
                has_visible = False
                j = i + 1
                while j < self.fonts_list.count():
                    child = self.fonts_list.item(j)
                    if child.data(Qt.UserRole + 1):  # Next family header
                        break
                    if not child.isHidden():
                        has_visible = True
                        break
                    j += 1
                item.setHidden(not has_visible)
    
    def _expand_families_with_visible_children(self):
        """Auto-expand family headers that have visible children (for filtering)."""
        for i in range(self.fonts_list.count()):
            item = self.fonts_list.item(i)
            family_name = item.data(Qt.UserRole + 1)
            if family_name and not item.isHidden():
                # If header shows ▶ (collapsed), switch to ▼ (expanded)
                text = item.text()
                if text.startswith("▶"):
                    item.setText(text.replace("▶", "▼", 1))
    
    def apply_filters(self):
        """Re-apply filters to the font list without full reload."""
        self.load_all_fonts()
    
    def _refresh_collection_filter(self):
        """Refresh the collection filter combo box with current collections."""
        if not hasattr(self, 'filter_collection_combo'):
            return
        current_data = self.filter_collection_combo.currentData()
        self.filter_collection_combo.clear()
        self.filter_collection_combo.addItem("All", None)
        collections = self.db.get_all_collections()
        for coll in collections:
            self.filter_collection_combo.addItem(coll['name'], coll['id'])
        # Restore previous selection if possible
        if current_data is not None:
            for i in range(self.filter_collection_combo.count()):
                if self.filter_collection_combo.itemData(i) == current_data:
                    self.filter_collection_combo.setCurrentIndex(i)
                    break
    
    def on_preview_text_changed(self, text):
        """Update preview text in font list with debounce."""
        # Debounce: reload after 500ms of no typing
        if hasattr(self, '_preview_timer'):
            self._preview_timer.stop()
        else:
            from PyQt5.QtCore import QTimer
            self._preview_timer = QTimer()
            self._preview_timer.setSingleShot(True)
            self._preview_timer.timeout.connect(self._apply_preview_text)
        self._preview_timer.start(500)
    
    def _apply_preview_text(self):
        """Apply the debounced preview text change."""
        text = self.preview_input.text()
        # Save to settings
        settings_file = APP_SUPPORT_DIR / "settings.json"
        settings = {}
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        settings['preview_text'] = text
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Reload fonts with new preview text
        self.load_all_fonts()
    
    def _load_preview_presets(self):
        """Load preview text presets into combo box."""
        self.preview_preset_combo.clear()
        self.preview_preset_combo.addItem("Select preset...", "")
        
        settings_file = APP_SUPPORT_DIR / "settings.json"
        settings = {}
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        
        default_presets = [
            "The quick brown fox jumps over the lazy dog",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "abcdefghijklmnopqrstuvwxyz",
            "0123456789",
            "ABCDEFGHIJKLM NOPQRSTUVWXYZ",
            "abcdefghijklm nopqrstuvwxyz",
        ]
        
        saved_presets = settings.get('preview_presets', [])
        all_presets = default_presets + [p for p in saved_presets if p not in default_presets]
        
        for preset in all_presets:
            self.preview_preset_combo.addItem(preset[:40] + "..." if len(preset) > 40 else preset, preset)
    
    def on_preset_selected(self, display_text):
        """Apply selected preset to preview input."""
        idx = self.preview_preset_combo.currentIndex()
        preset_text = self.preview_preset_combo.itemData(idx)
        if preset_text:
            self.preview_input.setText(preset_text)
    
    def on_save_preset(self):
        """Save current preview text as a preset."""
        text = self.preview_input.text().strip()
        if not text:
            return
        
        settings_file = APP_SUPPORT_DIR / "settings.json"
        settings = {}
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        
        presets = settings.get('preview_presets', [])
        if text not in presets:
            presets.append(text)
            settings['preview_presets'] = presets
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        
        self._load_preview_presets()
        self.status_bar.showMessage(f"Preview preset saved", 2000)
    
    def on_compare_fonts(self):
        """Open comparison dialog for selected fonts."""
        selected_items = self.fonts_list.selectedItems()
        if not selected_items:
            self.status_bar.showMessage("Select fonts to compare", 2000)
            return
        
        # Collect font data from selected items
        font_data = []
        for item in selected_items:
            font_id = item.data(Qt.UserRole)
            if font_id:  # Skip family headers
                font_db = self.db.get_font_by_id(font_id)
                if font_db:
                    font_data.append(font_db)
        
        if len(font_data) < 2:
            self.status_bar.showMessage("Select at least 2 fonts to compare", 2000)
            return
        
        if len(font_data) > 6:
            font_data = font_data[:6]
            self.status_bar.showMessage("Comparing first 6 selected fonts", 2000)
        
        self._show_comparison_dialog(font_data)
    
    def _show_comparison_dialog(self, font_data):
        """Show font comparison dialog with horizontal/vertical layout."""
        from PyQt5.QtGui import QFont, QFontDatabase
        from PyQt5.QtWidgets import QScrollArea, QGridLayout, QFrame, QSpinBox, QCheckBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Font Comparison")
        dialog.setMinimumWidth(900)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        # ── Controls bar ────────────────────────────
        controls_bar = QHBoxLayout()
        
        preview_label = QLabel("Preview:")
        compare_input = QLineEdit()
        compare_input.setText(self.preview_input.text() if hasattr(self, 'preview_input') else self.get_preview_text())
        
        size_label = QLabel("Size:")
        size_spinner = QSpinBox()
        size_spinner.setRange(6, 120)
        size_spinner.setValue(20)
        size_spinner.setSuffix(" pt")
        
        vertical_cb = QCheckBox("Vertical")
        vertical_cb.setChecked(False)
        
        controls_bar.addWidget(preview_label)
        controls_bar.addWidget(compare_input, 1)
        controls_bar.addWidget(size_label)
        controls_bar.addWidget(size_spinner)
        controls_bar.addWidget(vertical_cb)
        layout.addLayout(controls_bar)
        
        # ── Scroll area ────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Build font entries (name box + preview for each font)
        font_entries = []  # list of (name_label, preview_label, font_info)
        
        for font in font_data:
            # ── Narrow font name box ────────────────
            name_label = QLabel(f"  {font.get('family_name', '')} — {font.get('style_name', '')}  ")
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setFrameStyle(QFrame.Box | QFrame.Plain)
            name_label.setStyleSheet("""
                QLabel {
                    background: #00bcd4;
                    border: 1px solid #0097a7;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-weight: bold;
                    font-size: 11px;
                    color: #ffffff;
                    max-height: 24px;
                }
            """)
            name_label.setFixedHeight(26)
            name_label.setMaximumHeight(26)
            
            # ── Preview label ───────────────────────
            preview_label = QLabel(compare_input.text())
            preview_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            preview_label.setWordWrap(True)
            
            # Apply actual font if cached
            cached_path = font.get('cached_path', '')
            applied_family = None
            applied_style = font.get('style_name', '')
            if cached_path and os.path.exists(cached_path):
                font_id_qt = QFontDatabase.addApplicationFont(cached_path)
                if font_id_qt != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id_qt)
                    if font_families:
                        applied_family = font_families[0]
                        custom_font = QFont(applied_family, size_spinner.value())
                        if applied_style:
                            custom_font.setStyleName(applied_style)
                        preview_label.setFont(custom_font)
            
            preview_label.setMinimumWidth(150)
            font_entries.append({
                'name': name_label,
                'preview': preview_label,
                'family': applied_family,
                'style': applied_style,
            })
        
        # ── Layout builder ──────────────────────────
        def build_layout():
            # Clear existing widgets from container
            for entry in font_entries:
                entry['name'].setParent(None)
                entry['preview'].setParent(None)
            # Remove any leftover separator frames
            for child in container.findChildren(QFrame):
                child.setParent(None)
            # Clear layout items
            while container_layout.count():
                item = container_layout.takeAt(0)
                if item.layout():
                    while item.layout().count():
                        child = item.layout().takeAt(0)
                        if child.widget():
                            child.widget().setParent(None)
                    item.layout().setParent(None)
                elif item.widget():
                    item.widget().setParent(None)
            
            is_vertical = vertical_cb.isChecked()
            font_size = size_spinner.value()
            
            if is_vertical:
                # Vertical: each font stacked on top of each other
                for entry in font_entries:
                    row_layout = QVBoxLayout()
                    row_layout.setSpacing(2)
                    row_layout.setContentsMargins(4, 8, 4, 8)
                    row_layout.addWidget(entry['name'])
                    entry['preview'].setAlignment(Qt.AlignLeft | Qt.AlignTop)
                    row_layout.addWidget(entry['preview'], 1)
                    
                    # Separator frame
                    sep = QFrame()
                    sep.setFrameShape(QFrame.HLine)
                    sep.setFrameShadow(QFrame.Sunken)
                    row_layout.addWidget(sep)
                    
                    container_layout.addLayout(row_layout)
            else:
                # Horizontal: side by side in a grid
                grid = QGridLayout()
                grid.setSpacing(12)
                for col, entry in enumerate(font_entries):
                    entry['name'].setAlignment(Qt.AlignCenter)
                    grid.addWidget(entry['name'], 0, col)
                    entry['preview'].setAlignment(Qt.AlignCenter)
                    grid.addWidget(entry['preview'], 1, col)
                container_layout.addLayout(grid)
            
            # Update font sizes
            for entry in font_entries:
                if entry['family']:
                    custom_font = QFont(entry['family'], font_size)
                    if entry['style']:
                        custom_font.setStyleName(entry['style'])
                    entry['preview'].setFont(custom_font)
        
        container.setLayout(container_layout)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        
        # ── Close button ────────────────────────────
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        # ── Live updates ────────────────────────────
        def update_preview_text(text):
            for entry in font_entries:
                entry['preview'].setText(text)
        
        def update_font_size(val):
            for entry in font_entries:
                if entry['family']:
                    custom_font = QFont(entry['family'], val)
                    if entry['style']:
                        custom_font.setStyleName(entry['style'])
                    entry['preview'].setFont(custom_font)
        
        def toggle_layout():
            build_layout()
        
        compare_input.textChanged.connect(update_preview_text)
        size_spinner.valueChanged.connect(update_font_size)
        vertical_cb.stateChanged.connect(toggle_layout)
        
        # Initial build
        build_layout()
        
        dialog.setLayout(layout)
        dialog.exec_()
    
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
        elif tab_name == "Logs":
            self.refresh_logs()
    
    def update_fonts_tab_icons(self):
        """Update only the activation icons in Fonts tab without rebuilding."""
        from PyQt5.QtGui import QIcon
        assets_dir = Path(__file__).parent / "assets"
        active_icon = QIcon(str(assets_dir / "active.svg"))
        inactive_icon = QIcon(str(assets_dir / "inactive.svg"))
        cached_icon = QIcon(str(assets_dir / "cached.svg"))
        remote_icon = QIcon(str(assets_dir / "remote.svg"))
        
        user_fonts_dir = get_fonts_dir()
        
        for i in range(self.fonts_list.count()):
            item = self.fonts_list.item(i)
            font_id = item.data(Qt.UserRole)
            if font_id:  # Only update actual fonts, not family headers
                is_active = self.font_manager.is_font_active(font_id)
                if is_active:
                    item.setIcon(active_icon)
                else:
                    # Check cached state
                    state = item.data(Qt.UserRole + 3)
                    if state == "Cached":
                        item.setIcon(cached_icon)
                    else:
                        item.setIcon(remote_icon)
    
    def update_collection_fonts_icons(self):
        """Update only the activation icons in Collections tab without rebuilding."""
        from PyQt5.QtGui import QIcon
        assets_dir = Path(__file__).parent / "assets"
        active_icon = QIcon(str(assets_dir / "active.svg"))
        inactive_icon = QIcon(str(assets_dir / "inactive.svg"))
        cached_icon = QIcon(str(assets_dir / "cached.svg"))
        remote_icon = QIcon(str(assets_dir / "remote.svg"))
        
        for i in range(self.collection_fonts_list.count()):
            item = self.collection_fonts_list.item(i)
            item_type = item.data(Qt.UserRole + 1)
            if item_type == 'font':
                font_id = item.data(Qt.UserRole)
                if font_id:
                    is_active = self.font_manager.is_font_active(font_id)
                    if is_active:
                        item.setIcon(active_icon)
                    else:
                        state = item.data(Qt.UserRole + 3)
                        item.setIcon(cached_icon if state == "Cached" else remote_icon)
    
    def update_client_fonts_icons(self):
        """Update only the activation icons in Clients tab without rebuilding."""
        from PyQt5.QtGui import QIcon
        assets_dir = Path(__file__).parent / "assets"
        active_icon = QIcon(str(assets_dir / "active.svg"))
        inactive_icon = QIcon(str(assets_dir / "inactive.svg"))
        cached_icon = QIcon(str(assets_dir / "cached.svg"))
        remote_icon = QIcon(str(assets_dir / "remote.svg"))
        
        for i in range(self.client_fonts_list.count()):
            item = self.client_fonts_list.item(i)
            font_id = item.data(Qt.UserRole)
            if font_id:  # Only update actual fonts, not family headers
                is_active = self.font_manager.is_font_active(font_id)
                if is_active:
                    item.setIcon(active_icon)
                else:
                    state = item.data(Qt.UserRole + 3)
                    item.setIcon(cached_icon if state == "Cached" else remote_icon)
    
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
                params={"limit": 1000},
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
                collapse_icon = "▼" if not collapse_by_default else "▶"
                family_item = QListWidgetItem(f"{collapse_icon} {family_name} ({len(fonts)} styles) - {format_type}")
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
                    user_fonts_dir = get_fonts_dir()
                    filename = font.get('filename_original', '')
                    is_activated = (user_fonts_dir / filename).exists() if filename else False
                    
                    preview_text = self.get_preview_text()
                    item_text = f"{preview_text}    {style}    {font_format}"
                    font_item = QListWidgetItem(item_text)
                    
                    # Add status icon based on state
                    from PyQt5.QtGui import QIcon
                    assets_dir = Path(__file__).parent / "assets"
                    if is_activated:
                        font_item.setIcon(QIcon(str(assets_dir / "active.svg")))
                        state_tag = "Local"
                    elif cached_path and os.path.exists(cached_path):
                        font_item.setIcon(QIcon(str(assets_dir / "cached.svg")))
                        state_tag = "Cached"
                    else:
                        font_item.setIcon(QIcon(str(assets_dir / "remote.svg")))
                        state_tag = "Remote"
                    
                    item_text = f"{preview_text}    {style}    {font_format}    [{state_tag}]"
                    font_item.setText(item_text)
                    
                    font_item.setData(Qt.UserRole, font['id'])
                    font_item.setData(Qt.UserRole + 1, None)
                    font_item.setData(Qt.UserRole + 3, state_tag)
                    
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

        # Get fonts in this collection grouped by family
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

        if not fonts:
            return

        self._show_fonts_by_family(fonts)
    
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
            assets_dir = Path(__file__).parent / "assets"
            active_icon = QIcon(str(assets_dir / "active.svg"))
            cached_icon = QIcon(str(assets_dir / "cached.svg"))
            remote_icon = QIcon(str(assets_dir / "remote.svg"))
            
            # Add family groups
            for family_name in sorted(families.keys()):
                family_fonts = families[family_name]
                ext = ''
                font_db_entry = self.db.get_font_by_id(family_fonts[0][0]) if family_fonts else None
                if font_db_entry:
                    ext = font_db_entry.get('extension', '')
                format_type = 'TrueType' if ext in ['.ttf', '.ttc'] else 'OpenType' if ext == '.otf' else ''
                
                # Add family header
                icon = "▼" if not collapse_by_default else "▶"
                header_text = f"{icon} {family_name} ({len(family_fonts)} styles)"
                if format_type:
                    header_text += f" - {format_type}"
                family_item = QListWidgetItem(header_text)
                family_item.setData(Qt.UserRole, None)
                family_item.setData(Qt.UserRole + 1, family_name)  # Family name identifies header
                family_item.setBackground(Qt.lightGray)
                font = QFont()
                font.setBold(True)
                family_item.setFont(font)
                self.collection_fonts_list.addItem(family_item)
                
                # Add individual fonts (initially hidden)
                for font_data in family_fonts:
                    font_id, postscript_name, style_name, _ = font_data
                    
                    # Determine state
                    user_fonts_dir = get_fonts_dir()
                    font_db = self.db.get_font_by_id(font_id)
                    cached_path = font_db.get('cached_path') if font_db else None
                    filename = font_db.get('filename_original', '') if font_db else ''
                    is_activated = (user_fonts_dir / filename).exists() if filename else False
                    
                    if is_activated:
                        icon = active_icon
                        state_tag = "Local"
                    elif cached_path and os.path.exists(cached_path):
                        icon = cached_icon
                        state_tag = "Cached"
                    else:
                        icon = remote_icon
                        state_tag = "Remote"
                    
                    display_style = style_name or postscript_name or 'Unknown'
                    preview_text = self.get_preview_text()
                    font_format = 'TrueType' if ext in ['.ttf', '.ttc'] else 'OpenType' if ext == '.otf' else ext
                    item_text = f"{preview_text}    {display_style}    {font_format}    [{state_tag}]"
                    
                    font_item = QListWidgetItem(icon, item_text)
                    font_item.setData(Qt.UserRole, font_id)
                    font_item.setData(Qt.UserRole + 1, None)  # None = font item (not a header)
                    font_item.setData(Qt.UserRole + 3, state_tag)
                    
                    # Apply font preview if cached
                    if cached_path and os.path.exists(cached_path):
                        from PyQt5.QtGui import QFontDatabase
                        font_id_qt = QFontDatabase.addApplicationFont(cached_path)
                        if font_id_qt != -1:
                            font_families_qt = QFontDatabase.applicationFontFamilies(font_id_qt)
                            if font_families_qt:
                                font_size = self.get_font_preview_size()
                                custom_font = QFont(font_families_qt[0], font_size)
                                if style_name:
                                    custom_font.setStyleName(style_name)
                                font_item.setFont(custom_font)
                    
                    self.collection_fonts_list.addItem(font_item)
                    font_item.setHidden(collapse_by_default)  # Must be after addItem
        
        except Exception as e:
            self.status_bar.showMessage(f"Error loading fonts: {str(e)}", 5000)
    
    def on_collection_font_clicked(self, item):
        family_name = item.data(Qt.UserRole + 1)
        
        if family_name:
            # Family header clicked - toggle expand/collapse
            is_expanded = item.text().startswith("▼")
            new_icon = "▶" if is_expanded else "▼"
            item.setText(item.text().replace("▶" if not is_expanded else "▼", new_icon, 1))
            
            # Walk forward from this item, toggling visibility until next header
            current_index = self.collection_fonts_list.row(item)
            i = current_index + 1
            while i < self.collection_fonts_list.count():
                next_item = self.collection_fonts_list.item(i)
                if next_item.data(Qt.UserRole + 1):  # Hit next family header
                    break
                next_item.setHidden(is_expanded)
                i += 1
        
        else:
            # Font item clicked - toggle activation
            font_id = item.data(Qt.UserRole)
            if font_id:
                is_active = self.font_manager.is_font_active(font_id)
                
                try:
                    if is_active:
                        result = self.font_manager.deactivate_font(font_id)
                        self.status_bar.showMessage(result.get('message', 'Font deactivated'), 2000)
                    else:
                        result = self.font_manager.activate_font(font_id)
                        self.status_bar.showMessage(result.get('message', 'Font activated'), 2000)
                    
                    # Reload all tabs to sync status
                    self.reload_all_tabs()
                except Exception as e:
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
        self._set_connection_state("connecting")
        
        self.sync_thread = SyncThread(self.font_manager)
        self.sync_thread.finished.connect(self.on_sync_finished)
        self.sync_thread.error.connect(self.on_sync_error)
        self.sync_thread.start()
    
    def on_sync_finished(self, result):
        self.load_collections()
        self.load_clients()  # Reload clients list to show new clients
        self._refresh_collection_filter()  # Update filter combo with new collections
        
        # Update connection state and sync time
        self._set_connection_state("connected")
        self._last_sync_time = datetime.now()
        self._save_last_sync_time()
        self._refresh_sync_time()
        self._refresh_cache_count()
        
        # Auto-download fonts in background if there are new ones
        if result['fonts'] > 0:
            self.status_bar.showMessage(f"Synced {result['fonts']} fonts. Downloading...")
            self.download_all_fonts()
        else:
            self.status_bar.showMessage(f"Sync complete: {result['fonts']} fonts, {result['collections']} collections, {result['clients']} clients", 3000)
            self.sync_button.setEnabled(True)
    
    def on_sync_error(self, error):
        self.status_bar.showMessage(f"Sync failed: {error} — working offline", 5000)
        self.sync_button.setEnabled(True)
        self._set_connection_state("disconnected")
        # Still load fonts from local DB so UI isn't empty
        self.load_all_fonts()
        self.load_recent()
    
    def _set_connection_state(self, state):
        """Update the connection indicator in the status bar."""
        if state == "connected":
            self.connection_label.setText("● Connected")
            self.connection_label.setStyleSheet("color: #22c55e; font-weight: bold; padding: 0 8px;")
        elif state == "connecting":
            self.connection_label.setText("● Connecting...")
            self.connection_label.setStyleSheet("color: #f97316; font-weight: bold; padding: 0 8px;")
        else:  # disconnected
            self.connection_label.setText("● Disconnected")
            self.connection_label.setStyleSheet("color: #ef4444; font-weight: bold; padding: 0 8px;")
    
    def _refresh_sync_time(self):
        """Update the 'last sync' label with relative time."""
        if self._last_sync_time:
            delta = datetime.now() - self._last_sync_time
            seconds = int(delta.total_seconds())
            if seconds < 60:
                text = "Last sync: just now"
            elif seconds < 3600:
                text = f"Last sync: {seconds // 60} mins ago"
            elif seconds < 86400:
                text = f"Last sync: {seconds // 3600} hours ago"
            else:
                text = f"Last sync: {seconds // 86400} days ago"
            self.last_sync_label.setText(text)
        else:
            self.last_sync_label.setText("Last sync: never")
    
    def _refresh_cache_count(self):
        """Update the cache count label."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fonts WHERE cached = 1 OR (cached_path IS NOT NULL AND cached_path != '')")
            count = cursor.fetchone()[0]
            conn.close()
            self.cache_count_label.setText(f"{count} fonts cached")
        except Exception:
            self.cache_count_label.setText("? fonts cached")
    
    def _load_last_sync_time(self):
        """Load last sync time from settings."""
        settings_file = APP_SUPPORT_DIR / "settings.json"
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                ts = settings.get('last_sync_time')
                if ts:
                    self._last_sync_time = datetime.fromisoformat(ts)
                    self._refresh_sync_time()
        
        # Also refresh cache count on startup
        self._refresh_cache_count()
    
    def _save_last_sync_time(self):
        """Save last sync time to settings."""
        settings_file = APP_SUPPORT_DIR / "settings.json"
        settings = {}
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        settings['last_sync_time'] = self._last_sync_time.isoformat() if self._last_sync_time else None
        # Also save last known good URL
        settings['last_known_good_url'] = self.api.server_url if hasattr(self, 'api') else ''
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    
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
        """Find fonts in the database using smart multi-field matching.
        Returns list of (id, postscript_name, family_name, style_name) tuples."""
        # Use smart matching - tries PostScript, family+style, full_name, family, fuzzy
        results = self.db.smart_match_font(
            postscript_name=font_name,
            family=font_name
        )
        
        # Convert dicts to tuples for backward compatibility
        return [(f['id'], f['postscript_name'], f['family_name'], f['style_name']) for f in results]
    
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
                self._load_system_fonts()  # Refresh system fonts (collapse setting may have changed)
                
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
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Logout")
        msg.setText("Are you sure you want to logout?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        reply = msg.exec_()
        
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
