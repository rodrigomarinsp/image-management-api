# app/db/base.py
from app.db.session import Base

# Import models here so they are registered with SQLAlchemy
# We'll import them as needed
# app/db/base.py
from app.db.session import Base

# Import all models for Alembic to detect
from app.models.team import Team
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.image import Image
