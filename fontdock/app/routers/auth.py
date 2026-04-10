"""Authentication router."""
import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import UserLogin, Token, User
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_token,
    get_user_by_username,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from token and verify session is active."""
    from app.models import UserSession
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = decode_token(token)
    if token_data is None or token_data.username is None:
        raise credentials_exception
    
    user = get_user_by_username(db, token_data.username)
    if user is None:
        raise credentials_exception
    
    # Check if user has any active sessions - if not, token is revoked
    active_session = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True
    ).first()
    
    if not active_session:
        raise credentials_exception
    
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current user and verify they are admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """Login and get access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=60 * 24)  # 1 day
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Track session - first clear any existing active sessions for this user
    from app.models import UserSession
    import uuid
    
    # Deactivate all existing sessions for this user
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True
    ).update({"is_active": False})
    
    session = UserSession(
        user_id=user.id,
        token_jti=str(uuid.uuid4()),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        is_active=True
    )
    db.add(session)
    db.commit()
    
    logger.info(f"[AUDIT] User login: username='{user.username}', ip='{request.client.host if request.client else 'unknown'}'")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get current authenticated user info."""
    return current_user


@router.get("/sessions", response_model=list)
async def get_active_sessions(
    current_user: Annotated[dict, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    """Get all active user sessions (admin only)."""
    from app.models import UserSession, User
    from sqlalchemy.orm import joinedload
    
    sessions = db.query(UserSession).options(
        joinedload(UserSession.user)
    ).filter(UserSession.is_active == True).all()
    
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "username": s.user.username if s.user else None,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
        }
        for s in sessions
    ]


@router.post("/logout-user/{user_id}")
async def logout_user(
    user_id: int,
    current_user: Annotated[dict, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    """Force logout a specific user by invalidating all their sessions (admin only)."""
    from app.models import UserSession
    
    # Deactivate all sessions for this user
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).all()
    
    for session in sessions:
        session.is_active = False
    
    db.commit()
    
    return {
        "success": True, 
        "message": f"Logged out {len(sessions)} session(s) for user",
        "sessions_revoked": len(sessions)
    }


@router.post("/logout-session/{session_id}")
async def logout_session(
    session_id: int,
    current_user: Annotated[dict, Depends(get_current_admin)],
    db: Session = Depends(get_db),
):
    """Revoke a specific session by ID (admin only)."""
    from app.models import UserSession
    
    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    session.is_active = False
    db.commit()
    
    return {"success": True, "message": "Session revoked"}
