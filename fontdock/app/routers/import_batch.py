"""Batch import router for bulk font ingestion from folder structures."""
import os
import hashlib
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers.auth import get_current_admin
from app.models import User, Font as FontModel, FontFamily, Client, FontLicense
from app.services.font_ingest_service import extract_font_metadata, normalize_family_name

router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)


def calculate_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_font_files(folder_path: str) -> tuple:
    """Recursively find all font files and license files in folder.
    
    Returns (fonts_list, licenses_by_folder) where licenses_by_folder
    maps each folder path to a list of license file dicts.
    
    License detection strategy:
    - Files with license-related extensions (.txt, .pdf, .html, etc.)
      whose filename contains license keywords (license, eula, receipt, etc.)
    - Files inside folders named "Licenses", "License", "Legal", "EULA", etc.
      are treated as license files regardless of filename
    - License files in subfolders are associated with the parent font folder
    """
    font_extensions = {'.ttf', '.otf', '.ttc', '.woff', '.woff2'}
    license_extensions = {'.txt', '.pdf', '.rtf', '.html', '.htm', '.doc', '.docx'}
    license_keywords = {
        'license', 'licence', 'eula', 'terms', 'readme', 
        'agreement', 'legal', 'receipt', 'invoice', 'vat',
        'purchase', 'order', 'certificate', 'entitlement',
    }
    license_folder_names = {
        'licenses', 'license', 'licence', 'licences', 'legal', 'eula', 'terms',
    }
    fonts = []
    licenses_by_folder = {}
    
    for root, dirs, files in os.walk(folder_path):
        folder_licenses = []
        # Check if this folder is a license subfolder
        folder_name = os.path.basename(root).lower()
        is_license_folder = folder_name in license_folder_names
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            filepath = os.path.join(root, file)
            
            if ext in font_extensions:
                # Determine client from folder structure
                rel_path = os.path.relpath(filepath, folder_path)
                path_parts = rel_path.split(os.sep)
                
                # First folder level is client name
                client_name = path_parts[0] if len(path_parts) > 1 else 'General'
                
                fonts.append({
                    'path': filepath,
                    'filename': file,
                    'client_name': client_name,
                    'extension': ext,
                    'folder': root
                })
            elif ext in license_extensions:
                name_lower = file.lower()
                # License file if: in a license-named folder, or filename contains keywords
                is_license = (
                    is_license_folder or
                    any(kw in name_lower for kw in license_keywords)
                )
                if is_license:
                    folder_licenses.append({
                        'path': filepath,
                        'filename': file,
                        'extension': ext
                    })
        
        if folder_licenses:
            # If this is a license subfolder, associate licenses with parent folder
            # so they get attached to fonts in the parent folder
            if is_license_folder:
                parent_folder = os.path.dirname(root)
                if parent_folder not in licenses_by_folder:
                    licenses_by_folder[parent_folder] = []
                licenses_by_folder[parent_folder].extend(folder_licenses)
            else:
                if root not in licenses_by_folder:
                    licenses_by_folder[root] = []
                licenses_by_folder[root].extend(folder_licenses)
    
    return fonts, licenses_by_folder


@router.post("/batch-folder")
async def batch_import_from_folder(
    folder_path: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Batch import fonts from a folder structure.
    
    Expected structure:
    /folder_path/
      Client1/
        font1.ttf
        font2.otf
      Client2/
        font3.ttf
    
    Creates clients automatically, processes fonts, handles duplicates.
    """
    if not os.path.exists(folder_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder not found: {folder_path}"
        )
    
    # Find all font files and license files
    font_files, licenses_by_folder = find_font_files(folder_path)
    logger.info(f"[BATCH IMPORT] Found {len(font_files)} font files and {sum(len(v) for v in licenses_by_folder.values())} license files in {folder_path}")
    for f in font_files[:5]:  # Log first 5 for debugging
        logger.info(f"[BATCH IMPORT] File: {f['path']} -> Client: {f['client_name']}")
    for folder, lics in licenses_by_folder.items():
        logger.info(f"[BATCH IMPORT] License files in {folder}: {[l['filename'] for l in lics]}")
    
    if not font_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No font files found in folder"
        )
    
    results = {
        'total': len(font_files),
        'imported': 0,
        'updated': 0,
        'failed': 0,
        'licenses_attached': 0,
        'clients_created': [],
        'errors': []
    }
    
    # Track which license files have been attached to which font to avoid duplicates
    attached_license_combos = set()  # (font_id, license_path) tuples
    
    # Get or create clients
    clients_cache = {}
    
    for font_info in font_files:
        try:
            client_name = font_info['client_name']
            
            # Get or create client
            if client_name not in clients_cache:
                client = db.query(Client).filter(Client.name == client_name).first()
                if not client:
                    # Generate code from name (slugify)
                    client_code = client_name.lower().replace(' ', '-').replace('_', '-')
                    # Check if code exists, append number if needed
                    base_code = client_code
                    counter = 1
                    while db.query(Client).filter(Client.code == client_code).first():
                        client_code = f"{base_code}-{counter}"
                        counter += 1
                    
                    client = Client(
                        name=client_name,
                        code=client_code,
                        is_active=True
                    )
                    db.add(client)
                    db.commit()
                    db.refresh(client)
                    results['clients_created'].append(client_name)
                clients_cache[client_name] = client
            
            client = clients_cache[client_name]
            
            # Calculate file hash
            file_hash = calculate_file_hash(font_info['path'])
            
            # Check for duplicate by hash
            existing_font = db.query(FontModel).filter(FontModel.file_hash_sha256 == file_hash).first()
            
            if existing_font:
                # Update existing font file
                existing_font.updated_at = datetime.utcnow()
                
                # Copy new file over old one
                storage_path = f"fontdock/storage/fonts/{existing_font.id}{existing_font.extension}"
                shutil.copy2(font_info['path'], storage_path)
                
                results['updated'] += 1
            else:
                # Extract metadata
                metadata = extract_font_metadata(font_info['path'])
                
                # Get or create font family
                family_name = metadata.get('typographic_family') or metadata.get('family_name')
                if not family_name:
                    # Try to get family name from parent folder (client name is folder name)
                    family_name = client.name  # Use client name as fallback for family grouping
                if not family_name:
                    family_name = os.path.splitext(font_info['filename'])[0]
                
                # Log for debugging
                if not metadata.get('typographic_family') and not metadata.get('family_name'):
                    logger.warning(f"Font {font_info['filename']} has no family metadata in name tables, using: {family_name}")
                
                normalized = family_name.lower().replace(" ", "_") if family_name else None
                family = db.query(FontFamily).filter(FontFamily.normalized_name == normalized).first()
                if not family:
                    display_name = normalize_family_name(family_name)
                    family = FontFamily(
                        name=display_name,
                        normalized_name=normalized,
                        foundry=metadata.get('manufacturer'),
                        notes=metadata.get('description')
                    )
                    db.add(family)
                    db.commit()
                    db.refresh(family)
                
                # Create font record (no client_id, use many-to-many)
                temp_storage_path = f"pending/{font_info['filename']}"
                font = FontModel(
                    family_id=family.id,
                    filename_original=font_info['filename'],
                    filename_storage=font_info['filename'],
                    storage_path=temp_storage_path,
                    style_name=metadata.get('style_name'),
                    postscript_name=metadata.get('postscript_name'),
                    extension=font_info['extension'],
                    file_hash_sha256=file_hash,
                    file_size_bytes=os.path.getsize(font_info['path']),
                    version_string=metadata.get('version'),
                    is_active=True
                )
                db.add(font)
                db.commit()
                db.refresh(font)
                
                # Assign font to client using many-to-many relationship
                if font not in client.fonts:
                    client.fonts.append(font)
                    db.commit()
                
                # Copy file to storage with correct path
                storage_dir = Path("fontdock/storage/fonts")
                storage_dir.mkdir(parents=True, exist_ok=True)
                final_storage_path = storage_dir / f"{font.id}{font.extension}"
                shutil.copy2(font_info['path'], final_storage_path)
                
                # Update font with correct storage path
                font.storage_path = str(final_storage_path)
                db.commit()
                
                results['imported'] += 1
            
            # Auto-attach license files from the same folder
            font_folder = font_info.get('folder', os.path.dirname(font_info['path']))
            folder_licenses = licenses_by_folder.get(font_folder, [])
            for lic_info in folder_licenses:
                combo = (font.id, lic_info['path'])
                if combo in attached_license_combos:
                    continue
                try:
                    import uuid
                    lic_ext = lic_info['extension']
                    lic_storage_name = f"{uuid.uuid4().hex}{lic_ext}"
                    lic_storage_dir = Path("./storage/licenses")
                    lic_storage_dir.mkdir(parents=True, exist_ok=True)
                    lic_storage_path = lic_storage_dir / lic_storage_name
                    shutil.copy2(lic_info['path'], lic_storage_path)
                    
                    license_record = FontLicense(
                        font_id=font.id,
                        license_type='desktop',
                        filename_original=lic_info['filename'],
                        filename_storage=lic_storage_name,
                        storage_path=str(lic_storage_path),
                        notes='Auto-attached during batch import'
                    )
                    db.add(license_record)
                    attached_license_combos.add(combo)
                    results['licenses_attached'] += 1
                    logger.info(f"[BATCH IMPORT] Attached license {lic_info['filename']} to font {font.postscript_name or font.filename_original}")
                except Exception as e:
                    logger.warning(f"[BATCH IMPORT] Failed to attach license {lic_info['filename']}: {e}")
            
            # Commit any license attachments for this font
            if licenses_by_folder.get(font_info.get('folder', os.path.dirname(font_info['path']))):
                db.commit()
                
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"{font_info['filename']}: {str(e)}")
    
    return {
        'success': True,
        'message': f"Batch import complete: {results['imported']} imported, {results['updated']} updated, {results['failed']} failed, {results['licenses_attached']} licenses attached",
        'clients_created': results['clients_created'],
        'errors': results['errors'],
        'results': results
    }


@router.post("/upload-zip")
async def batch_import_from_zip(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Upload and import fonts from a ZIP file with folder structure."""
    import zipfile
    import tempfile
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are supported"
        )
    
    # Save and extract ZIP
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "upload.zip")
        
        with open(zip_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Extract
        extract_dir = os.path.join(tmpdir, "extracted")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Process as folder import
        return await batch_import_from_folder(
            folder_path=extract_dir,
            background_tasks=background_tasks,
            current_user=current_user,
            db=db
        )


@router.get("/browse")
async def browse_folders(
    path: str = "",
    current_user: User = Depends(get_current_admin),
):
    """Browse server folders for import selection."""
    import glob
    
    # Default to home directory if no path provided
    if not path:
        path = os.path.expanduser("~")
    
    # Security: prevent traversal outside reasonable bounds
    if ".." in path or path.startswith("/"):
        # Normalize and check
        real_path = os.path.realpath(path)
        home = os.path.realpath(os.path.expanduser("~"))
        if not real_path.startswith(home) and not real_path.startswith("/Users") and not real_path.startswith("/home"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access this directory"
            )
    
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path not found: {path}"
        )
    
    if not os.path.isdir(path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a directory: {path}"
        )
    
    try:
        items = os.listdir(path)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    folders = []
    for item in sorted(items):
        full_path = os.path.join(path, item)
        if os.path.isdir(full_path):
            folders.append({
                "name": item,
                "path": full_path,
            })
    
    return {
        "current_path": path,
        "parent_path": os.path.dirname(path) if path != os.path.dirname(path) else None,
        "folders": folders
    }


@router.get("/status/{task_id}")
async def get_import_status(
    task_id: str,
    current_user: User = Depends(get_current_admin),
):
    """Get status of background import task."""
    # TODO: Implement background task tracking
    return {'task_id': task_id, 'status': 'pending'}
