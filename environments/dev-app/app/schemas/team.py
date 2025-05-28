# app/schemas/team.py
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampMixin


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Team(TeamBase, TimestampMixin, BaseSchema):
    id: int


# Define TeamWithUsers without direct reference to User
class TeamWithUsers(Team):
    # Use Any type to avoid circular imports
    users: List[Any] = []
