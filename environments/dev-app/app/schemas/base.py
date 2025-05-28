# app/schemas/base.py
from datetime import datetime
from pydantic import BaseModel


class TimestampMixin(BaseModel):
    """Timestamp fields for database models"""
    created_at: datetime
    updated_at: datetime


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
