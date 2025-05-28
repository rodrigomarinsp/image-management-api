# app/db/session.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from app.core.config import settings

# Default to SQLite if no database URI is provided
database_uri = settings.SQLALCHEMY_DATABASE_URI or "sqlite:///./image_management.db"

engine = create_engine(
    database_uri,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if database_uri.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
