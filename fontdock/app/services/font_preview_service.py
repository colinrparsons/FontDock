"""Font preview service for generating visual previews."""
import base64
import io
from pathlib import Path
from typing import Optional, Tuple

from fontTools.ttLib import TTFont


def generate_font_preview(
    font_path: Path,
    preview_text: str = "AaBbCc",
    size: int = 48,
    width: int = 300,
    height: int = 80
) -> Optional[str]:
    """
    Generate a font preview as base64-encoded SVG.
    
    Args:
        font_path: Path to the font file
        preview_text: Text to render in the preview
        size: Font size in pixels
        width: Preview width in pixels
        height: Preview height in pixels
    
    Returns:
        Base64-encoded SVG string, or None if generation fails
    """
    try:
        font = TTFont(str(font_path))
        
        # Get font metrics
        units_per_em = font['head'].unitsPerEm
        
        # Calculate scale factor
        scale = size / units_per_em
        
        # Get glyph indices for preview text
        cmap = font.getBestCmap()
        if not cmap:
            # Fallback to a simple ASCII cmap
            cmap = {}
        
        # Build SVG path data
        paths = []
        x_offset = 10
        
        for char in preview_text:
            char_code = ord(char)
            glyph_name = cmap.get(char_code)
            
            if glyph_name and 'glyf' in font:
                glyf_table = font['glyf']
                glyph = glyf_table.get(glyph_name)
                
                if glyph:
                    # Get glyph width
                    hmtx = font['hmtx']
                    advance_width, lsb = hmtx.get(glyph_name, (units_per_em, 0))
                    
                    # Convert glyph to SVG path (simplified)
                    path_data = _glyph_to_svg_path(glyph, x_offset, height - 20, scale)
                    if path_data:
                        paths.append(path_data)
                    
                    x_offset += advance_width * scale + 5
        
        font.close()
        
        # Build SVG
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            <rect width="{width}" height="{height}" fill="#f8f9fa"/>
            <text x="10" y="{height//2 + 10}" font-family="Arial, sans-serif" font-size="14" fill="#666">
                Preview not available
            </text>
        </svg>'''
        
        if paths:
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
                <rect width="{width}" height="{height}" fill="#f8f9fa"/>
                <g fill="#333">
                    {"".join(paths)}
                </g>
            </svg>'''
        
        # Encode as base64
        svg_bytes = svg.encode('utf-8')
        base64_svg = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{base64_svg}"
        
    except Exception as e:
        # Return a placeholder on error
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
            <rect width="{width}" height="{height}" fill="#f8f9fa"/>
            <text x="10" y="{height//2 + 5}" font-family="Arial, sans-serif" font-size="14" fill="#666">
                {preview_text}
            </text>
        </svg>'''
        svg_bytes = svg.encode('utf-8')
        base64_svg = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{base64_svg}"


def _glyph_to_svg_path(glyph, x_offset: float, y_offset: float, scale: float) -> str:
    """Convert a TrueType glyph to SVG path data."""
    # Simplified path extraction - returns empty for complex glyphs
    # For a complete implementation, you'd parse the glyph contours
    return ""


def get_font_sample_text(font_path: Path) -> str:
    """Get appropriate sample text for a font based on its characteristics."""
    try:
        font = TTFont(str(font_path))
        
        # Check for common character sets
        cmap = font.getBestCmap()
        
        # Default sample text
        sample = "AaBbCc 123"
        
        # Try to find a good sample based on available glyphs
        if cmap:
            # Build sample from available characters
            chars = []
            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
                if ord(char) in cmap:
                    chars.append(char)
                    if len(chars) >= 10:
                        break
            if chars:
                sample = "".join(chars[:8])
        
        font.close()
        return sample
        
    except Exception:
        return "AaBbCc"
