"""FontDock configuration."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "FontDock"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    
    # Server (for run.py)
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Database
    database_url: str = "sqlite:///./fontdock.db"
    
    # Storage
    storage_path: Path = Path("./storage/fonts")
    
    # Logging
    log_level: str = "INFO"
    
    # Auth
    access_token_expire_minutes: int = 60 * 24  # 1 day
    
    # Upload
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: set[str] = {".otf", ".ttf", ".ttc"}
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
