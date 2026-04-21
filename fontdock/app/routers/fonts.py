"""Fonts router."""
import logging
import tempfile
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status, Request
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.db import get_db
from app.schemas import (
    Font,
    FontDetail,
    FontList,
    FontSearchResult,
    FontUploadResponse,
    FontWithFamily,
)
from app.models import User, Font as FontModel, Collection
from app.routers.auth import get_current_user, get_current_admin
from app.services.font_ingest_service import ingest_font
from app.services.font_search_service import search_fonts
from app.services.auth_service import decode_token, get_user_by_username
from app.config import get_settings

router = APIRouter(prefix="/api/fonts", tags=["fonts"])
settings = get_settings()
logger = logging.getLogger(__name__)


class OptionalOAuth2PasswordBearer(OAuth2PasswordBearer):
    """OAuth2 scheme that allows optional authentication for @font-face CSS requests."""
    
    async def __call__(self, request: Request) -> Optional[str]:
        # Check if token is in query param (for CSS font-face)
        token = request.query_params.get("token")
        if token:
            return token
        # Otherwise use header-based auth
        return await super().__call__(request)


optional_oauth2 = OptionalOAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user_optional_token(
    token: Annotated[str, Depends(optional_oauth2)],
    db: Session = Depends(get_db),
) -> User:
    """Get current user from header or query param (for CSS font-face)."""
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = decode_token(token)
    if token_data is None or token_data.username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_username(db, token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


@router.get("", response_model=FontList)
async def list_fonts(
    q: Optional[str] = Query(None, description="Search query"),
    family_id: Optional[int] = Query(None),
    collection_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(None, ge=1),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List fonts with optional filtering and search."""
    # Build query with family join
    query = db.query(FontModel).options(joinedload(FontModel.family))
    
    if family_id:
        query = query.filter(FontModel.family_id == family_id)
    
    if collection_id:
        query = query.join(FontModel.collections).filter(Collection.id == collection_id)
    
    if client_id:
        query = query.filter(FontModel.client_id == client_id)
    
    if q:
        query = query.filter(
            or_(
                FontModel.postscript_name.ilike(f"%{q}%"),
                FontModel.style_name.ilike(f"%{q}%"),
                FontModel.full_name.ilike(f"%{q}%"),
            )
        )
    
    total = query.count()
    q = query.offset(skip)
    if limit is not None:
        q = q.limit(limit)
    fonts = q.all()
    
    # Build response with family_name and client_ids populated
    font_responses = []
    for font in fonts:
        font_dict = {
            "id": font.id,
            "postscript_name": font.postscript_name,
            "style_name": font.style_name,
            "full_name": font.full_name,
            "filename_original": font.filename_original,
            "filename_storage": font.filename_storage,
            "storage_path": font.storage_path,
            "file_hash_sha256": font.file_hash_sha256,
            "file_size_bytes": font.file_size_bytes,
            "family_id": font.family_id,
            "family_name": font.family.name if font.family else None,
            "client_ids": [client.id for client in font.clients],
            "extension": font.extension,
            "created_at": font.created_at,
            "updated_at": font.updated_at,
        }
        font_responses.append(font_dict)
    
    return FontList(items=font_responses, total=total)


@router.get("/{font_id}", response_model=FontDetail)
async def get_font(
    font_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get font details by ID."""
    from app.models import Font as FontModel
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    return font


async def check_upload_permission(
    current_user: User = Depends(get_current_user),
) -> User:
    """Check if user can upload fonts (admin or has upload permission)."""
    if not current_user.is_admin and not current_user.can_upload_fonts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload access required",
        )
    return current_user


@router.post("/upload", response_model=FontUploadResponse)
async def upload_font(
    file: Annotated[UploadFile, File(description="Font file to upload (OTF, TTF, TTC)")],
    collection_ids: Optional[str] = Form(None, description="Comma-separated collection IDs"),
    client_id: Optional[int] = Form(None, description="Client ID to assign font to"),
    current_user: User = Depends(check_upload_permission),
    db: Session = Depends(get_db),
):
    """Upload a new font file (admin or users with upload permission)."""
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )
    
    extension = Path(file.filename).suffix.lower()
    if extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.allowed_extensions)}",
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        content = await file.read()
        
        # Check file size
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: {settings.max_upload_size_bytes / 1024 / 1024}MB",
            )
        
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        # Parse collection IDs
        col_ids = None
        if collection_ids:
            col_ids = [int(x.strip()) for x in collection_ids.split(",") if x.strip()]
        
        # Ingest font
        font = ingest_font(
            db,
            file_path=tmp_path,
            original_filename=file.filename,
            collection_ids=col_ids,
        )
        
        if font:
            # Assign to client if specified
            if client_id:
                from app.models import Client
                client = db.query(Client).filter(Client.id == client_id).first()
                if client and font not in client.fonts:
                    client.fonts.append(font)
                    db.commit()
                    logger.info(f"[AUDIT] Font {font.id} assigned to client {client_id}")
            
            logger.info(f"[AUDIT] Font uploaded: ID={font.id}, name='{font.postscript_name}', user='{current_user.username}'")
            return FontUploadResponse(
                success=True,
                font_id=font.id,
                message=f"Font uploaded successfully: {font.postscript_name or file.filename}",
            )
        else:
            return FontUploadResponse(
                success=False,
                message="Failed to ingest font",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing font: {str(e)}",
        )
    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


@router.get("/{font_id}/download")
async def download_font(
    font_id: int,
    current_user: User = Depends(get_current_user_optional_token),
    db: Session = Depends(get_db),
):
    """Download a font file."""
    from app.models import Font as FontModel
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    if not font.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Font is not active",
        )
    
    file_path = Path(font.storage_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font file not found on disk",
        )
    
    # Log download event
    from app.models import FontUsageEvent
    event = FontUsageEvent(
        user_id=current_user.id,
        font_id=font.id,
        event_type="download",
        source="api",
    )
    db.add(event)
    db.commit()
    
    return FileResponse(
        path=file_path,
        filename=font.filename_original,
        media_type="application/octet-stream",
    )


@router.get("/{font_id}/preview")
async def font_preview(
    font_id: int,
    db: Session = Depends(get_db),
):
    """Get a visual preview of the font."""
    from app.models import Font as FontModel
    from app.services.font_preview_service import generate_font_preview, get_font_sample_text
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    file_path = Path(font.storage_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font file not found on disk",
        )
    
    # Generate preview
    sample_text = get_font_sample_text(file_path)
    preview_data = generate_font_preview(file_path, sample_text)
    
    if not preview_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview",
        )
    
    return {"preview": preview_data, "sample_text": sample_text}


@router.delete("/all")
async def delete_all_fonts(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete all fonts (admin only)."""
    from app.models import Font as FontModel, FontFamily, collection_fonts
    
    # Get all fonts
    fonts = db.query(FontModel).all()
    deleted_count = 0
    
    for font in fonts:
        # Delete font file from disk
        file_path = Path(font.storage_path)
        if file_path.exists():
            file_path.unlink()
        deleted_count += 1
    
    # Remove all font-collection associations
    stmt = collection_fonts.delete()
    db.execute(stmt)
    
    # Delete all fonts from DB
    db.query(FontModel).delete()
    db.commit()
    
    # Delete all families (since no fonts remain)
    db.query(FontFamily).delete()
    db.commit()
    
    return {"success": True, "message": f"Deleted {deleted_count} fonts and all families"}


@router.post("/{font_id}/client")
async def assign_font_to_client(
    font_id: int,
    data: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign a font to a client."""
    from app.models import Client
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    client_id = data.get("client_id")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required",
        )
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    font.client_id = client_id
    db.commit()
    
    logger.info(f"[AUDIT] Font assigned to client: font_id={font_id}, client_id={client_id}, user='{current_user.username}'")
    return {"success": True, "message": f"Font assigned to {client.name}"}


@router.delete("/{font_id}/client")
async def remove_font_from_client(
    font_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Remove a font from its client (set client_id to NULL)."""
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    old_client_id = font.client_id
    font.client_id = None
    db.commit()
    
    logger.info(f"[AUDIT] Font removed from client: font_id={font_id}, old_client_id={old_client_id}, user='{current_user.username}'")
    return {"success": True, "message": "Font removed from client"}


@router.post("/cleanup-duplicates")
async def cleanup_duplicate_fonts(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Find and remove duplicate fonts by PostScript name+extension AND file hash."""
    from app.models import Font as FontModel, client_fonts
    from sqlalchemy import func
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[CLEANUP] Starting duplicate cleanup by {current_user.username}")
        
        removed_count = 0
        kept_fonts = []
        removed_fonts = []
        
        # Method 1: Find duplicates by PostScript name + extension
        ps_duplicates = db.query(
            FontModel.postscript_name,
            FontModel.extension,
            func.count(FontModel.id).label('count')
        ).group_by(
            FontModel.postscript_name,
            FontModel.extension
        ).having(func.count(FontModel.id) > 1).all()
        
        logger.info(f"[CLEANUP] Found {len(ps_duplicates)} PostScript name duplicate groups")
        
        for ps_name, ext, count in ps_duplicates:
            logger.info(f"[CLEANUP] Processing PS duplicate: {ps_name} ({ext}) - {count} copies")
            
            fonts = db.query(FontModel).filter(
                FontModel.postscript_name == ps_name,
                FontModel.extension == ext
            ).order_by(FontModel.created_at).all()
            
            kept = fonts[0]
            kept_fonts.append(f"{ps_name} ({ext}) - ID {kept.id} - {kept.filename_original}")
            logger.info(f"[CLEANUP] Keeping font ID {kept.id} ({kept.filename_original})")
            
            for font in fonts[1:]:
                logger.info(f"[CLEANUP] Removing font ID {font.id} ({font.filename_original})")
                removed_fonts.append(f"{ps_name} ({ext}) - ID {font.id} - {font.filename_original}")
                
                # Delete from client_fonts association table
                db.execute(client_fonts.delete().where(client_fonts.c.font_id == font.id))
                
                # Delete font usage events
                from app.models import FontUsageEvent
                db.query(FontUsageEvent).filter(FontUsageEvent.font_id == font.id).delete()
                
                # Delete the font file
                if os.path.exists(font.storage_path):
                    os.remove(font.storage_path)
                    logger.info(f"[CLEANUP] Deleted file: {font.storage_path}")
                
                # Delete from database
                db.delete(font)
                removed_count += 1
        
        # Method 2: Find duplicates by file hash (same file, different filename)
        hash_duplicates = db.query(
            FontModel.file_hash_sha256,
            func.count(FontModel.id).label('count')
        ).filter(
            FontModel.file_hash_sha256.isnot(None)
        ).group_by(
            FontModel.file_hash_sha256
        ).having(func.count(FontModel.id) > 1).all()
        
        logger.info(f"[CLEANUP] Found {len(hash_duplicates)} file hash duplicate groups")
        
        for file_hash, count in hash_duplicates:
            logger.info(f"[CLEANUP] Processing hash duplicate: {file_hash[:16]}... - {count} copies")
            
            fonts = db.query(FontModel).filter(
                FontModel.file_hash_sha256 == file_hash
            ).order_by(FontModel.created_at).all()
            
            kept = fonts[0]
            kept_fonts.append(f"Hash {file_hash[:16]}... - ID {kept.id} - {kept.filename_original}")
            logger.info(f"[CLEANUP] Keeping font ID {kept.id} ({kept.filename_original})")
            
            for font in fonts[1:]:
                logger.info(f"[CLEANUP] Removing duplicate file ID {font.id} ({font.filename_original})")
                removed_fonts.append(f"Hash {file_hash[:16]}... - ID {font.id} - {font.filename_original}")
                
                # Delete from client_fonts association table
                db.execute(client_fonts.delete().where(client_fonts.c.font_id == font.id))
                
                # Delete font usage events
                from app.models import FontUsageEvent
                db.query(FontUsageEvent).filter(FontUsageEvent.font_id == font.id).delete()
                
                # Delete the font file
                if os.path.exists(font.storage_path):
                    os.remove(font.storage_path)
                    logger.info(f"[CLEANUP] Deleted file: {font.storage_path}")
                
                # Delete from database
                db.delete(font)
                removed_count += 1
        
        db.commit()
        
        logger.info(f"[AUDIT] Duplicate cleanup complete: removed {removed_count} fonts by {current_user.username}")
        
        return {
            "success": True,
            "removed_count": removed_count,
            "kept_fonts": kept_fonts,
            "removed_fonts": removed_fonts,
            "message": f"Removed {removed_count} duplicate fonts"
        }
    
    except Exception as e:
        logger.error(f"[CLEANUP] Error during cleanup: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.delete("/{font_id}")
async def delete_font(
    font_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a font (admin only)."""
    from app.models import Font as FontModel, collection_fonts, client_fonts, FontFamily, FontUsageEvent
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    # Store info before deleting
    family_id = font.family_id
    font_name = font.postscript_name or font.filename_original
    
    # Remove from collections
    stmt = collection_fonts.delete().where(collection_fonts.c.font_id == font_id)
    db.execute(stmt)
    
    # Remove from clients (many-to-many relationship)
    stmt = client_fonts.delete().where(client_fonts.c.font_id == font_id)
    db.execute(stmt)
    
    # Delete usage events
    db.query(FontUsageEvent).filter(FontUsageEvent.font_id == font_id).delete()
    
    # Delete font file from disk
    file_path = Path(font.storage_path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete font record
    db.delete(font)
    db.commit()
    logger.info(f"[AUDIT] Font deleted: ID={font_id}, name='{font_name}', user='{current_user.username}'")
    
    # Check if family has any remaining fonts, if not, delete the family
    remaining_fonts = db.query(FontModel).filter(FontModel.family_id == family_id).count()
    if remaining_fonts == 0:
        family = db.query(FontFamily).filter(FontFamily.id == family_id).first()
        if family:
            db.delete(family)
            db.commit()
    
    return {"success": True, "message": "Font deleted"}


@router.delete("/all")
async def delete_all_fonts(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete all fonts (admin only)."""
    from app.models import Font as FontModel, FontFamily, collection_fonts
    
    # Get all fonts
    fonts = db.query(FontModel).all()
    deleted_count = 0
    
    for font in fonts:
        # Delete font file from disk
        file_path = Path(font.storage_path)
        if file_path.exists():
            file_path.unlink()
        deleted_count += 1
    
    # Remove all font-collection associations
    stmt = collection_fonts.delete()
    db.execute(stmt)
    
    # Delete all fonts from DB
    db.query(FontModel).delete()
    db.commit()
    
    # Delete all families (since no fonts remain)
    db.query(FontFamily).delete()
    db.commit()
    
    return {"success": True, "message": f"Deleted {deleted_count} fonts and all families"}


@router.post("/{font_id}/client")
async def assign_font_to_client(
    font_id: int,
    data: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign a font to a client."""
    from app.models import Client
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    client_id = data.get("client_id")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id is required",
        )
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    font.client_id = client_id
    db.commit()
    
    logger.info(f"[AUDIT] Font assigned to client: font_id={font_id}, client_id={client_id}, user='{current_user.username}'")
    return {"success": True, "message": f"Font assigned to {client.name}"}


@router.delete("/{font_id}/client")
async def remove_font_from_client(
    font_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Remove a font from its client (set client_id to NULL)."""
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    old_client_id = font.client_id
    font.client_id = None
    db.commit()
    
    logger.info(f"[AUDIT] Font removed from client: font_id={font_id}, old_client_id={old_client_id}, user='{current_user.username}'")
    return {"success": True, "message": "Font removed from client"}
