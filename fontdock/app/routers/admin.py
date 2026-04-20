"""Admin router for server management."""
import subprocess
import threading
import os
import json
import shutil
import glob
import logging
import zipfile
import tempfile
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from app.routers.auth import get_current_admin
from app.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

logger = logging.getLogger(__name__)

LOG_FILE_PATH = "logs/fontdock.log"
BACKUP_DIR = "backups"
MAX_BACKUPS = 2
BACKUP_SETTINGS_FILE = "backup_settings.json"

# Valid schedule values and their intervals in seconds
SCHEDULE_INTERVALS = {
    "never": None,
    "daily": 86400,
    "weekly": 86400 * 7,
    "monthly": 86400 * 30,
}
DEFAULT_SCHEDULE = "weekly"


def _get_db_path() -> str:
    """Get the database file path from settings."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        path = db_url[len("sqlite:///"):]
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        return path
    return None


def _get_storage_path() -> str:
    """Get the font storage path from settings."""
    settings = get_settings()
    path = str(settings.storage_path)
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return path


def _ensure_backup_dir():
    """Create backup directory if it doesn't exist."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _load_backup_settings() -> dict:
    """Load backup schedule settings from JSON file."""
    defaults = {"schedule": DEFAULT_SCHEDULE, "last_backup": None}
    if os.path.exists(BACKUP_SETTINGS_FILE):
        try:
            with open(BACKUP_SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults


def _save_backup_settings(settings: dict):
    """Save backup schedule settings to JSON file."""
    with open(BACKUP_SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)


def _prune_old_backups():
    """Keep only the most recent MAX_BACKUPS backup files."""
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "fontdock_*.zip")), key=os.path.getmtime)
    while len(backups) > MAX_BACKUPS:
        oldest = backups.pop(0)
        os.remove(oldest)
        logger.info(f"Pruned old backup: {os.path.basename(oldest)}")


def _create_backup_zip() -> str:
    """Create a ZIP backup containing database + font storage. Returns the zip path."""
    _ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(BACKUP_DIR, f"fontdock_{timestamp}.zip")
    
    db_path = _get_db_path()
    storage_path = _get_storage_path()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add database
        if db_path and os.path.exists(db_path):
            zf.write(db_path, "fontdock.db")
            logger.info(f"Backed up database: {db_path}")
        
        # Add font storage
        if os.path.isdir(storage_path):
            for root, dirs, files in os.walk(storage_path):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    arcname = os.path.relpath(full_path, os.path.dirname(storage_path))
                    zf.write(full_path, arcname)
            font_count = sum(len(f) for _, _, f in os.walk(storage_path))
            logger.info(f"Backed up {font_count} font files from storage")
    
    _prune_old_backups()
    return zip_path


def run_restart_script():
    """Run restart script in background."""
    subprocess.Popen(
        ["bash", "scripts/restart.sh"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# ── Scheduled Backup ──────────────────────────────────────────────

def auto_backup_check():
    """Create a backup if the schedule says it's due."""
    settings = _load_backup_settings()
    schedule = settings.get("schedule", DEFAULT_SCHEDULE)
    
    if schedule == "never":
        return
    
    interval = SCHEDULE_INTERVALS.get(schedule)
    if interval is None:
        return
    
    # Check if a backup is due
    last_backup_str = settings.get("last_backup")
    if last_backup_str:
        try:
            last_backup = datetime.fromisoformat(last_backup_str)
            if (datetime.now() - last_backup).total_seconds() < interval:
                return  # Not due yet
        except Exception:
            pass
    
    try:
        zip_path = _create_backup_zip()
        settings["last_backup"] = datetime.now().isoformat()
        _save_backup_settings(settings)
        logger.info(f"Auto-backup created: {os.path.basename(zip_path)}")
    except Exception as e:
        logger.error(f"Auto-backup failed: {e}")


def start_backup_scheduler():
    """Start periodic backup check thread."""
    def _scheduler():
        import time
        while True:
            time.sleep(3600)  # Check every hour
            auto_backup_check()
    
    thread = threading.Thread(target=_scheduler, daemon=True)
    thread.start()
    # Run initial check
    auto_backup_check()


# ── Server Management ──────────────────────────────────────────────

@router.post("/restart-script")
async def restart_server_script(
    current_user = Depends(get_current_admin),
):
    """Restart the server using shell script."""
    try:
        thread = threading.Thread(target=run_restart_script, daemon=True)
        thread.start()
        return {"success": True, "message": "Server restart initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart server: {str(e)}")


# ── Logs ──────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(
    current_user = Depends(get_current_admin),
) -> dict:
    """Get server logs."""
    try:
        if not os.path.exists(LOG_FILE_PATH):
            return {"logs": [], "message": "No logs found"}
        with open(LOG_FILE_PATH, "r") as f:
            lines = f.readlines()
            logs = [line.rstrip() for line in lines[-500:]]
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@router.delete("/logs")
async def clear_logs(
    current_user = Depends(get_current_admin),
) -> dict:
    """Clear server logs."""
    try:
        if os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, "w") as f:
                f.write("")
        return {"success": True, "message": "Logs cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")


# ── Backup Settings ───────────────────────────────────────────────

@router.get("/backup-settings")
async def get_backup_settings(
    current_user = Depends(get_current_admin),
) -> dict:
    """Get current backup schedule settings."""
    settings = _load_backup_settings()
    return {
        "schedule": settings.get("schedule", DEFAULT_SCHEDULE),
        "last_backup": settings.get("last_backup"),
        "max_backups": MAX_BACKUPS,
        "available_schedules": list(SCHEDULE_INTERVALS.keys()),
    }


@router.put("/backup-settings")
async def update_backup_settings(
    schedule: str,
    current_user = Depends(get_current_admin),
) -> dict:
    """Update backup schedule. Options: never, daily, weekly, monthly."""
    if schedule not in SCHEDULE_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule. Must be one of: {', '.join(SCHEDULE_INTERVALS.keys())}"
        )
    
    settings = _load_backup_settings()
    settings["schedule"] = schedule
    _save_backup_settings(settings)
    logger.info(f"[AUDIT] Backup schedule changed to '{schedule}', admin='{current_user.username}'")
    
    return {
        "success": True,
        "schedule": schedule,
        "message": f"Backup schedule set to {schedule}",
    }


# ── Backup & Restore (ZIP) ────────────────────────────────────────

@router.post("/backup")
async def create_backup(
    current_user = Depends(get_current_admin),
) -> dict:
    """Create a full backup (database + fonts) as a ZIP file."""
    db_path = _get_db_path()
    if not db_path or not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="No database file found")
    
    try:
        zip_path = _create_backup_zip()
        
        # Update last_backup timestamp
        settings = _load_backup_settings()
        settings["last_backup"] = datetime.now().isoformat()
        _save_backup_settings(settings)
        
        logger.info(f"[AUDIT] Manual backup created: {os.path.basename(zip_path)}, admin='{current_user.username}'")
        return {
            "success": True,
            "message": "Full backup created",
            "backup_file": os.path.basename(zip_path),
            "backup_path": zip_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/backups")
async def list_backups(
    current_user = Depends(get_current_admin),
) -> dict:
    """List available backup ZIP files."""
    _ensure_backup_dir()
    
    backups = []
    for f in sorted(glob.glob(os.path.join(BACKUP_DIR, "fontdock_*.zip")), reverse=True):
        stat = os.stat(f)
        backups.append({
            "filename": os.path.basename(f),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    
    return {"backups": backups, "total": len(backups)}


@router.get("/backups/{filename}")
async def download_backup(
    filename: str,
    current_user = Depends(get_current_admin),
):
    """Download a specific backup ZIP file."""
    safe_name = os.path.basename(filename)
    backup_path = os.path.join(BACKUP_DIR, safe_name)
    
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup not found")
    
    return FileResponse(
        backup_path,
        media_type="application/zip",
        filename=safe_name,
    )


@router.post("/restore")
async def restore_backup(
    filename: str,
    current_user = Depends(get_current_admin),
) -> dict:
    """Restore from a backup ZIP file. Server will restart."""
    db_path = _get_db_path()
    storage_path = _get_storage_path()
    if not db_path:
        raise HTTPException(status_code=400, detail="Cannot determine database path (non-SQLite?)")
    
    safe_name = os.path.basename(filename)
    backup_path = os.path.join(BACKUP_DIR, safe_name)
    
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(tmp)
            
            # Restore database
            extracted_db = os.path.join(tmp, "fontdock.db")
            if os.path.exists(extracted_db):
                shutil.copy2(extracted_db, db_path)
            
            # Restore font storage
            extracted_storage = os.path.join(tmp, "fonts")
            if os.path.exists(extracted_storage):
                if os.path.exists(storage_path):
                    shutil.rmtree(storage_path)
                shutil.copytree(extracted_storage, storage_path)
        
        logger.info(f"[AUDIT] Full restore from: {safe_name}, admin='{current_user.username}'")
        
        thread = threading.Thread(target=run_restart_script, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Full restore complete. Server restarting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.post("/restore-upload")
async def restore_from_upload(
    file: UploadFile = File(...),
    current_user = Depends(get_current_admin),
) -> dict:
    """Restore from an uploaded ZIP backup. Server will restart."""
    db_path = _get_db_path()
    storage_path = _get_storage_path()
    if not db_path:
        raise HTTPException(status_code=400, detail="Cannot determine database path (non-SQLite?)")
    
    try:
        content = await file.read()
        
        with tempfile.TemporaryDirectory() as tmp:
            # Save uploaded file to temp
            temp_zip = os.path.join(tmp, "upload.zip")
            with open(temp_zip, "wb") as f:
                f.write(content)
            
            # Extract
            extract_dir = os.path.join(tmp, "extracted")
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                zf.extractall(extract_dir)
            
            # Restore database
            extracted_db = os.path.join(extract_dir, "fontdock.db")
            if os.path.exists(extracted_db):
                shutil.copy2(extracted_db, db_path)
            
            # Restore font storage
            extracted_storage = os.path.join(extract_dir, "fonts")
            if os.path.exists(extracted_storage):
                if os.path.exists(storage_path):
                    shutil.rmtree(storage_path)
                shutil.copytree(extracted_storage, storage_path)
        
        logger.info(f"[AUDIT] Full restore from upload: {file.filename}, admin='{current_user.username}'")
        
        thread = threading.Thread(target=run_restart_script, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Full restore from upload complete. Server restarting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.delete("/backups/{filename}")
async def delete_backup(
    filename: str,
    current_user = Depends(get_current_admin),
) -> dict:
    """Delete a specific backup file."""
    safe_name = os.path.basename(filename)
    backup_path = os.path.join(BACKUP_DIR, safe_name)
    
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        os.remove(backup_path)
        return {"success": True, "message": f"Backup {safe_name} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
