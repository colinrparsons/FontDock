"""Platform-specific abstraction for FontDock client.

Provides a unified interface for macOS and Windows operations:
- Font activation/deactivation paths
- App data directories
- Adobe app detection and document querying
- Font extraction from files
"""

import sys

IS_MACOS = sys.platform == 'darwin'
IS_WINDOWS = sys.platform == 'win32'

if IS_MACOS:
    from fontdock_platform.macos import (
        get_app_support_dir,
        get_cache_dir,
        get_fonts_dir,
        get_db_path,
        get_log_path,
        get_request_dir,
        is_app_running,
        get_open_documents,
        get_photoshop_font_names,
        detect_installed_apps,
        extract_fonts_from_file,
        get_adobe_startup_dir,
    )
elif IS_WINDOWS:
    from fontdock_platform.windows import (
        get_app_support_dir,
        get_cache_dir,
        get_fonts_dir,
        get_db_path,
        get_log_path,
        get_request_dir,
        is_app_running,
        get_open_documents,
        get_photoshop_font_names,
        detect_installed_apps,
        extract_fonts_from_file,
        get_adobe_startup_dir,
    )
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
