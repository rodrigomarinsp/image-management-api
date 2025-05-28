#!/bin/bash

# setup.sh - Configuration script for Image Management API
# Docker-specific version

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
    apt-get update -y || {
        warning "Failed apt-get update. Trying to configure for $ARCH architecture..."
        # Configure repositories for specific architecture
        dpkg --add-architecture $ARCH
        apt-get update -y || warning "Failed to update repositories. Continuing anyway..."
    }
    
    # Try to install Python and pip adapted to architecture
    apt-get install -y python3 python3-pip python3-venv || {
        warning "Failed standard installation. Trying alternative method..."
        
        # Alternative method: use apt-get install with --no-install-recommends to minimize issues
        apt-get install -y --no-install-recommends python3-minimal python3-pip || {
            error "Could not install Python. Checking if it's already installed..."
            
            # Check if Python is already available under another name
            if command -v python >/dev/null 2>&1; then
                log "Python is already installed as 'python'"
                ln -sf $(which python) /usr/bin/python3 || warning "Could not create symbolic link"
            else
                error "Python is not available. Setup may fail."
            fi
        }
    }
elif [[ "$OS" == *"Alpine"* ]]; then
    apk update
    apk add python3 py3-pip
else
    warning "Unrecognized operating system: $OS. Trying to install Python via generic method..."
    
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y python3 python3-pip
    elif command -v apk >/dev/null 2>&1; then
        apk update
        apk add python3 py3-pip
    elif command -v yum >/dev/null 2>&1; then
        yum -y update
        yum -y install python3 python3-pip
    else
        error "Could not determine package manager. Manual installation required."
    fi
fi

# Verify if Python was installed correctly
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
    log "Using 'python' instead of 'python3'"
else
    error "Python is not available after installation attempt. Creating fallback script..."
    PYTHON_CMD="python3"
    
    # Create a fallback script
    echo '#!/bin/sh
echo "Python is not available. Please install Python 3.8+ manually."
exit 1' > /usr/local/bin/python3_fallback
    chmod +x /usr/local/bin/python3_fallback
    PYTHON_CMD="/usr/local/bin/python3_fallback"
fi

# Verify if pip was installed correctly
if command -v pip3 >/dev/null 2>&1; then
    PIP_CMD="pip3"
elif command -v pip >/dev/null 2>&1; then
    PIP_CMD="pip"
    log "Using 'pip' instead of 'pip3'"
else
    # Try to install pip using get-pip.py
    log "pip not found. Trying to install it using get-pip.py..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    $PYTHON_CMD get-pip.py || {
        error "Failed to install pip. Creating fallback script..."
        
        # Create a fallback script for pip
        echo '#!/bin/sh
echo "pip is not available. Please install pip manually."
exit 1' > /usr/local/bin/pip_fallback
        chmod +x /usr/local/bin/pip_fallback
        PIP_CMD="/usr/local/bin/pip_fallback"
    }
    rm -f get-pip.py
fi

# Check Python version
if command -v $PYTHON_CMD >/dev/null 2>&1; then
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null)
    log "Using Python $PYTHON_VERSION"
else
    warning "Could not determine Python version."
    PYTHON_VERSION="unknown"
fi

# Create directory for local storage
log "Setting up local storage directory..."
mkdir -p storage/teams

# Install dependencies
log "Installing dependencies..."
if [ -f "requirements.txt" ]; then
    $PIP_CMD install -r requirements.txt || warning "Failed to install dependencies from requirements.txt."
else
    warning "requirements.txt file not found. Creating basic file..."
    
    # Create a basic requirements.txt
    cat > requirements.txt << EOF
fastapi>=0.68.0,<0.69.0
uvicorn>=0.15.0,<0.16.0
sqlalchemy>=1.4.0,<1.5.0
psycopg2-binary>=2.9.1,<2.10.0
python-multipart>=0.0.5,<0.0.6
pydantic>=1.8.0,<1.9.0
pydantic-settings>=2.0.0,<3.0.0
loguru>=0.6.0,<0.7.0
python-jose[cryptography]>=3.3.0,<3.4.0
passlib[bcrypt]>=1.7.4,<1.8.0
pillow>=9.0.0,<10.0.0
EOF
    
    log "Attempting to install basic dependencies..."
    $PIP_CMD install -r requirements.txt || {
        warning "Failed to install all dependencies. Trying minimal installation..."
        $PIP_CMD install fastapi uvicorn sqlalchemy || error "Failed minimal installation."
    }
fi

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
SECRET_KEY=$(openssl rand -hex 32)
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

# Check if main.py file exists
if [ ! -f "app/main.py" ]; then
    warning "app/main.py not found. Creating basic file..."
    cat > app/main.py << EOF
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings

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

# Include routers here when ready
# example: app.include_router(api_router)
EOF
    warning "Basic main.py file created. You'll need to implement it completely."
fi

# Optional: create a basic script for database.py if it doesn't exist
if [ ! -f "app/db/session.py" ]; then
    warning "app/db/session.py not found. Creating basic file..."
    cat > app/db/session.py << EOF
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
log "  $ python run.py"
echo 
log "The API will be available on the port defined in your Dockerfile/docker-compose"
echo 

exit 0
