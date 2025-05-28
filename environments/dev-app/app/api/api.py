# app/api/api.py
from fastapi import APIRouter

api_router = APIRouter()

# Import test endpoint for initial testing
from app.api.endpoints.test import router as test_router
api_router.include_router(test_router, prefix="/test", tags=["test"])

# Import team endpoints
from app.api.endpoints.teams import router as teams_router
api_router.include_router(teams_router, prefix="/teams", tags=["teams"])

# Import user endpoints
from app.api.endpoints.users import router as users_router
api_router.include_router(users_router, prefix="/users", tags=["users"])

#Import API key endpoints
from app.api.endpoints.api_keys import router as api_keys_router
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])

# Import image endpoints
# from app.api.endpoints.images import router as images_router
# api_router.include_router(images_router, prefix="/images", tags=["images"])
