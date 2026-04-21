"""Font metadata extraction and ingest service."""
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from fontTools.ttLib import TTFont
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Font, FontFamily, FontAlias
from app.schemas import FontCreate, FontFamilyCreate


settings = get_settings()


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_font_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from a font file using fontTools."""
    metadata = {
        "postscript_name": None,
        "full_name": None,
        "family_name": None,
        "style_name": None,
        "weight_class": None,
        "width_class": None,
        "italic_angle": None,
        "version_string": None,
        "is_variable_font": False,
    }
    
    try:
        font = TTFont(file_path)
        
        # Get name table entries
        name_table = font.get("name", None)
        if name_table:
            # First pass: get all name records
            for record in name_table.names:
                name_id = record.nameID
                string = record.toStr()
                
                if name_id == 6:  # PostScript name
                    metadata["postscript_name"] = string
                elif name_id == 4:  # Full name
                    metadata["full_name"] = string
                elif name_id == 1:  # Family name (legacy)
                    metadata["family_name"] = string
                elif name_id == 2:  # Style name (Subfamily - legacy)
                    metadata["style_name"] = string
                elif name_id == 16:  # Typographic Family name (preferred)
                    metadata["typographic_family"] = string
                elif name_id == 17:  # Typographic Subfamily (preferred)
                    metadata["typographic_style"] = string
                elif name_id == 5:  # Version string
                    metadata["version_string"] = string
        
        # Use typographic names if available (they're cleaner)
        if metadata.get("typographic_family"):
            metadata["family_name"] = metadata["typographic_family"]
        if metadata.get("typographic_style"):
            metadata["style_name"] = metadata["typographic_style"]
        
        # Get OS/2 table for weight/width
        os2_table = font.get("OS/2", None)
        if os2_table:
            metadata["weight_class"] = getattr(os2_table, "usWeightClass", None)
            metadata["width_class"] = getattr(os2_table, "usWidthClass", None)
        
        # Get post table for italic angle
        post_table = font.get("post", None)
        if post_table:
            metadata["italic_angle"] = getattr(post_table, "italicAngle", None)
        
        # Check for variable font (fvar table)
        if "fvar" in font:
            metadata["is_variable_font"] = True
        
        font.close()
        
    except Exception as e:
        print(f"Error extracting font metadata: {e}")
    
    return metadata


def normalize_family_name(name: str) -> str:
    """Normalize family name to title case."""
    if not name:
        return "Unknown"
    # Title case the name, but preserve mixed-case names that aren't ALL CAPS
    if name.isupper():
        return name.title()
    return name


def get_or_create_family(db: Session, family_name: str, foundry: Optional[str] = None) -> FontFamily:
    """Get existing family or create new one."""
    # Normalize family name for lookup
    normalized = family_name.lower().replace(" ", "_") if family_name else None
    
    family = db.query(FontFamily).filter(
        FontFamily.normalized_name == normalized
    ).first()
    
    if not family:
        display_name = normalize_family_name(family_name)
        family = FontFamily(
            name=display_name,
            normalized_name=normalized,
            foundry=foundry,
        )
        db.add(family)
        db.commit()
        db.refresh(family)
    
    return family


def ingest_font(
    db: Session,
    file_path: Path,
    original_filename: str,
    collection_ids: Optional[list] = None,
) -> Optional[Font]:
    """Ingest a font file into the system.
    
    Args:
        db: Database session
        file_path: Path to the uploaded font file
        original_filename: Original filename from upload
        collection_ids: Optional list of collection IDs to assign
        
    Returns:
        Created Font object or None if failed
    """
    extension = Path(original_filename).suffix.lower()
    
    # Validate extension
    if extension not in settings.allowed_extensions:
        raise ValueError(f"Invalid file extension: {extension}")
    
    # Compute file hash
    file_hash = compute_file_hash(file_path)
    
    # Check for duplicate by hash
    existing = db.query(Font).filter(Font.file_hash_sha256 == file_hash).first()
    if existing:
        # Return existing font (deduplication)
        return existing
    
    # Extract metadata
    metadata = extract_font_metadata(file_path)
    
    # Check for duplicate by PostScript name + extension
    # This catches cases where the same font was uploaded with different file modifications
    if metadata.get("postscript_name"):
        existing_by_name = db.query(Font).filter(
            Font.postscript_name == metadata["postscript_name"],
            Font.extension == extension
        ).first()
        if existing_by_name:
            raise ValueError(
                f"Font '{metadata['postscript_name']}' ({extension}) already exists. "
                f"Use a different format (e.g., .ttf vs .otf) if you want both versions."
            )
    
    # Get or create family
    family_name = metadata.get("family_name") or Path(original_filename).stem
    family = get_or_create_family(db, family_name)
    
    # Generate storage filename
    storage_filename = f"{file_hash[:16]}{extension}"
    storage_path = settings.storage_path / storage_filename
    
    # Ensure storage directory exists
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    
    # Move/copy file to storage
    shutil.copy2(file_path, storage_path)
    
    # Create font record
    font = Font(
        family_id=family.id,
        filename_original=original_filename,
        filename_storage=storage_filename,
        storage_path=str(storage_path),
        file_hash_sha256=file_hash,
        file_size_bytes=file_path.stat().st_size,
        extension=extension,
        postscript_name=metadata.get("postscript_name"),
        full_name=metadata.get("full_name"),
        style_name=metadata.get("style_name"),
        weight_class=metadata.get("weight_class"),
        width_class=metadata.get("width_class"),
        italic_angle=metadata.get("italic_angle"),
        version_string=metadata.get("version_string"),
        is_variable_font=metadata.get("is_variable_font", False),
    )
    
    db.add(font)
    db.commit()
    db.refresh(font)
    
    # Add to collections if specified
    if collection_ids:
        from app.models import collection_fonts
        for collection_id in collection_ids:
            stmt = collection_fonts.insert().values(
                collection_id=collection_id,
                font_id=font.id
            )
            db.execute(stmt)
        db.commit()
    
    return font


def create_font_alias(
    db: Session,
    font_id: int,
    alias_name: str,
    source_type: Optional[str] = None,
) -> FontAlias:
    """Create a font alias."""
    alias_normalized = alias_name.lower().replace(" ", "_")
    
    alias = FontAlias(
        font_id=font_id,
        alias_name=alias_name,
        alias_normalized=alias_normalized,
        source_type=source_type or "manual",
    )
    
    db.add(alias)
    db.commit()
    db.refresh(alias)
    
    return alias
