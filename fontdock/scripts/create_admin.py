"""Create initial admin user script."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.db import SessionLocal, engine, Base
from app.services.auth_service import create_user


def create_admin():
    """Create initial admin user."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin already exists
        from app.models import User
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("Admin user already exists!")
            return
        
        # Create admin user
        user = create_user(
            db,
            username="admin",
            email="admin@fontdock.local",
            password="admin123",
            is_admin=True,
        )
        print(f"Admin user created: {user.username}")
        print("Email: admin@fontdock.local")
        print("Password: admin123")
        print("\nIMPORTANT: Change the password after first login!")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
