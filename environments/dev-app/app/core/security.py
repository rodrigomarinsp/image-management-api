# app/core/security.py
import secrets
import string
from typing import Optional
from datetime import datetime, timedelta
from app.core.config import settings


def generate_secure_random_string(length: int = 32) -> str:
    """Generate a secure random string with the specified length."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_api_key() -> str:
    """
    Create a new API key with a prefix for easier identification.
    Format: prefix_randomstring
    """
    random_part = generate_secure_random_string(settings.API_KEY_LENGTH)
    return f"{settings.API_KEY_PREFIX}_{random_part}"


def get_expiry_date(days: Optional[int] = None) -> Optional[datetime]:
    """
    Calculate an expiry date from now.
    If days is None, returns None (no expiry).
    """
    if days is None:
        return None
    return datetime.utcnow() + timedelta(days=days)
