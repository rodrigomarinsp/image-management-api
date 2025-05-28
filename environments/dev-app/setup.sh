#!/bin/bash

# setup.sh - Complete setup script for Image Management API in Docker
# This script handles environment setup, dependencies, and fixes common issues

# Define colors for messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions for displaying timestamped messages
log() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${GREEN}[$timestamp]${NC} $1"
}

error() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${RED}[$timestamp ERROR]${NC} $1" >&2
}

warning() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${YELLOW}[$timestamp WARN]${NC} $1"
}

log "Starting complete setup for Docker environment..."

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    log "Detected operating system: $OS $VER"
else
    warning "Could not detect operating system, assuming Debian/Ubuntu based"
    OS="Unknown"
fi

# Detect architecture
ARCH=$(uname -m)
log "Detected architecture: $ARCH"

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

# Create __init__.py files in directories if they don't exist
for dir in app app/api app/api/endpoints app/core app/db app/models app/schemas app/services app/middleware; do
    if [ ! -f "$dir/__init__.py" ]; then
        touch "$dir/__init__.py"
    fi
done

# Install essential system packages
log "Installing essential system packages..."
if command -v apt-get &> /dev/null; then
    apt-get update -y || warning "apt-get update failed, continuing anyway"
    apt-get install -y python3 python3-venv python3-pip curl || {
        warning "Failed to install all packages at once. Trying one by one..."
        apt-get install -y python3 || warning "Failed to install python3"
        apt-get install -y python3-venv || warning "Failed to install python3-venv"
        apt-get install -y python3-pip || warning "Failed to install python3-pip"
        apt-get install -y curl || warning "Failed to install curl"
    }
elif command -v apk &> /dev/null; then
    apk update
    apk add python3 py3-pip py3-virtualenv curl
else
    warning "Unsupported package manager. Please install Python 3, pip, virtualenv, and curl manually."
fi

# Verify Python installation
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    log "Python installed: $(python3 --version)"
else
    error "Python 3 is not installed or not in PATH. Setup cannot continue."
    exit 1
fi

# Set up virtual environment with direct path references to avoid issues
VENV_DIR="$PROJECT_DIR/.venv"
log "Setting up virtual environment at $VENV_DIR..."

# Remove existing virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    log "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new virtual environment
$PYTHON_CMD -m venv $VENV_DIR || {
    error "Failed to create virtual environment. Trying with alternative method..."
    pip3 install virtualenv
    virtualenv $VENV_DIR || {
        error "Could not create virtual environment. Setup cannot continue."
        exit 1
    }
}

# Define paths for virtual environment binaries
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# Activate virtual environment
log "Activating virtual environment..."
source "$VENV_DIR/bin/activate" || {
    error "Failed to activate virtual environment."
    exit 1
}

# Verify virtual environment is active
if [ "$VIRTUAL_ENV" != "$VENV_DIR" ]; then
    warning "Virtual environment activation check failed. Proceeding anyway."
fi

# Upgrade base packages in the virtual environment
log "Upgrading pip, wheel, and setuptools..."
$VENV_PIP install --upgrade pip wheel setuptools || warning "Failed to upgrade base packages."

# Install packages individually to ensure they're installed correctly
log "Installing dependencies one by one..."
PACKAGES=(
    "fastapi==0.103.1"
    "uvicorn==0.23.2"
    "sqlalchemy==2.0.20"
    "psycopg2-binary==2.9.7"
    "python-multipart==0.0.6"
    "pydantic==2.0.3"  # Specific version compatible with pydantic-settings
    "python-dotenv==1.0.0"
    "loguru==0.7.0"
    "python-jose[cryptography]==3.3.0"
    "passlib[bcrypt]==1.7.4"
    "pillow==10.0.0"
)

# Install each package with clear output and error handling
for package in "${PACKAGES[@]}"; do
    log "Installing $package..."
    $VENV_PIP install --no-cache-dir $package || {
        error "Failed to install $package. Continuing with other packages."
    }
done

# Special handling for pydantic-settings which has been problematic
log "Installing pydantic-settings with special handling..."
$VENV_PIP uninstall -y pydantic-settings &> /dev/null  # Remove if exists
$VENV_PIP install --no-cache-dir pydantic-settings==2.0.3

# Verify pydantic-settings installation with detailed error handling
log "Verifying pydantic-settings installation..."
if $VENV_PYTHON -c "import pydantic_settings; print('pydantic_settings version:', pydantic_settings.__version__)" &> /dev/null; then
    log "pydantic-settings verification successful!"
else
    warning "pydantic-settings verification failed. Attempting alternative fix..."
    
    # Try reinstalling pydantic first, then pydantic-settings
    $VENV_PIP uninstall -y pydantic &> /dev/null
    $VENV_PIP uninstall -y pydantic-settings &> /dev/null
    $VENV_PIP install --no-cache-dir pydantic==2.0.3
    $VENV_PIP install --no-cache-dir pydantic-settings==2.0.3
    
    # Add project directory to Python path as a last resort
    SITE_PACKAGES=$($VENV_PYTHON -c "import site; print(site.getsitepackages()[0])")
    echo "$PROJECT_DIR" > "$SITE_PACKAGES/project.pth"
    log "Added project directory to Python path."
    
    # Create alternative config.py that doesn't use pydantic-settings
    log "Creating alternative config.py that doesn't require pydantic-settings..."
    
    cat > "app/core/config.py" << EOF
# app/core/config.py - Alternative implementation without pydantic-settings
import os
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "Image Management API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    
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
    log "Alternative config.py created."
fi

# Create or update core files

# 1. Create config.py if it doesn't exist yet
if [ ! -f "app/core/config.py" ]; then
    log "Creating app/core/config.py..."
    
    cat > "app/core/config.py" << EOF
# app/core/config.py
import os
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    from pydantic import BaseModel as BaseSettings
    from dotenv import load_dotenv
    load_dotenv()
    print("Warning: Using pydantic.BaseModel instead of pydantic_settings.BaseSettings")

class Settings(BaseSettings):
    PROJECT_NAME: str = "Image Management API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    
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
fi

# 2. Create main.py if it doesn't exist yet
if [ ! -f "app/main.py" ]; then
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
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
fi

# 3. Create a basic db session handler if it doesn't exist
if [ ! -f "app/db/session.py" ]; then
    log "Creating app/db/session.py..."
    
    cat > "app/db/session.py" << EOF
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF
fi

# 4. Create an init_db script if it doesn't exist
if [ ! -f "app/db/init_db.py" ]; then
    log "Creating app/db/init_db.py..."
    
    cat > "app/db/init_db.py" << EOF
# app/db/init_db.py
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def init_db(db: Session) -> None:
    """Initialize the database with default data."""
    logger.info("Database initialization not implemented yet.")
    # You can add code here to create initial data
    pass
EOF
fi

# 5. Create a run.py script if it doesn't exist
if [ ! -f "run.py" ]; then
    log "Creating run.py..."
    
    cat > "run.py" << EOF
# run.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
EOF
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log "Creating .env file..."
    
    # Generate a random secret key
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "replace_with_secure_random_key")
    
    cat > ".env" << EOF
# Database Configuration
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=image_management
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@db/image_management # pragma: allowlist secret

# API Settings
SECRET_KEY=$SECRET_KEY
API_KEY_PREFIX=imapi
API_KEY_LENGTH=32
ENVIRONMENT=development
LOG_LEVEL=INFO
ENABLE_VECTOR_SEARCH=false

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:8000", "http://localhost:3000"]
EOF
    
    warning "Default .env file created for Docker. Edit as needed for your environment."
fi

# Create run script with proper environment activation
log "Creating executable run script..."

cat > "run_app.sh" << EOF
#!/bin/bash
# Script to run the Image Management API with properly activated environment

# Path to virtual environment
VENV_DIR="$VENV_DIR"

# Activate virtual environment
source "\$VENV_DIR/bin/activate"

# Ensure PYTHONPATH includes project directory
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"

echo "Starting Image Management API..."
echo "Python version: \$(python --version)"
echo "Modules available:"
python -c "import sys; print('\\n'.join(sorted(sys.modules.keys())))" | grep pydantic

# Run the application
python run.py
EOF

chmod +x run_app.sh

# Add executable permissions to the scripts
chmod +x run.py

# Create requirements.txt for reference
log "Creating or updating requirements.txt..."
cat > "requirements.txt" << EOF
# Core dependencies
fastapi==0.103.1
uvicorn==0.23.2
sqlalchemy==2.0.20
psycopg2-binary==2.9.7
python-multipart==0.0.6
pydantic==2.0.3
pydantic-settings==2.0.3
python-dotenv==1.0.0
loguru==0.7.0

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Image processing
pillow==10.0.0
EOF

# Verify the environment
log "Verifying environment setup..."
source "$VENV_DIR/bin/activate"

# Check Python
PYTHON_VERSION=$($VENV_PYTHON --version 2>&1)
log "Python version: $PYTHON_VERSION"

# List installed packages
log "Installed packages:"
$VENV_PIP list | grep -E 'pydantic|fastapi|uvicorn'

# Check if we can import important modules
log "Testing imports..."
IMPORT_TEST=$($VENV_PYTHON -c "
try:
    import fastapi
    print('✓ fastapi')
except ImportError as e:
    print('✗ fastapi:', e)

try:
    import pydantic
    print('✓ pydantic')
except ImportError as e:
    print('✗ pydantic:', e)

try:
    import pydantic_settings
    print('✓ pydantic_settings')
except ImportError as e:
    print('✗ pydantic_settings:', e)

try:
    from dotenv import load_dotenv
    print('✓ python-dotenv')
except ImportError as e:
    print('✗ python-dotenv:', e)
")

echo "$IMPORT_TEST"

# Final instructions
echo 
log "Setup completed successfully!"
echo 
log "To start the application:"
log "  $ ./run_app.sh"
echo 
log "The API will be available at: http://localhost:8000"
log "Swagger documentation will be at: http://localhost:8000/docs"
echo 

# Deactivate virtual environment
deactivate

exit 0
