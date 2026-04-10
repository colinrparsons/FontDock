#!/usr/bin/env python3
"""
Save FontDock documentation to the brain
Uses the brain API directly via HTTP
"""

import httpx
import os
import sys

BRAIN_API = os.environ.get("BRAIN_API", "http://192.168.0.49:8000")
DOCS_DIR = "/Users/colinparsons/Documents/Developement/FontDock/docs"

def save_to_brain(text, project="FontDock", type_="documentation"):
    """Save a memory to the brain."""
    try:
        response = httpx.post(
            f"{BRAIN_API}/save_memory",
            json={
                "text": text,
                "project": project,
                "type": type_
            },
            timeout=30.0
        )
        result = response.json()
        if result.get("status") == "ok" or result.get("success"):
            print(f"  ✓ Saved: {text[:60]}...")
            return True
        else:
            print(f"  ✗ Failed: {result}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def read_doc_file(filename):
    """Read a documentation file."""
    filepath = os.path.join(DOCS_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r') as f:
        return f.read()

def main():
    print(f"Connecting to brain at {BRAIN_API}...")
    
    # Check brain is online (try root endpoint)
    try:
        response = httpx.get(f"{BRAIN_API}/", timeout=5.0)
        if response.status_code == 200:
            print("Brain server is online ✓")
        else:
            print(f"Brain server responded with status {response.status_code}")
    except Exception as e:
        print(f"Cannot connect to brain server: {e}")
        print("Make sure the brain server is running at 192.168.0.49:8000")
        sys.exit(1)
    
    print("\nSaving FontDock documentation to brain...\n")
    
    # Save project overview
    overview = read_doc_file("01-project-overview.md")
    if overview:
        print("Saving: Project Overview")
        save_to_brain(overview, "FontDock", "project_overview")
    
    # Save architecture
    architecture = read_doc_file("02-system-architecture.md")
    if architecture:
        print("Saving: System Architecture")
        save_to_brain(architecture, "FontDock", "architecture")
    
    # Save backend spec (includes what we built)
    backend = read_doc_file("03-server-backend-spec.md")
    if backend:
        print("Saving: Server Backend Spec (includes MVP status)")
        save_to_brain(backend, "FontDock", "backend_spec")
    
    # Save database schema
    database = read_doc_file("04-database-schema.md")
    if database:
        print("Saving: Database Schema")
        save_to_brain(database, "FontDock", "database_schema")
    
    # Save web UI spec
    webui = read_doc_file("05-web-ui-spec.md")
    if webui:
        print("Saving: Web UI Spec")
        save_to_brain(webui, "FontDock", "webui_spec")
    
    # Save development roadmap
    roadmap = read_doc_file("11-development-roadmap.md")
    if roadmap:
        print("Saving: Development Roadmap")
        save_to_brain(roadmap, "FontDock", "roadmap")
    
    # Save MVP checklist
    checklist = read_doc_file("12-mvp-checklist.md")
    if checklist:
        print("Saving: MVP Checklist")
        save_to_brain(checklist, "FontDock", "checklist")
    
    # Save current project status
    status = """# FontDock MVP Status - April 2, 2026

## COMPLETED

### Core Infrastructure
- FastAPI backend with SQLite, SQLAlchemy, JWT auth
- Font ingestion with metadata extraction (typographic family names)
- File storage with SHA256 deduplication
- Granular permissions system

### API Endpoints
- Auth, Fonts, Collections, Clients, Users, Admin

### Web UI
- Login, Dashboard, Fonts, Collections, Clients, Upload
- Users, Permissions, Logs pages
- Server restart button, log viewer, username display

### Key Features
- Font preview with actual @font-face rendering
- Family grouping with "Add All" to collections
- Permission-based access (not just admin)

## PENDING (Tomorrow)

1. Backup system (DB + font files)
2. Font activation flow (collection download all, tracking)
3. Search improvements (full-text, aliases, fuzzy)
4. Production hardening (PostgreSQL, migrations)

## Technical Stack
Python 3.11+, FastAPI, SQLAlchemy, Pydantic, fontTools, PyJWT, passlib, Jinja2, SQLite
"""
    print("Saving: Current Project Status")
    save_to_brain(status, "FontDock", "current_status")
    
    print("\n✓ All documentation saved to brain!")
    print(f"Visit {BRAIN_API}/ to view memories")

if __name__ == "__main__":
    main()
