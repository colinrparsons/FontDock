"""Groups API router — user groups for font access control."""
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Group as GroupModel, Font as FontModel, User as UserModel, Client as ClientModel, FontFamily as FontFamilyModel
from app.schemas import (
    Group, GroupCreate, GroupUpdate, GroupDetail,
    GroupList, GroupFontAssign, GroupUserAssign,
)
from app.routers.auth import get_current_user, get_current_admin


router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=GroupList)
async def list_groups(
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all groups (admin sees all, regular users see their own groups)."""
    query = db.query(GroupModel)
    
    if not current_user.is_admin:
        # Regular users only see groups they belong to
        query = query.join(GroupModel.users).filter(UserModel.id == current_user.id)
    
    if is_active is not None:
        query = query.filter(GroupModel.is_active == is_active)
    
    total = query.count()
    groups = query.order_by(GroupModel.name).all()
    
    # Build response with font/user counts
    group_items = []
    for g in groups:
        group_items.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "is_active": g.is_active,
            "created_at": g.created_at,
            "updated_at": g.updated_at,
            "font_count": len(g.fonts),
            "user_count": len(g.users),
        })
    
    return GroupList(items=group_items, total=total)


@router.post("", response_model=Group, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new group (admin only)."""
    existing = db.query(GroupModel).filter(GroupModel.name == group_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Group '{group_data.name}' already exists",
        )
    
    group = GroupModel(
        name=group_data.name,
        description=group_data.description,
        is_active=group_data.is_active,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=GroupDetail)
async def get_group(
    group_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get group details with fonts and users."""
    from sqlalchemy.orm import joinedload
    from app.models import Font as FontModel
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    # Non-admin users can only see groups they belong to
    if not current_user.is_admin:
        user_ids = [u.id for u in group.users]
        if current_user.id not in user_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this group",
            )
    
    # Build font list with family_name populated
    font_list = []
    for f in group.fonts:
        font_dict = {
            "id": f.id,
            "postscript_name": f.postscript_name,
            "style_name": f.style_name,
            "full_name": f.full_name,
            "filename_original": f.filename_original,
            "filename_storage": f.filename_storage,
            "storage_path": f.storage_path,
            "file_hash_sha256": f.file_hash_sha256,
            "file_size_bytes": f.file_size_bytes,
            "family_id": f.family_id,
            "family_name": f.family.name if f.family else None,
            "client_ids": [c.id for c in f.clients],
            "group_ids": [g.id for g in f.groups],
            "extension": f.extension,
            "created_at": f.created_at,
            "updated_at": f.updated_at,
        }
        font_list.append(font_dict)
    
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        fonts=font_list,
        font_ids=[f.id for f in group.fonts],
        users=group.users,
        user_ids=[u.id for u in group.users],
    )


@router.put("/{group_id}", response_model=Group)
async def update_group(
    group_id: int,
    group_data: GroupUpdate,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    if group_data.name is not None:
        # Check for name conflict
        existing = db.query(GroupModel).filter(
            GroupModel.name == group_data.name,
            GroupModel.id != group_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Group '{group_data.name}' already exists",
            )
        group.name = group_data.name
    
    if group_data.description is not None:
        group.description = group_data.description
    if group_data.is_active is not None:
        group.is_active = group_data.is_active
    
    group.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    db.delete(group)
    db.commit()


@router.post("/{group_id}/fonts", response_model=GroupDetail)
async def assign_fonts_to_group(
    group_id: int,
    assign_data: GroupFontAssign,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign fonts to a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    # Validate font IDs exist
    fonts = db.query(FontModel).filter(FontModel.id.in_(assign_data.font_ids)).all()
    found_ids = {f.id for f in fonts}
    missing_ids = set(assign_data.font_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Font IDs not found: {missing_ids}",
        )
    
    # Add fonts that aren't already assigned
    existing_font_ids = {f.id for f in group.fonts}
    for font in fonts:
        if font.id not in existing_font_ids:
            group.fonts.append(font)
    
    db.commit()
    db.refresh(group)
    
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        fonts=group.fonts,
        font_ids=[f.id for f in group.fonts],
        users=group.users,
        user_ids=[u.id for u in group.users],
    )


@router.post("/{group_id}/fonts/by-client", response_model=GroupDetail)
async def assign_fonts_by_client(
    group_id: int,
    client_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign all fonts belonging to a client to a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    client = db.query(ClientModel).filter(ClientModel.id == client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    
    existing_font_ids = {f.id for f in group.fonts}
    added = 0
    for font in client.fonts:
        if font.id not in existing_font_ids:
            group.fonts.append(font)
            added += 1
    
    db.commit()
    db.refresh(group)
    
    return GroupDetail(
        id=group.id, name=group.name, description=group.description,
        is_active=group.is_active, created_at=group.created_at, updated_at=group.updated_at,
        fonts=group.fonts, font_ids=[f.id for f in group.fonts],
        users=group.users, user_ids=[u.id for u in group.users],
    )


@router.post("/{group_id}/fonts/by-family", response_model=GroupDetail)
async def assign_fonts_by_family(
    group_id: int,
    family_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign all fonts in a family to a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    family = db.query(FontFamilyModel).filter(FontFamilyModel.id == family_id).first()
    if not family:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Font family not found")
    
    family_fonts = db.query(FontModel).filter(FontModel.family_id == family_id).all()
    existing_font_ids = {f.id for f in group.fonts}
    added = 0
    for font in family_fonts:
        if font.id not in existing_font_ids:
            group.fonts.append(font)
            added += 1
    
    db.commit()
    db.refresh(group)
    
    return GroupDetail(
        id=group.id, name=group.name, description=group.description,
        is_active=group.is_active, created_at=group.created_at, updated_at=group.updated_at,
        fonts=group.fonts, font_ids=[f.id for f in group.fonts],
        users=group.users, user_ids=[u.id for u in group.users],
    )


@router.delete("/{group_id}/fonts/{font_id}", response_model=GroupDetail)
async def remove_font_from_group(
    group_id: int,
    font_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Remove a font from a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    font = db.query(FontModel).filter(FontModel.id == font_id).first()
    if not font:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Font not found",
        )
    
    if font in group.fonts:
        group.fonts.remove(font)
        db.commit()
    
    db.refresh(group)
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        fonts=group.fonts,
        font_ids=[f.id for f in group.fonts],
        users=group.users,
        user_ids=[u.id for u in group.users],
    )


@router.post("/{group_id}/users", response_model=GroupDetail)
async def assign_users_to_group(
    group_id: int,
    assign_data: GroupUserAssign,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign users to a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    # Validate user IDs exist
    users = db.query(UserModel).filter(UserModel.id.in_(assign_data.user_ids)).all()
    found_ids = {u.id for u in users}
    missing_ids = set(assign_data.user_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User IDs not found: {missing_ids}",
        )
    
    # Add users that aren't already assigned
    existing_user_ids = {u.id for u in group.users}
    for user in users:
        if user.id not in existing_user_ids:
            group.users.append(user)
    
    db.commit()
    db.refresh(group)
    
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        fonts=group.fonts,
        font_ids=[f.id for f in group.fonts],
        users=group.users,
        user_ids=[u.id for u in group.users],
    )


@router.delete("/{group_id}/users/{user_id}", response_model=GroupDetail)
async def remove_user_from_group(
    group_id: int,
    user_id: int,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Remove a user from a group (admin only)."""
    group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if user in group.users:
        group.users.remove(user)
        db.commit()
    
    db.refresh(group)
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        fonts=group.fonts,
        font_ids=[f.id for f in group.fonts],
        users=group.users,
        user_ids=[u.id for u in group.users],
    )
