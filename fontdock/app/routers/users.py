"""Users router (admin only)."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import User, UserCreate, UserUpdate, UserList
from app.routers.auth import get_current_user, get_current_admin
from app.services.auth_service import create_user

router = APIRouter(prefix="/api/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.get("", response_model=UserList)
async def list_users(
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List users (admin only)."""
    from app.models import User as UserModel
    
    query = db.query(UserModel)
    
    if is_active is not None:
        query = query.filter(UserModel.is_active == is_active)
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return UserList(items=users, total=total)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get user by ID (admin only)."""
    from app.models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


@router.post("", response_model=User)
async def create_new_user(
    data: UserCreate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)."""
    from app.services.auth_service import get_user_by_username, get_user_by_email
    
    # Check for duplicate username
    existing = get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{data.username}' already exists",
        )
    
    # Check for duplicate email
    existing = get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{data.email}' already exists",
        )
    
    new_user = create_user(
        db,
        username=data.username,
        email=data.email,
        password=data.password,
        is_admin=data.is_admin,
        can_create_users=data.can_create_users,
        can_delete_users=data.can_delete_users,
        can_upload_fonts=data.can_upload_fonts,
        can_download_fonts=data.can_download_fonts,
        can_create_collections=data.can_create_collections,
        can_create_clients=data.can_create_clients,
    )
    logger.info(f"[AUDIT] User created: ID={new_user.id}, username='{new_user.username}', admin='{current_user.username}'")
    
    return new_user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a user (admin only)."""
    from app.models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if data.email is not None:
        user.email = data.email
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.can_create_users is not None:
        user.can_create_users = data.can_create_users
    if data.can_delete_users is not None:
        user.can_delete_users = data.can_delete_users
    if data.can_upload_fonts is not None:
        user.can_upload_fonts = data.can_upload_fonts
    if data.can_download_fonts is not None:
        user.can_download_fonts = data.can_download_fonts
    if data.can_create_collections is not None:
        user.can_create_collections = data.can_create_collections
    if data.can_create_clients is not None:
        user.can_create_clients = data.can_create_clients
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a user from the database (admin only)."""
    from app.models import User as UserModel, FontUsageEvent, UserSession, UserClientPermission
    
    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Delete related records first to avoid foreign key constraints
    db.query(FontUsageEvent).filter(FontUsageEvent.user_id == user_id).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == user_id).delete(synchronize_session=False)
    db.query(UserClientPermission).filter(UserClientPermission.user_id == user_id).delete(synchronize_session=False)
    
    # Permanently delete user
    db.delete(user)
    db.commit()
    logger.info(f"[AUDIT] User deleted: ID={user_id}, username='{user.username}', admin='{current_user.username}'")
    
    return {"success": True, "message": "User deleted permanently"}


@router.post("/admin/restart")
async def restart_server(
    current_user: dict = Depends(get_current_admin),
):
    """Restart the server (admin only)."""
    import os
    import sys
    import subprocess
    
    # Schedule restart after response is sent
    def delayed_restart():
        import time
        time.sleep(1)
        # Use the same Python executable and script
        subprocess.Popen([sys.executable, "run.py"])
        # Exit current process
        os._exit(0)
    
    import threading
    threading.Thread(target=delayed_restart, daemon=True).start()
    
    return {"success": True, "message": "Server restarting..."}
