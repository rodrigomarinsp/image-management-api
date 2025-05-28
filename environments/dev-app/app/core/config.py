# app/core/config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import secrets
from ast import literal_eval


class Settings(BaseSettings):
    PROJECT_NAME: str = "Image Management API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # Database settings
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # Google Cloud Storage
    GCS_BUCKET_NAME: str = "test-bucket"
    GCS_PROJECT_ID: str = "test-project"
    GCS_CREDENTIALS_FILE: Optional[str] = None
    
    # Vector search settings (for bonus)
    ENABLE_VECTOR_SEARCH: bool = False
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    
    # API Key settings
    API_KEY_LENGTH: int = 32
    API_KEY_PREFIX: str = "imapi"
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]

    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def __init__(self, **data: Any):
        super().__init__(**data)
        
        # Process CORS origins from string representation if needed
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            try:
                self.BACKEND_CORS_ORIGINS = literal_eval(self.BACKEND_CORS_ORIGINS)
            except:
                self.BACKEND_CORS_ORIGINS = []
                
        # Process image extensions from string representation if needed
        if isinstance(self.ALLOWED_IMAGE_EXTENSIONS, str):
            try:
                self.ALLOWED_IMAGE_EXTENSIONS = literal_eval(self.ALLOWED_IMAGE_EXTENSIONS)
            except:
                self.ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "webp"]
                
        # Construct DB URI if not provided directly
        if not self.SQLALCHEMY_DATABASE_URI:
            if self.POSTGRES_SERVER and self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
                self.SQLALCHEMY_DATABASE_URI = (
                    f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                    f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
                )
            else:
                # Default to SQLite if PostgreSQL settings are not complete
                self.SQLALCHEMY_DATABASE_URI = "sqlite:///./image_management.db"


settings = Settings()
