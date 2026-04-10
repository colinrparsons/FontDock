#!/usr/bin/env python3
"""Reset admin password to default."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db import SessionLocal
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def reset_admin_password():
    """Reset admin password to 'admin123'."""
    db = SessionLocal()
    try:
        # Find admin user
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("❌ Admin user not found!")
            return
        
        # Reset password to default
        password = "admin123"
        # Truncate to 72 characters for bcrypt compatibility
        if len(password) > 72:
            password = password[:72]
        admin.password_hash = pwd_context.hash(password)
        db.commit()
        
        print("✅ Admin password reset to: admin123")
        print("   Username: admin")
        print("   Password: admin123")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    reset_admin_password()
