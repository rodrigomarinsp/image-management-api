# app/models/image.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False, unique=True)
    media_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Optional metadata for search and organization
    # Use JSON type for both tags and metadata for SQLite compatibility
    tags = Column(JSON, nullable=True)
    image_metadata = Column(JSON, nullable=True)  # Changed from 'metadata' to 'image_metadata'
    
    # For bonus challenge - vector embedding
    embedding_id = Column(String, nullable=True, index=True)
    embedding_model = Column(String, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="images")
    user = relationship("User")
