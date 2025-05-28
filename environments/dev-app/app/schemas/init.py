# app/schemas/__init__.py
# Import schemas in correct order to avoid circular imports
from app.schemas.base import BaseSchema, TimestampMixin
from app.schemas.team import TeamBase, TeamCreate, TeamUpdate, Team
from app.schemas.user import UserBase, UserCreate, UserUpdate, User
from app.schemas.api_key import ApiKeyBase, ApiKeyCreate, ApiKeyUpdate, ApiKey, ApiKeyCreateResponse
from app.schemas.image import ImageBase, ImageCreate, ImageUpdate, Image, ImageResponse, ImageSearchResult

# Import the with-relations classes after all base classes are defined
from app.schemas.team import TeamWithUsers
from app.schemas.user import UserWithApiKeys

# Update forward references only after all classes are defined
# Add this after all imports to avoid circular dependencies
# We will comment these out for now until we fix the circular references
# TeamWithUsers.update_forward_refs()
# UserWithApiKeys.update_forward_refs()
