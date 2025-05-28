#!/bin/bash

# setup.sh - Simplified setup script for Image Management API in Docker

# Define colors for messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Simple logging functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log "Starting setup for Docker environment..."

# Define project directory
PROJECT_DIR=$(pwd)
log "Project directory: $PROJECT_DIR"

# Create necessary directories
log "Creating directory structure..."
mkdir -p app/api/endpoints
mkdir -p app/core
mkdir -p app/db
mkdir -p app/models
mkdir -p app/schemas
mkdir -p app/services
mkdir -p app/middleware
mkdir -p storage/teams
mkdir -p uploads
mkdir -p temp

# Create __init__.py files in directories
touch app/__init__.py
touch app/api/__init__.py
touch app/api/endpoints/__init__.py
touch app/core/__init__.py
touch app/db/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/middleware/__init__.py

# Install system packages
log "Installing essential system packages..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip curl

# Set up virtual environment
log "Setting up virtual environment..."
VENV_DIR="$PROJECT_DIR/.venv"

# Remove existing virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    log "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment
python3 -m venv $VENV_DIR
if [ $? -ne 0 ]; then
    error "Failed to create virtual environment."
    exit 1
fi

# Define paths
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    error "Failed to activate virtual environment."
    exit 1
fi

# Upgrade pip
log "Upgrading pip..."
$VENV_PIP install --upgrade pip wheel setuptools

# Install core dependencies
log "Installing dependencies..."
$VENV_PIP install fastapi==0.103.1
$VENV_PIP install uvicorn==0.23.2
$VENV_PIP install sqlalchemy==2.0.20
$VENV_PIP install psycopg2-binary==2.9.7
$VENV_PIP install python-multipart==0.0.6
$VENV_PIP install pydantic==2.0.3
$VENV_PIP install python-dotenv==1.0.0
$VENV_PIP install loguru==0.7.0

# Special handling for pydantic-settings
log "Installing pydantic-settings with special handling..."
$VENV_PIP uninstall -y pydantic-settings
$VENV_PIP install pydantic-settings==2.0.3

# Create config.py with fallback
log "Creating app/core/config.py..."
cat > "app/core/config.py" << EOF
# app/core/config.py
import os
from typing import List

# Try to use pydantic_settings or fallback to pydantic
try:
    from pydantic_settings import BaseSettings
    from dotenv import load_dotenv
    load_dotenv()
    print("Using pydantic_settings.BaseSettings")
except ImportError:
    # Fallback to regular pydantic
    from pydantic import BaseModel as BaseSettings
    from dotenv import load_dotenv
    load_dotenv()
    print("Fallback: Using pydantic.BaseModel instead of pydantic_settings.BaseSettings")

class Settings(BaseSettings):
    PROJECT_NAME: str = "Image Management API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key")
    
    # Database settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "image_management")
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI", 
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
    )
    
    # API key settings
    API_KEY_LENGTH: int = int(os.getenv("API_KEY_LENGTH", "32"))
    API_KEY_PREFIX: str = os.getenv("API_KEY_PREFIX", "imapi")
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        case_sensitive = True

# Create a settings instance
settings = Settings()
EOF

# Create main.py
log "Creating app/main.py..."
cat > "app/main.py" << EOF
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

try:
    from app.core.config import settings
    print("Successfully imported settings")
except ImportError as e:
    print(f"Error importing settings: {e}")
    raise

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Image Management API",
    description="API for image management with semantic search capabilities",
    version="0.1.0",
)

# Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
def root():
    return {"message": "Image Management API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
EOF

# Create run.py
log "Creating run.py..."
cat > "run.py" << EOF
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
EOF

# Create .env file
log "Creating .env file..."
cat > ".env" << EOF
# Database Configuration
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=image_management
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@db/image_management # pragma: allowlist secret

# API Settings
SECRET_KEY=supersecretkey
API_KEY_PREFIX=imapi
API_KEY_LENGTH=32
ENVIRONMENT=development
LOG_LEVEL=INFO
ENABLE_VECTOR_SEARCH=false

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:8000", "http://localhost:3000"]
EOF

# Create run script
log "Creating run_app.sh..."
cat > "run_app.sh" << EOF
#!/bin/bash
# Script to run the Image Management API

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set Python path
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"

echo "Starting Image Management API..."
python run.py
EOF
chmod +x run_app.sh

# Create requirements.txt
log "Creating requirements.txt..."
cat > "requirements.txt" << EOF
fastapi==0.103.1
uvicorn==0.23.2
sqlalchemy==2.0.20
psycopg2-binary==2.9.7
python-multipart==0.0.6
pydantic==2.0.3
pydantic-settings==2.0.3
python-dotenv==1.0.0
loguru==0.7.0
EOF

# Verify the environment
log "Verifying environment..."
$VENV_PYTHON -c "import sys; print('Python version:', sys.version)"

# Final message
echo ""
log "Setup completed!"
echo ""
log "To run the application:"
log "  $ ./run_app.sh"
echo ""
log "The API will be available at: http://localhost:8000"
echo ""

# Deactivate virtual environment
deactivate

exit 0
