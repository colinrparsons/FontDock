"""Clients router."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    Client,
    ClientCreate,
    ClientUpdate,
    ClientList,
)
from app.routers.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/clients", tags=["clients"])
logger = logging.getLogger(__name__)


@router.get("", response_model=ClientList)
async def list_clients(
    is_active: Optional[bool] = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List clients."""
    from app.models import Client as ClientModel
    
    query = db.query(ClientModel)
    
    if is_active is not None:
        query = query.filter(ClientModel.is_active == is_active)
    
    total = query.count()
    clients = query.offset(skip).limit(limit).all()
    
    return ClientList(items=clients, total=total)


@router.get("/{client_id}/fonts")
async def get_client_fonts(
    client_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all fonts assigned to a client."""
    from app.models import Client as ClientModel
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    # Return fonts using many-to-many relationship
    fonts = client.fonts
    
    # Convert to dict format
    return [
        {
            "id": font.id,
            "postscript_name": font.postscript_name,
            "style_name": font.style_name,
            "full_name": font.full_name,
            "filename_original": font.filename_original,
            "extension": font.extension,
            "family": {
                "id": font.family.id,
                "name": font.family.name
            } if font.family else None
        }
        for font in fonts
    ]


@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get client by ID."""
    from app.models import Client as ClientModel
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    return client


@router.post("", response_model=Client)
async def create_client(
    data: ClientCreate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new client (admin only)."""
    from app.models import Client as ClientModel
    
    # Check for duplicate code
    if data.code:
        existing = db.query(ClientModel).filter(ClientModel.code == data.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Client with code '{data.code}' already exists",
            )
    
    client = ClientModel(
        name=data.name,
        code=data.code,
        description=data.description,
        is_active=data.is_active,
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    logger.info(f"[AUDIT] Client created: ID={client.id}, name='{client.name}', user='{current_user.username}'")
    return client


@router.put("/{client_id}", response_model=Client)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a client (admin only)."""
    from app.models import Client as ClientModel
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    if data.name is not None:
        client.name = data.name
    if data.code is not None:
        # Check for duplicate code
        existing = db.query(ClientModel).filter(
            ClientModel.code == data.code,
            ClientModel.id != client_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Client with code '{data.code}' already exists",
            )
        client.code = data.code
    if data.description is not None:
        client.description = data.description
    if data.is_active is not None:
        client.is_active = data.is_active
    
    db.commit()
    db.refresh(client)
    
    return client


@router.post("/{client_id}/fonts")
async def assign_font_to_client(
    client_id: int,
    data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign a font to a client (many-to-many)."""
    from app.models import Client as ClientModel, Font
    
    font_id = data.get('font_id')
    if not font_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="font_id is required",
        )
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    font = db.query(Font).filter(Font.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    # Add font to client's fonts if not already assigned
    if font not in client.fonts:
        client.fonts.append(font)
        db.commit()
        logger.info(f"[AUDIT] Font {font_id} assigned to client {client_id} by {current_user.username}")
        return {"success": True, "message": f"Font assigned to {client.name}"}
    else:
        return {"success": True, "message": f"Font already assigned to {client.name}"}


@router.delete("/{client_id}/fonts/{font_id}")
async def unassign_font_from_client(
    client_id: int,
    font_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unassign a font from a client (many-to-many)."""
    from app.models import Client as ClientModel, Font
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    font = db.query(Font).filter(Font.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    # Remove font from client's fonts
    if font in client.fonts:
        client.fonts.remove(font)
        db.commit()
        logger.info(f"[AUDIT] Font {font_id} unassigned from client {client_id} by {current_user.username}")
        return {"success": True, "message": "Font unassigned from client"}
    else:
        return {"success": True, "message": "Font was not assigned to this client"}


@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Hard-delete a client and all related records (admin only)."""
    from app.models import Client as ClientModel, Font, Collection, UserClientPermission
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    
    client_name = client.name
    
    # Delete all collections for this client
    db.query(Collection).filter(Collection.client_id == client_id).delete()
    
    # Delete all user permissions for this client
    db.query(UserClientPermission).filter(UserClientPermission.client_id == client_id).delete()
    
    # Delete client_fonts associations (many-to-many)
    from app.models import client_fonts
    db.execute(client_fonts.delete().where(client_fonts.c.client_id == client_id))
    
    # Now delete the client
    db.delete(client)
    db.commit()
    
    logger.info(f"[AUDIT] Client deleted: ID={client_id}, name='{client_name}', admin='{current_user.username}'")
    
    return {"success": True, "message": "Client deleted permanently"}
