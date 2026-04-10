"""Font search service."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models import Font, FontFamily, FontAlias, Collection, Client, Tag


def search_fonts(
    db: Session,
    query: Optional[str] = None,
    family_id: Optional[int] = None,
    client_id: Optional[int] = None,
    collection_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    skip: int = 0,
    limit: int = 50,
) -> tuple[List[Font], int]:
    """Search fonts with filters.
    
    Returns:
        Tuple of (fonts_list, total_count)
    """
    q = db.query(Font)
    
    # Join with family for search
    q = q.join(FontFamily, Font.family_id == FontFamily.id)
    
    # Apply text search
    if query:
        search_term = f"%{query}%"
        q = q.filter(
            or_(
                Font.postscript_name.ilike(search_term),
                Font.full_name.ilike(search_term),
                Font.style_name.ilike(search_term),
                FontFamily.name.ilike(search_term),
            )
        )
    
    # Apply filters
    if family_id:
        q = q.filter(Font.family_id == family_id)
    
    if is_active is not None:
        q = q.filter(Font.is_active == is_active)
    
    # Filter by collection
    if collection_id:
        from app.models import collection_fonts
        q = q.join(
            collection_fonts,
            Font.id == collection_fonts.c.font_id
        ).filter(collection_fonts.c.collection_id == collection_id)
    
    # Filter by client (through collections)
    if client_id:
        from app.models import collection_fonts
        q = q.join(
            collection_fonts,
            Font.id == collection_fonts.c.font_id
        ).join(
            Collection,
            collection_fonts.c.collection_id == Collection.id
        ).filter(Collection.client_id == client_id)
    
    # Get total count before pagination
    total = q.count()
    
    # Apply pagination
    fonts = q.offset(skip).limit(limit).all()
    
    return fonts, total


def search_fonts_by_alias(
    db: Session,
    alias_query: str,
) -> List[Font]:
    """Search fonts by alias name."""
    search_term = f"%{alias_query}%"
    
    aliases = db.query(FontAlias).filter(
        or_(
            FontAlias.alias_name.ilike(search_term),
            FontAlias.alias_normalized.ilike(search_term),
        )
    ).all()
    
    return [alias.font for alias in aliases if alias.font]


def get_font_by_postscript_name(
    db: Session,
    postscript_name: str,
) -> Optional[Font]:
    """Get font by exact PostScript name match."""
    return db.query(Font).filter(
        Font.postscript_name == postscript_name
    ).first()


def get_fonts_in_collection(
    db: Session,
    collection_id: int,
) -> List[Font]:
    """Get all fonts in a collection."""
    from app.models import collection_fonts
    
    fonts = db.query(Font).join(
        collection_fonts,
        Font.id == collection_fonts.c.font_id
    ).filter(
        collection_fonts.c.collection_id == collection_id
    ).all()
    
    return fonts
