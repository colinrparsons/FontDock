"""Password change router."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.services.auth_service import verify_password, get_password_hash
from app.dependencies import templates

router = APIRouter(prefix="/change-password", tags=["password"])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


@router.get("", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Show password change form."""
    return templates.TemplateResponse(
        "change_password.html",
        {"request": request, "user": current_user}
    )


@router.post("")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if len(password_data.new_password) > 72:
        raise HTTPException(status_code=400, detail="Password must be less than 72 characters")
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
