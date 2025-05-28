#!/bin/bash

# setup.sh - Configuration script for Image Management API
# Docker-specific version with enhanced dependency installation

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

log "Starting setup for Docker environment..."

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    log "Detected operating system: $OS $VER"
else
    error "Could not detect operating system"
    OS="Unknown"
fi

# Detect architecture
ARCH=$(uname -m)
log "Detected architecture: $ARCH"

# Install essential packages based on operating system
log "Installing essential packages..."

if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
    # Try to update repositories for the correct architecture
    apt-get update -y || warning "Failed to update repositories. Continuing anyway..."
    
    # Install Python and venv support
    apt-get install -y python3 python3-venv python3-full curl || {
        error "Failed to install Python and virtual environment support. Trying minimal install..."
        apt-get install -y --no-install-recommends python3-minimal python3-venv curl || {
            error "Could not install Python requirements. Setup may fail."
        }
    }
elif [[ "$OS" == *"Alpine"* ]]; then
    apk update
    apk add python3 py3-pip py3-virtualenv curl
else
    warning "Unrecognized operating system: $OS. Trying to install Python via generic method..."
    
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y python3 python3-venv curl
    elif command -v apk >/dev/null 2>&1; then
        apk update
        apk add python3 py3-virtualenv curl
    elif command -v yum >/dev/null 2>&1; then
        yum -y update
        yum -y install python3 python3-virtualenv curl
    else
        error "Could not determine package manager. Manual installation required."
    fi
fi

# Verify if Python was installed correctly
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    error "Python3 is not available. Installation failed."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
log "Using $PYTHON_VERSION"

# Create directory for local storage
log "Setting up local storage directory..."
mkdir -p storage/teams

# Create virtual environment
log "Creating virtual environment..."
APP_DIR="$(pwd)"
VENV_DIR="${APP_DIR}/.venv"

# Remove existing virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    log "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create fresh virtual environment
$PYTHON_CMD -m venv $VENV_DIR || {
    error "Failed to create virtual environment. Make sure python3-venv is installed."
    exit 1
}

# Activate virtual environment
log "Activating virtual environment..."
source $VENV_DIR/bin/activate || {
    error "Failed to activate virtual environment."
    exit 1
}

# Now pip should be available from the virtual environment
if command -v pip >/dev/null 2>&1; then
    PIP_CMD="pip"
else
    error "pip not available in virtual environment. Something is wrong with the venv setup."
    exit 1
}

# Upgrade pip in the virtual environment
log "Upgrading pip in virtual environment..."
$PIP_CMD install --upgrade pip wheel setuptools

# Create or update requirements.txt with specific versions
log "Setting up requirements.txt with correct dependencies..."
cat > requirements.txt << EOF
fastapi==0.103.1
uvicorn==0.23.2
sqlalchemy==2.0.20
psycopg2-binary==2.9.7
python-multipart==0.0.6
pydantic==2.3.0
pydantic-settings==2.0.3
loguru==0.7.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pillow==10.0.0
python-dotenv==1.0.0
EOF

# Install dependencies
log "Installing dependencies in virtual environment..."
$PIP_CMD install -r requirements.txt || {
    error "Failed to install dependencies from requirements.txt."
    
    # Try to install dependencies one by one
    log "Trying to install dependencies one by one..."
    $PIP_CMD install fastapi
    $PIP_CMD install uvicorn
    $PIP_CMD install sqlalchemy
    $PIP_CMD install psycopg2-binary
    $PIP_CMD install python-multipart
    $PIP_CMD install pydantic
    $PIP_CMD install pydantic-settings
    $PIP_CMD install loguru
    $PIP_CMD install python-jose[cryptography]
    $PIP_CMD install passlib[bcrypt]
    $PIP_CMD install pillow
    $PIP_CMD install python-dotenv
}

# Verify critical dependencies
log "Verifying critical dependencies..."
$PYTHON_CMD -c "import fastapi, uvicorn, pydantic_settings" || {
    error "Critical dependencies are missing. Trying one more installation method..."
    $PIP_CMD install --no-cache-dir pydantic-settings
    $PYTHON_CMD -c "import pydantic_settings" || error "Failed to install pydantic-settings."
}

# Check environment variables
log "Checking environment configuration..."
if [ ! -f ".env" ]; then
    log "Creating default .env file..."
    cat > .env << EOF
# Database Configuration
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=image_management
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@db/image_management # pragma: allowlist secret

# API Settings
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "replace_with_secure_random_key")
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

# Create temporary storage directory
log "Creating temporary storage directory..."
mkdir -p uploads temp

# Check if app can be started
log "Verifying application configuration..."
if [ -f "run.py" ]; then
    log "run.py file found."
else
    # Create run.py if it doesn't exist
    log "Creating basic run.py file..."
    cat > run.py << EOF
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
EOF
fi

# Check if config.py exists, if not create a basic one
if [ ! -f "app/core/config.py" ]; then
    log "Creating app/core/config.py..."
    mkdir -p app/core
    cat > app/core/config.py << EOF
import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

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

settings = Settings()
EOF
fi

# Check basic directory structure
if [ ! -d "app" ]; then
    log "Creating basic directory structure..."
    mkdir -p app/api/endpoints
    mkdir -p app/core
    mkdir -p app/db
    mkdir -p app/models
    mkdir -p app/schemas
    mkdir -p app/services
    mkdir -p app/middleware
    
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
fi

# Create a convenient wrapper script to run the application
log "Creating run wrapper script..."
cat > run_app.sh << EOF
#!/bin/bash
# Activate virtual environment and run the application
source $VENV_DIR/bin/activate
echo "Starting Image Management API..."
python run.py
EOF
chmod +x run_app.sh

# Check if main.py exists, if not create a basic one
if [ ! -f "app/main.py" ]; then
    warning "app/main.py not found. Creating basic file..."
    cat > app/main.py << EOF
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

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

# Final instructions
echo 
log "Docker environment setup completed!"
echo 
log "Important: If you're using this service in a Docker Compose setup, ensure that:"
log "  1. The database service is properly configured"
log "  2. Environment variables in .env match your configuration"
log "  3. The volume for persistent storage is configured"
echo 
log "To start the application inside the container:"
log "  $ ./run_app.sh  # This will activate the virtual environment and start the app"
log "  or"
log "  $ source .venv/bin/activate && python run.py"
echo 
log "The API will be available on the port defined in your Dockerfile/docker-compose"
echo 

# Deactivate virtual environment
deactivate

exit 0
