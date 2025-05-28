# app/schemas/api_key.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampMixin


class ApiKeyBase(BaseModel):
    name: str
    is_active: bool = True
    user_id: int
    expires_at: Optional[datetime] = None


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ApiKey(ApiKeyBase, TimestampMixin, BaseSchema):
    id: int
    key: str
    last_used_at: Optional[datetime] = None


class ApiKeyCreateResponse(BaseModel):
    api_key: str
    id: int
    name: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
