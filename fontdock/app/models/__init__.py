"""SQLAlchemy models for FontDock."""
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text, Float, Date
from sqlalchemy.orm import relationship

from app.db import Base


# Association tables
collection_fonts = Table(
    "collection_fonts",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("collection_id", Integer, ForeignKey("collections.id"), nullable=False),
    Column("font_id", Integer, ForeignKey("fonts.id"), nullable=False),
    Column("added_at", DateTime, default=datetime.datetime.utcnow),
)

collection_tags = Table(
    "collection_tags",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("collection_id", Integer, ForeignKey("collections.id"), nullable=False),
    Column("tag_id", Integer, ForeignKey("tags.id"), nullable=False),
)

client_fonts = Table(
    "client_fonts",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("client_id", Integer, ForeignKey("clients.id"), nullable=False),
    Column("font_id", Integer, ForeignKey("fonts.id"), nullable=False),
    Column("added_at", DateTime, default=datetime.datetime.utcnow),
)

group_fonts = Table(
    "group_fonts",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("group_id", Integer, ForeignKey("groups.id"), nullable=False),
    Column("font_id", Integer, ForeignKey("fonts.id"), nullable=False),
    Column("added_at", DateTime, default=datetime.datetime.utcnow),
)

user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("group_id", Integer, ForeignKey("groups.id"), nullable=False),
    Column("added_at", DateTime, default=datetime.datetime.utcnow),
)


class User(Base):
    """User account."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    # Granular permissions
    can_create_users = Column(Boolean, default=False)
    can_delete_users = Column(Boolean, default=False)
    can_upload_fonts = Column(Boolean, default=False)
    can_download_fonts = Column(Boolean, default=True)
    can_delete_fonts = Column(Boolean, default=False)
    can_create_collections = Column(Boolean, default=False)
    can_create_clients = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    client_permissions = relationship("UserClientPermission", back_populates="user")
    usage_events = relationship("FontUsageEvent", back_populates="user")
    audit_events = relationship("AuditEvent", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    groups = relationship("Group", secondary=user_groups, back_populates="users")


class Client(Base):
    """Client/brand entity."""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    collections = relationship("Collection", back_populates="client")
    fonts = relationship("Font", secondary=client_fonts, back_populates="clients")
    user_permissions = relationship("UserClientPermission", back_populates="client")


class Collection(Base):
    """Font collection (project, brand set, etc.)."""
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, index=True)
    description = Column(Text)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)  # NULL for global collections
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="collections")
    fonts = relationship("Font", secondary=collection_fonts, back_populates="collections")
    tags = relationship("Tag", secondary=collection_tags, back_populates="collections")
    usage_events = relationship("FontUsageEvent", back_populates="collection")


class Tag(Base):
    """Tag for categorizing collections."""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, index=True)
    
    # Relationships
    collections = relationship("Collection", secondary=collection_tags, back_populates="tags")


class FontFamily(Base):
    """Font family grouping."""
    __tablename__ = "font_families"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, index=True)
    foundry = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    fonts = relationship("Font", back_populates="family")


class Font(Base):
    """Individual font file/style."""
    __tablename__ = "fonts"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("font_families.id"), nullable=False)
    filename_original = Column(String, nullable=False)
    filename_storage = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    file_hash_sha256 = Column(String, index=True)
    file_size_bytes = Column(Integer)
    extension = Column(String(10))
    postscript_name = Column(String, index=True)
    full_name = Column(String, index=True)
    style_name = Column(String, index=True)
    weight_class = Column(Integer)
    width_class = Column(Integer)
    italic_angle = Column(Float)
    version_string = Column(String)
    is_variable_font = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    family = relationship("FontFamily", back_populates="fonts")
    clients = relationship("Client", secondary=client_fonts, back_populates="fonts")
    collections = relationship("Collection", secondary=collection_fonts, back_populates="fonts")
    groups = relationship("Group", secondary=group_fonts, back_populates="fonts")
    aliases = relationship("FontAlias", back_populates="font")
    usage_events = relationship("FontUsageEvent", back_populates="font")
    licenses = relationship("FontLicense", back_populates="font")


class FontAlias(Base):
    """Alternative names for fonts (legacy, variations, etc.)."""
    __tablename__ = "font_aliases"
    
    id = Column(Integer, primary_key=True, index=True)
    font_id = Column(Integer, ForeignKey("fonts.id"), nullable=False)
    alias_name = Column(String, nullable=False, index=True)
    alias_normalized = Column(String, index=True)
    source_type = Column(String)  # e.g., 'legacy', 'abbreviation', 'common_name'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    font = relationship("Font", back_populates="aliases")


class UserClientPermission(Base):
    """User permissions per client."""
    __tablename__ = "user_client_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    can_view = Column(Boolean, default=True)
    can_download = Column(Boolean, default=False)
    can_activate = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="client_permissions")
    client = relationship("Client", back_populates="user_permissions")


class FontUsageEvent(Base):
    """Tracks font usage history."""
    __tablename__ = "font_usage_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    font_id = Column(Integer, ForeignKey("fonts.id"), nullable=False)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    source = Column(String)  # e.g., 'web', 'client', 'indesign'
    document_name = Column(String)
    document_path_hint = Column(String)
    event_type = Column(String, nullable=False)  # 'download', 'activate', 'deactivate', 'indesign_missing_font_match'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="usage_events")
    font = relationship("Font", back_populates="usage_events")
    collection = relationship("Collection", back_populates="usage_events")


class AuditEvent(Base):
    """Broad audit trail."""
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String, nullable=False)
    entity_type = Column(String)  # 'font', 'collection', 'client', 'user'
    entity_id = Column(Integer)
    payload_json = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="audit_events")


class Group(Base):
    """User group for font access control."""
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    users = relationship("User", secondary=user_groups, back_populates="groups")
    fonts = relationship("Font", secondary=group_fonts, back_populates="groups")


class FontLicense(Base):
    """License file/metadata attached to a font."""
    __tablename__ = "font_licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    font_id = Column(Integer, ForeignKey("fonts.id"), nullable=False, index=True)
    license_type = Column(String)  # e.g., 'desktop', 'web', 'app', 'universal'
    license_key = Column(Text)  # Optional license key text
    seat_count = Column(Integer)  # Number of licensed seats
    expiry_date = Column(Date)  # License expiry date
    notes = Column(Text)
    filename_original = Column(String)  # Original uploaded filename
    filename_storage = Column(String, nullable=False)  # Storage filename
    storage_path = Column(String, nullable=False)  # Full storage path
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    font = relationship("Font", back_populates="licenses")


class UserSession(Base):
    """Active user session for tracking logins."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_jti = Column(String, unique=True, index=True)  # JWT ID for revocation
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
