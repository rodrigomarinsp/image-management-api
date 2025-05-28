# app/api/endpoints/api_keys.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets
import string
from datetime import datetime, timedelta

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.api_key import ApiKey
from app.core.config import settings
from app.schemas.api_key import ApiKey as ApiKeySchema, ApiKeyCreate, ApiKeyUpdate, ApiKeyCreateResponse


router = APIRouter()


def generate_api_key() -> str:
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    api_key = settings.API_KEY_PREFIX + '_' + ''.join(
        secrets.choice(alphabet) for _ in range(settings.API_KEY_LENGTH)
    )
    return api_key


@router.get("/", response_model=List[ApiKeySchema])
def get_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """
    Get all API keys for the current user
    """
    return db.query(ApiKey).filter(ApiKey.user_id == current_user.id).offset(skip).limit(limit).all()


@router.get("/{api_key_id}", response_model=ApiKeySchema)
def get_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific API key
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id, ApiKey.user_id == current_user.id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or doesn't belong to the current user"
        )
    return api_key


@router.post("/", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    api_key_in: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key for the current user
    """
    # Check if a name is already used by this user
    existing_key = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id,
        ApiKey.name == api_key_in.name
    ).first()
    
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An API key with this name already exists"
        )
    
    # Generate API key
    api_key_str = generate_api_key()
    
    # Set expiry date if provided
    expires_at = None
    if api_key_in.expires_at:
        expires_at = api_key_in.expires_at
    
    # Create API key object
    api_key = ApiKey(
        key=api_key_str,
        name=api_key_in.name,
        is_active=True,
        user_id=current_user.id,
        expires_at=expires_at
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # Return with the key visible (it won't be visible later)
    return ApiKeyCreateResponse(
        api_key=api_key_str,
        id=api_key.id,
        name=api_key.name,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at
    )


@router.put("/{api_key_id}", response_model=ApiKeySchema)
def update_api_key(
    api_key_id: int,
    api_key_in: ApiKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an API key (name, active status, expiry)
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id, ApiKey.user_id == current_user.id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or doesn't belong to the current user"
        )
    
    # Check name uniqueness if changing name
    if api_key_in.name and api_key_in.name != api_key.name:
        existing_key = db.query(ApiKey).filter(
            ApiKey.user_id == current_user.id,
            ApiKey.name == api_key_in.name,
            ApiKey.id != api_key_id
        ).first()
        
        if existing_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An API key with this name already exists"
            )
    
    # Update fields
    update_data = api_key_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)
    
    db.commit()
    db.refresh(api_key)
    return api_key


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an API key
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id, ApiKey.user_id == current_user.id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or doesn't belong to the current user"
        )
    
    db.delete(api_key)
    db.commit()
    return None
