"""Main FastAPI application."""
import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload

from app.db import engine, Base, get_db
from app.config import get_settings
from app.routers import auth, fonts, collections, clients, users, admin as admin_router, import_batch, change_password, groups, licenses
from app.routers.auth import get_current_user, get_current_admin
from app.logging_config import setup_logging

# Setup logging with file output
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

# Load templates manually with jinja2
from jinja2 import Environment, FileSystemLoader
template_dir = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    auto_reload=True,
    cache_size=0,
)


def render_template(template_name: str, **context) -> str:
    """Render a Jinja2 template to string."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Template dir: {template_dir}, exists: {template_dir.exists()}")
    Base.metadata.create_all(bind=engine)
    # Start automatic backup scheduler
    from app.routers.admin import start_backup_scheduler
    start_backup_scheduler()
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="Font server and management system for creative teams",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router)
    app.include_router(fonts.router)
    app.include_router(collections.router)
    app.include_router(clients.router)
    app.include_router(users.router)
    app.include_router(admin_router.router)
    app.include_router(import_batch.router)
    app.include_router(change_password.router)
    app.include_router(groups.router)
    app.include_router(licenses.router)
    
    # Mount static files (for images, CSS, JS)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Mounted static files from {static_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
    
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "docs_url": "/docs",
        }
    
    # Favicon and apple-touch-icon routes (browsers request these at root)
    static_dir = Path(__file__).parent / "static"
    
    @app.get("/favicon.ico")
    async def favicon():
        ico_path = static_dir / "favicon.ico"
        if ico_path.exists():
            return FileResponse(str(ico_path), media_type="image/x-icon")
        return FileResponse(str(static_dir / "favicon.svg"), media_type="image/svg+xml")
    
    @app.get("/favicon.svg")
    async def favicon_svg():
        return FileResponse(str(static_dir / "favicon.svg"), media_type="image/svg+xml")
    
    @app.get("/apple-touch-icon.png")
    async def apple_touch_icon():
        png_path = static_dir / "apple-touch-icon.png"
        if png_path.exists():
            return FileResponse(str(png_path), media_type="image/png")
        return FileResponse(str(static_dir / "favicon.svg"), media_type="image/svg+xml")
    
    @app.get("/apple-touch-icon-precomposed.png")
    async def apple_touch_icon_precomposed():
        png_path = static_dir / "apple-touch-icon-precomposed.png"
        if png_path.exists():
            return FileResponse(str(png_path), media_type="image/png")
        return FileResponse(str(static_dir / "apple-touch-icon.png"), media_type="image/png")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    # Web UI routes using manual jinja2 rendering
    @app.get("/ui/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        try:
            html = render_template("login.html", request=request)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Login page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/fonts", response_class=HTMLResponse)
    async def fonts_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import Font, FontFamily
            # Get all families with their fonts, filter out empty families
            families = db.query(FontFamily).all()
            families_with_fonts = []
            for family in families:
                family.fonts = db.query(Font).filter(Font.family_id == family.id).all()
                if family.fonts:  # Only include families that have fonts
                    families_with_fonts.append(family)
            html = render_template("fonts.html", request=request, families=families_with_fonts)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Fonts page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/upload", response_class=HTMLResponse)
    async def upload_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import Client, Collection
            clients = db.query(Client).filter(Client.is_active == True).all()
            collections = db.query(Collection).filter(Collection.is_active == True).all()
            
            # Group collections by client
            collections_by_client = {}
            for c in collections:
                client_id = c.client_id if c.client_id else 0
                if client_id not in collections_by_client:
                    collections_by_client[client_id] = []
                collections_by_client[client_id].append({"id": c.id, "name": c.name})
            
            html = render_template("upload.html", 
                request=request, 
                clients=clients,
                collections_by_client=collections_by_client
            )
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Upload page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/import", response_class=HTMLResponse)
    async def import_batch_page(
        request: Request,
    ):
        try:
            html = render_template("import_batch.html", request=request)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Import batch page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/dashboard", response_class=HTMLResponse)
    async def dashboard_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import Font, FontFamily, Collection, Client
            total_fonts = db.query(Font).count()
            # Only count families that have at least one font
            total_families = db.query(FontFamily).join(Font).distinct().count()
            total_collections = db.query(Collection).count()
            total_clients = db.query(Client).filter(Client.is_active == True).count()
            recent_fonts = db.query(Font).order_by(Font.created_at.desc()).limit(10).all()
            
            html = render_template("dashboard.html", 
                request=request,
                total_fonts=total_fonts,
                total_families=total_families,
                total_collections=total_collections,
                total_clients=total_clients,
                recent_fonts=recent_fonts
            )
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Dashboard page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/collections", response_class=HTMLResponse)
    async def collections_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from sqlalchemy.orm import joinedload
            from app.models import Collection, Client
            collections = db.query(Collection).options(
                joinedload(Collection.client)
            ).filter(Collection.is_active == True).all()
            clients = db.query(Client).filter(Client.is_active == True).order_by(Client.name).all()
            html = render_template("collections.html", request=request, collections=collections, clients=clients)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Collections page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/collections/{collection_id}", response_class=HTMLResponse)
    async def collection_detail_page(
        request: Request,
        collection_id: int,
        db: Session = Depends(get_db),
    ):
        try:
            from sqlalchemy.orm import joinedload
            from app.models import Collection, Font
            collection = db.query(Collection).options(
                joinedload(Collection.fonts).joinedload(Font.family)
            ).filter(Collection.id == collection_id).first()
            if not collection:
                return HTMLResponse(content="<h1>Collection not found</h1>", status_code=404)
            html = render_template("collection_detail.html", request=request, collection=collection)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Collection detail page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/clients", response_class=HTMLResponse)
    async def clients_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import Client, Font
            clients = db.query(Client).all()
            # Get font count for each client (many-to-many)
            clients_with_counts = []
            for client in clients:
                font_count = len(client.fonts)
                clients_with_counts.append({
                    'client': client,
                    'font_count': font_count
                })
            html = render_template("clients.html", request=request, clients_with_counts=clients_with_counts)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Clients page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/clients/{client_id}/fonts", response_class=HTMLResponse)
    async def client_fonts_page(
        request: Request,
        client_id: int,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import Client, Font, FontFamily
            from collections import defaultdict
            
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return HTMLResponse(content="<h1>Client not found</h1>", status_code=404)
            
            # Get assigned fonts with family info (many-to-many)
            fonts = client.fonts
            
            # Group assigned fonts by family
            families_map = defaultdict(lambda: {"id": None, "name": "Unknown Family", "fonts": [], "formats": set()})
            for font in fonts:
                family_name = font.family.name if font.family else "Unknown Family"
                family_id = font.family.id if font.family else 0
                if families_map[family_name]["id"] is None:
                    families_map[family_name]["id"] = family_id
                    families_map[family_name]["name"] = family_name
                families_map[family_name]["fonts"].append(font)
                if font.extension:
                    families_map[family_name]["formats"].add(font.extension.upper().replace('.', ''))
            
            # Convert to list for template
            families = []
            for name, data in families_map.items():
                families.append({
                    "id": data["id"],
                    "name": data["name"],
                    "fonts": data["fonts"],
                    "formats": list(data["formats"])
                })
            
            html = render_template("client_fonts.html", request=request, client=client, 
                                 fonts=fonts, families=families, total_fonts=len(fonts))
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Client fonts page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/users", response_class=HTMLResponse)
    async def users_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import User
            users = db.query(User).filter(User.is_active == True).all()
            html = render_template("users.html", request=request, users=users)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Users page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/groups", response_class=HTMLResponse)
    async def groups_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            html = render_template("groups.html", request=request)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Groups page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/permissions", response_class=HTMLResponse)
    async def permissions_page(
        request: Request,
        db: Session = Depends(get_db),
    ):
        try:
            from app.models import User
            users = db.query(User).filter(User.is_active == True).all()
            html = render_template("permissions.html", request=request, users=users)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Permissions page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/logs", response_class=HTMLResponse)
    async def logs_page(
        request: Request,
    ):
        try:
            html = render_template("logs.html", request=request)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Logs page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    @app.get("/ui/backup", response_class=HTMLResponse)
    async def backup_page(
        request: Request,
    ):
        try:
            html = render_template("backup.html", request=request)
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Backup page error: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>Error: {e}</h1><pre>{traceback.format_exc()}</pre>", status_code=500)
    
    return app


app = create_app()
