# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampMixin


class UserBase(BaseModel):
    email: EmailStr
    name: str
    is_active: bool = True
    is_admin: bool = False
    team_id: int


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    team_id: Optional[int] = None


class User(UserBase, TimestampMixin, BaseSchema):
    id: int


# Define UserWithApiKeys without direct reference to ApiKey
class UserWithApiKeys(User):
    # Use Any type to avoid circular imports
    api_keys: List[Any] = []
