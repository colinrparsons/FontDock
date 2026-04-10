"""Admin router for server management."""
import subprocess
import threading
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])

LOG_FILE_PATH = "logs/fontdock.log"


def run_restart_script():
    """Run restart script in background."""
    subprocess.Popen(
        ["bash", "scripts/restart.sh"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


@router.post("/restart-script")
async def restart_server_script(
    current_user = Depends(get_current_admin),
):
    """Restart the server using shell script."""
    try:
        # Start restart in background thread (don't wait for completion)
        thread = threading.Thread(target=run_restart_script, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "message": "Server restart initiated"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart server: {str(e)}"
        )


@router.get("/logs")
async def get_logs(
    current_user = Depends(get_current_admin),
) -> dict:
    """Get server logs."""
    try:
        if not os.path.exists(LOG_FILE_PATH):
            return {"logs": [], "message": "No logs found"}
        
        with open(LOG_FILE_PATH, "r") as f:
            # Read last 500 lines
            lines = f.readlines()
            logs = [line.rstrip() for line in lines[-500:]]
        
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read logs: {str(e)}"
        )


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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear logs: {str(e)}"
        )
