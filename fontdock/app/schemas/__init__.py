"""Pydantic schemas for FontDock."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ============= Auth Schemas =============

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


# ============= User Schemas =============

class UserBase(BaseModel):
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    can_create_users: bool = False
    can_delete_users: bool = False
    can_upload_fonts: bool = False
    can_download_fonts: bool = True
    can_delete_fonts: bool = False
    can_create_collections: bool = False
    can_create_clients: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    can_create_users: Optional[bool] = None
    can_delete_users: Optional[bool] = None
    can_upload_fonts: Optional[bool] = None
    can_download_fonts: Optional[bool] = None
    can_delete_fonts: Optional[bool] = None
    can_create_collections: Optional[bool] = None
    can_create_clients: Optional[bool] = None


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class UserList(BaseModel):
    items: List[User]
    total: int


# ============= Client Schemas =============

class ClientBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Client(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class ClientList(BaseModel):
    items: List[Client]
    total: int


# ============= Collection Schemas =============

class CollectionBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    is_active: bool = True


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    is_active: Optional[bool] = None


class Collection(CollectionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class CollectionWithFonts(Collection):
    fonts: List["Font"] = []


class CollectionList(BaseModel):
    items: List[Collection]
    total: int


# ============= Tag Schemas =============

class TagBase(BaseModel):
    name: str
    slug: Optional[str] = None


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


# ============= Font Family Schemas =============

class FontFamilyBase(BaseModel):
    name: str
    normalized_name: Optional[str] = None
    foundry: Optional[str] = None
    notes: Optional[str] = None


class FontFamilyCreate(FontFamilyBase):
    pass


class FontFamily(FontFamilyBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class FontFamilyWithFonts(FontFamily):
    fonts: List["Font"] = []


class FontFamilyList(BaseModel):
    items: List[FontFamily]
    total: int


# ============= Font Schemas =============

class FontBase(BaseModel):
    family_id: int
    filename_original: str
    extension: str
    postscript_name: Optional[str] = None
    full_name: Optional[str] = None
    style_name: Optional[str] = None
    weight_class: Optional[int] = None
    width_class: Optional[int] = None
    italic_angle: Optional[float] = None
    version_string: Optional[str] = None
    is_variable_font: bool = False
    is_active: bool = True


class FontCreate(FontBase):
    filename_storage: str
    storage_path: str
    file_hash_sha256: str
    file_size_bytes: int


class Font(FontBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    filename_storage: str
    storage_path: str
    file_hash_sha256: Optional[str] = None
    file_size_bytes: Optional[int] = None
    family_name: Optional[str] = None  # Added for API response
    client_ids: List[int] = []  # Added for many-to-many client relationship
    created_at: datetime
    updated_at: datetime


class FontWithFamily(Font):
    family: Optional[FontFamily] = None


class FontWithCollections(Font):
    collections: List[Collection] = []


# ============= Font Alias Schemas =============
# Define FontAlias BEFORE FontDetail to avoid forward reference issues

class FontAliasBase(BaseModel):
    font_id: int
    alias_name: str
    alias_normalized: Optional[str] = None
    source_type: Optional[str] = None


class FontAliasCreate(FontAliasBase):
    pass


class FontAlias(FontAliasBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


# Now FontDetail can reference FontAlias
class FontDetail(Font):
    family: Optional[FontFamily] = None
    collections: List[Collection] = []
    aliases: List[FontAlias] = []


class FontList(BaseModel):
    items: List[FontWithFamily]
    total: int


class FontUploadResponse(BaseModel):
    success: bool
    font_id: Optional[int] = None
    message: str


# ============= Search Schemas =============

class FontSearchQuery(BaseModel):
    q: Optional[str] = None
    family_id: Optional[int] = None
    client_id: Optional[int] = None
    collection_id: Optional[int] = None
    tag_id: Optional[int] = None
    is_active: Optional[bool] = True
    skip: int = 0
    limit: int = 50


class FontSearchResult(BaseModel):
    fonts: List[FontWithFamily]
    total: int
    skip: int
    limit: int


# ============= Audit Schemas =============

class AuditEventBase(BaseModel):
    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    payload_json: Optional[str] = None


class AuditEventCreate(AuditEventBase):
    user_id: Optional[int] = None


class AuditEvent(AuditEventBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: Optional[int] = None
    created_at: datetime


# ============= Usage Event Schemas =============

class FontUsageEventBase(BaseModel):
    font_id: int
    collection_id: Optional[int] = None
    source: Optional[str] = None
    document_name: Optional[str] = None
    document_path_hint: Optional[str] = None
    event_type: str


class FontUsageEventCreate(FontUsageEventBase):
    user_id: int


class FontUsageEvent(FontUsageEventBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime
