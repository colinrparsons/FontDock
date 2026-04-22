"""Users router (admin only)."""
import logging
import csv
import io
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import Response
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


@router.post("/import-csv")
async def bulk_import_users(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Bulk import users from a CSV file (admin only).
    
    CSV must have header row with columns:
    - username, email, password (required)
    - first_name, last_name (optional)
    - is_admin, can_create_users, can_delete_users, can_upload_fonts,
      can_download_fonts, can_delete_fonts, can_create_collections, can_create_clients (optional, true/false)
    """
    from app.services.auth_service import get_user_by_username, get_user_by_email
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV (.csv)"
        )
    
    content = await file.read()
    text = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))
    
    success = 0
    failed = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):  # Row 2 = first data row (1 is header)
        username = row.get("username", "").strip()
        email = row.get("email", "").strip()
        password = row.get("password", "").strip()
        
        if not username or not email or not password:
            failed += 1
            errors.append(f"Row {row_num}: Missing required field(s)")
            continue
        
        # Check for duplicate username
        if get_user_by_username(db, username):
            failed += 1
            errors.append(f"Row {row_num}: Username '{username}' already exists")
            continue
        
        # Check for duplicate email
        if get_user_by_email(db, email):
            failed += 1
            errors.append(f"Row {row_num}: Email '{email}' already exists")
            continue
        
        def parse_bool(val, default=False):
            if val is None:
                return default
            return val.strip().lower() in ('true', '1', 'yes')
        
        try:
            new_user = create_user(
                db,
                username=username,
                email=email,
                password=password,
                first_name=row.get("first_name", "").strip() or None,
                last_name=row.get("last_name", "").strip() or None,
                is_admin=parse_bool(row.get("is_admin")),
                can_create_users=parse_bool(row.get("can_create_users")),
                can_delete_users=parse_bool(row.get("can_delete_users")),
                can_upload_fonts=parse_bool(row.get("can_upload_fonts")),
                can_download_fonts=parse_bool(row.get("can_download_fonts"), default=True),
                can_delete_fonts=parse_bool(row.get("can_delete_fonts")),
                can_create_collections=parse_bool(row.get("can_create_collections")),
                can_create_clients=parse_bool(row.get("can_create_clients")),
            )
            success += 1
            logger.info(f"[AUDIT] Bulk import created user: ID={new_user.id}, username='{new_user.username}', admin='{current_user.username}'")
        except Exception as e:
            failed += 1
            errors.append(f"Row {row_num} ({username}): {str(e)}")
    
    result = {
        "success": True,
        "imported": success,
        "failed": failed,
        "total": success + failed,
    }
    if errors:
        result["errors"] = errors[:20]  # Cap at 20 errors in response
    
    return result


@router.get("/import-template")
async def download_csv_template(
    current_user = Depends(get_current_admin),
):
    """Download a CSV template for bulk user import."""
    header = "first_name,last_name,username,email,password,is_admin,can_create_users,can_delete_users,can_upload_fonts,can_download_fonts,can_delete_fonts,can_create_collections,can_create_clients"
    
    example_rows = [
        "John,Doe,jdoe,jdoe@company.com,ChangeMe123,false,false,false,true,true,false,false,false",
        "Admin,User,admin,admin@company.com,AdminPass456,true,true,true,true,true,true,true,true",
        "Jane,Designer,designer,designer@company.com,DesignPass789,false,false,false,true,true,false,false,false",
    ]
    
    csv_content = header + "\n" + "\n".join(example_rows) + "\n"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fontdock_users_template.csv"}
    )


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
    
    # Auto-grant all permissions for admin users
    if data.is_admin:
        perms = {
            'can_create_users': True,
            'can_delete_users': True,
            'can_upload_fonts': True,
            'can_download_fonts': True,
            'can_delete_fonts': True,
            'can_create_collections': True,
            'can_create_clients': True,
        }
    else:
        perms = {
            'can_create_users': data.can_create_users,
            'can_delete_users': data.can_delete_users,
            'can_upload_fonts': data.can_upload_fonts,
            'can_download_fonts': data.can_download_fonts,
            'can_delete_fonts': data.can_delete_fonts,
            'can_create_collections': data.can_create_collections,
            'can_create_clients': data.can_create_clients,
        }
    
    new_user = create_user(
        db,
        username=data.username,
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        is_admin=data.is_admin,
        **perms,
    )
    
    # Assign user to groups if specified
    if data.group_ids:
        from app.models import Group as GroupModel
        groups = db.query(GroupModel).filter(GroupModel.id.in_(data.group_ids)).all()
        for group in groups:
            group.users.append(new_user)
        db.commit()
    
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
        # Auto-grant all permissions when setting user as admin
        if data.is_admin:
            user.can_create_users = True
            user.can_delete_users = True
            user.can_upload_fonts = True
            user.can_download_fonts = True
            user.can_delete_fonts = True
            user.can_create_collections = True
            user.can_create_clients = True
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
