from app.schemas.team import Team, TeamCreate, TeamUpdate, TeamWithUsers
from app.schemas.user import User, UserCreate, UserUpdate, UserWithApiKeys
from app.schemas.api_key import ApiKey, ApiKeyCreate, ApiKeyUpdate, ApiKeyCreateResponse
from app.schemas.image import Image, ImageCreate, ImageUpdate, ImageResponse, ImageSearchResult

# Fix circular imports
from app.schemas.team import TeamWithUsers
from app.schemas.user import UserWithApiKeys
TeamWithUsers.update_forward_refs()
UserWithApiKeys.update_forward_refs()