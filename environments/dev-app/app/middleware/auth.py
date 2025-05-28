# app/middleware/auth.py
from fastapi import Request, HTTPException, Depends, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
import string

from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.core.config import settings
from app.core.logging import logger

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    api_key = settings.API_KEY_PREFIX + '_' + ''.join(
        secrets.choice(alphabet) for _ in range(settings.API_KEY_LENGTH)
    )
    return api_key


async def get_api_key(
    api_key_header: str = Depends(API_KEY_HEADER), db: Session = Depends(get_db)
) -> ApiKey:
    """
    Validate the API key and return the associated ApiKey object
    Updates last_used_at timestamp
    """
    if not api_key_header:
        logger.warning("API Key missing from request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing",
        )
    
    api_key = db.query(ApiKey).filter(ApiKey.key == api_key_header).first()
    
    if not api_key:
        logger.warning(f"Invalid API Key attempt: {api_key_header[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    
    if not api_key.is_active:
        logger.warning(f"Inactive API Key used: {api_key.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is inactive",
        )
    
    if api_key.expires_at and api_key.expires_at < datetime.now():
        logger.warning(f"Expired API Key used: {api_key.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key has expired",
        )
    
    # Update last used timestamp
    api_key.last_used_at = datetime.now()
    db.commit()
    
    return api_key


async def get_current_user(
    api_key: ApiKey = Depends(get_api_key), db: Session = Depends(get_db)
) -> User:
    """
    Get the current user based on the API key
    """
    user = db.query(User).filter(User.id == api_key.user_id).first()
    
    if not user:
        logger.error(f"User not found for API key: {api_key.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted to use API: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )
    
    return user


def team_access_required(image_team_id: int, user: User) -> bool:
    """
    Check if a user has access to resources owned by a particular team
    """
    return user.team_id == image_team_id or user.is_admin
