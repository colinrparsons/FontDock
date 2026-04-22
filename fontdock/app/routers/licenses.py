"""Font licenses API router — upload, download, and manage license files per font."""
import datetime
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Font as FontModel, FontLicense as FontLicenseModel
from app.schemas import FontLicenseSchema, FontLicenseList, FontLicenseUpdate
from app.routers.auth import get_current_user, get_current_admin


router = APIRouter(prefix="/api/fonts/{font_id}/licenses", tags=["licenses"])


def get_license_storage_path() -> Path:
    """Get or create the license storage directory."""
    storage_path = Path("./storage/licenses")
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def validate_font_access(font_id: int, db: Session) -> FontModel:
    """Validate font exists and return it."""
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    return font


@router.get("", response_model=FontLicenseList)
async def list_licenses(
    font_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all licenses for a font."""
    validate_font_access(font_id, db)
    
    licenses = db.query(FontLicenseModel).filter(
        FontLicenseModel.font_id == font_id
    ).order_by(FontLicenseModel.created_at.desc()).all()
    
    return FontLicenseList(items=licenses, total=len(licenses))


@router.post("", response_model=FontLicenseSchema, status_code=status.HTTP_201_CREATED)
async def upload_license(
    font_id: int,
    file: UploadFile = File(..., description="License file (text, PDF, etc.)"),
    license_type: Optional[str] = Form(None),
    license_key: Optional[str] = Form(None),
    seat_count: Optional[int] = Form(None),
    expiry_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Upload a license file for a font (admin only)."""
    font = validate_font_access(font_id, db)
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB max for license files
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License file too large (max 10MB)",
        )
    
    # Generate storage filename
    ext = Path(file.filename).suffix or ".txt"
    storage_name = f"{uuid.uuid4().hex}{ext}"
    storage_path = get_license_storage_path() / storage_name
    
    # Save file
    with open(storage_path, "wb") as f:
        f.write(content)
    
    # Parse expiry date
    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = datetime.date.fromisoformat(expiry_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid expiry date format: {expiry_date}. Use YYYY-MM-DD.",
            )
    
    # Create license record
    license_record = FontLicenseModel(
        font_id=font_id,
        license_type=license_type,
        license_key=license_key,
        seat_count=seat_count,
        expiry_date=parsed_expiry,
        notes=notes,
        filename_original=file.filename,
        filename_storage=storage_name,
        storage_path=str(storage_path),
    )
    db.add(license_record)
    db.commit()
    db.refresh(license_record)
    
    return license_record


@router.get("/{license_id}", response_model=FontLicenseSchema)
async def get_license(
    font_id: int,
    license_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get license details."""
    validate_font_access(font_id, db)
    
    license_record = db.query(FontLicenseModel).filter(
        FontLicenseModel.id == license_id,
        FontLicenseModel.font_id == font_id,
    ).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    
    return license_record


@router.get("/{license_id}/download")
async def download_license(
    font_id: int,
    license_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a license file."""
    validate_font_access(font_id, db)
    
    license_record = db.query(FontLicenseModel).filter(
        FontLicenseModel.id == license_id,
        FontLicenseModel.font_id == font_id,
    ).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    
    file_path = Path(license_record.storage_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License file not found on disk",
        )
    
    return FileResponse(
        path=file_path,
        filename=license_record.filename_original,
        media_type="application/octet-stream",
    )


@router.put("/{license_id}", response_model=FontLicenseSchema)
async def update_license(
    font_id: int,
    license_id: int,
    license_data: FontLicenseUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update license metadata (admin only)."""
    validate_font_access(font_id, db)
    
    license_record = db.query(FontLicenseModel).filter(
        FontLicenseModel.id == license_id,
        FontLicenseModel.font_id == font_id,
    ).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    
    if license_data.license_type is not None:
        license_record.license_type = license_data.license_type
    if license_data.license_key is not None:
        license_record.license_key = license_data.license_key
    if license_data.seat_count is not None:
        license_record.seat_count = license_data.seat_count
    if license_data.expiry_date is not None:
        license_record.expiry_date = license_data.expiry_date
    if license_data.notes is not None:
        license_record.notes = license_data.notes
    
    license_record.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(license_record)
    
    return license_record


@router.delete("/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license(
    font_id: int,
    license_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a license (admin only)."""
    validate_font_access(font_id, db)
    
    license_record = db.query(FontLicenseModel).filter(
        FontLicenseModel.id == license_id,
        FontLicenseModel.font_id == font_id,
    ).first()
    
    if not license_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    
    # Delete file from disk
    file_path = Path(license_record.storage_path)
    if file_path.exists():
        file_path.unlink()
    
    db.delete(license_record)
    db.commit()
