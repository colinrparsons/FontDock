#!/usr/bin/env python3
"""Change user password script."""
import sys
import getpass
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db import SessionLocal
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def change_password():
    """Change user password."""
    db = SessionLocal()
    try:
        # Get username
        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty!")
            return
        
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found!")
            return
        
        # Get new password
        password = getpass.getpass("New password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            print("Passwords do not match!")
            return
        
        if len(password) < 6:
            print("Password must be at least 6 characters!")
            return
        
        # Update password
        user.password_hash = pwd_context.hash(password)
        db.commit()
        
        print(f"✓ Password updated for user '{username}'")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    change_password()
