"""Collections router."""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    Collection,
    CollectionCreate,
    CollectionUpdate,
    CollectionList,
    CollectionWithFonts,
)
from app.routers.auth import get_current_user, get_current_admin
from app.models import User

router = APIRouter(prefix="/api/collections", tags=["collections"])
logger = logging.getLogger(__name__)


async def check_collection_permission(
    current_user: User = Depends(get_current_user),
) -> User:
    """Check if user can manage collections (admin or has collection permission)."""
    if not current_user.is_admin and not current_user.can_create_collections:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collection management access required",
        )
    return current_user


@router.get("", response_model=CollectionList)
async def list_collections(
    client_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List collections with optional client filter."""
    from app.models import Collection as CollectionModel
    
    query = db.query(CollectionModel)
    
    if client_id:
        query = query.filter(CollectionModel.client_id == client_id)
    
    query = query.filter(CollectionModel.is_active == True)
    
    total = query.count()
    collections = query.offset(skip).limit(limit).all()
    
    return CollectionList(items=collections, total=total)


@router.get("/{collection_id}", response_model=CollectionWithFonts)
async def get_collection(
    collection_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get collection details with fonts."""
    from sqlalchemy.orm import joinedload
    from app.models import Collection as CollectionModel, Font
    
    collection = db.query(CollectionModel).options(
        joinedload(CollectionModel.fonts).joinedload(Font.family)
    ).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    
    return collection


@router.get("/{collection_id}/fonts")
async def get_collection_fonts(
    collection_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get fonts in a collection."""
    from app.models import Collection as CollectionModel
    
    collection = db.query(CollectionModel).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    
    # Return fonts with family_name included
    fonts = []
    for font in collection.fonts:
        fonts.append({
            "id": font.id,
            "postscript_name": font.postscript_name,
            "style_name": font.style_name,
            "full_name": font.full_name,
            "family_id": font.family_id,
            "family_name": font.family.name if font.family else None,
            "extension": font.extension,
        })
    
    return fonts


@router.post("", response_model=Collection)
async def create_collection(
    data: CollectionCreate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new collection (admin only)."""
    from app.models import Collection as CollectionModel, Client
    
    collection = CollectionModel(
        name=data.name,
        slug=data.slug or data.name.lower().replace(" ", "-"),
        description=data.description,
        client_id=data.client_id,
        is_active=data.is_active,
    )
    
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    # If collection is assigned to a client, automatically add all client's fonts
    if data.client_id:
        client = db.query(Client).filter(Client.id == data.client_id).first()
        if client and client.fonts:
            collection.fonts.extend(client.fonts)
            db.commit()
            logger.info(f"[AUDIT] Added {len(client.fonts)} fonts from client {client.name} to collection {collection.name}")
    
    logger.info(f"[AUDIT] Collection created: ID={collection.id}, name='{collection.name}', user='{current_user.username}'")
    return collection


@router.put("/{collection_id}", response_model=Collection)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a collection (admin only)."""
    from app.models import Collection as CollectionModel, Client
    
    collection = db.query(CollectionModel).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    
    old_client_id = collection.client_id
    
    if data.name is not None:
        collection.name = data.name
    if data.slug is not None:
        collection.slug = data.slug
    if data.description is not None:
        collection.description = data.description
    if data.client_id is not None:
        collection.client_id = data.client_id
    if data.is_active is not None:
        collection.is_active = data.is_active
    
    db.commit()
    db.refresh(collection)
    
    # If client_id changed and new client has fonts, add them to collection
    if data.client_id is not None and data.client_id != old_client_id:
        if data.client_id:  # New client assigned
            client = db.query(Client).filter(Client.id == data.client_id).first()
            if client and client.fonts:
                # Get current font IDs in collection
                current_font_ids = {f.id for f in collection.fonts}
                # Add only fonts not already in collection
                new_fonts = [f for f in client.fonts if f.id not in current_font_ids]
                if new_fonts:
                    collection.fonts.extend(new_fonts)
                    db.commit()
                    logger.info(f"[AUDIT] Added {len(new_fonts)} fonts from client {client.name} to collection {collection.name}")
        # If client_id set to None, we don't remove fonts (they stay in collection)
    
    return collection


@router.post("/{collection_id}/fonts")
async def add_font_to_collection(
    collection_id: int,
    font_id: int = Query(...),
    current_user: User = Depends(check_collection_permission),
    db: Session = Depends(get_db),
):
    """Add a font to a collection (admin or users with collection permission)."""
    from app.models import Collection as CollectionModel, Font as FontModel, collection_fonts
    
    collection = db.query(CollectionModel).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    # Check if already exists
    existing = db.query(collection_fonts).filter(
        collection_fonts.c.collection_id == collection_id,
        collection_fonts.c.font_id == font_id,
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Font already in collection",
        )
    
    # Add to collection
    stmt = collection_fonts.insert().values(
        collection_id=collection_id,
        font_id=font_id,
    )
    db.execute(stmt)
    db.commit()
    logger.info(f"[AUDIT] Font added to collection: collection_id={collection_id}, font_id={font_id}, user='{current_user.username}'")
    return {"success": True, "message": "Font added to collection"}


@router.delete("/{collection_id}/fonts/{font_id}")
async def remove_font_from_collection(
    collection_id: int,
    font_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Remove a font from a collection (admin only)."""
    from app.models import collection_fonts
    
    stmt = collection_fonts.delete().where(
        collection_fonts.c.collection_id == collection_id,
        collection_fonts.c.font_id == font_id,
    )
    result = db.execute(stmt)
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found in collection",
        )
    
    logger.info(f"[AUDIT] Font removed from collection: collection_id={collection_id}, font_id={font_id}, user='{current_user.username}'")
    return {"success": True, "message": "Font removed from collection"}


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a collection (admin only)."""
    from app.models import Collection as CollectionModel, collection_fonts
    
    collection = db.query(CollectionModel).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )
    
    # Store name before deletion
    collection_name = collection.name
    
    # Remove all font associations first
    stmt = collection_fonts.delete().where(collection_fonts.c.collection_id == collection_id)
    db.execute(stmt)
    
    # Delete the collection
    db.delete(collection)
    db.commit()
    logger.info(f"[AUDIT] Collection deleted: ID={collection_id}, name='{collection_name}', user='{current_user.username}'")
    return {"success": True, "message": "Collection deleted"}
