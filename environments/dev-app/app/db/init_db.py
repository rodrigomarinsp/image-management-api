# app/db/init_db.py
import logging
from sqlalchemy.orm import Session
import secrets
import string

from app.models.team import Team
from app.models.user import User
from app.models.api_key import ApiKey
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    api_key = settings.API_KEY_PREFIX + '_' + ''.join(
        secrets.choice(alphabet) for _ in range(settings.API_KEY_LENGTH)
    )
    return api_key


def init_db(db: Session) -> None:
    """Initialize the database with seed data"""
    # Check if we already have data
    existing_team = db.query(Team).first()
    if existing_team:
        logger.info("Database already contains data, skipping initialization")
        return
        
    logger.info("Creating initial data")
    
    # Create default team
    default_team = Team(name="Default Team", description="Default team created during initialization")
    db.add(default_team)
    db.flush()  # Flush to get team ID
    
    # Create admin user
    admin_user = User(
        email="admin@example.com",
        name="Admin User",
        is_active=True,
        is_admin=True,
        team_id=default_team.id
    )
    db.add(admin_user)
    db.flush()  # Flush to get user ID
    
    # Create API key for admin
    admin_api_key = ApiKey(
        key=generate_api_key(),
        name="Admin API Key",
        is_active=True,
        user_id=admin_user.id
    )
    db.add(admin_api_key)
    
    # Create regular user
    regular_user = User(
        email="user@example.com",
        name="Regular User",
        is_active=True,
        is_admin=False,
        team_id=default_team.id
    )
    db.add(regular_user)
    db.flush()  # Flush to get user ID
    
    # Create API key for regular user
    user_api_key = ApiKey(
        key=generate_api_key(),
        name="User API Key",
        is_active=True,
        user_id=regular_user.id
    )
    db.add(user_api_key)
    
    # Commit all changes
    db.commit()
    
    # Log the created data
    logger.info(f"Created default team: {default_team.name}")
    logger.info(f"Created admin user: {admin_user.email} with API key: {admin_api_key.key}")
    logger.info(f"Created regular user: {regular_user.email} with API key: {user_api_key.key}")
    logger.info("Initial data created successfully")
