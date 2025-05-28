#!/bin/bash

# setup.sh - Configuration script for Image Management API
# Docker-specific version with virtual environment support

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
    apt-get install -y python3 python3-venv python3-full || {
        error "Failed to install Python and virtual environment support. Trying minimal install..."
        apt-get install -y --no-install-recommends python3-minimal python3-venv || {
            error "Could not install Python requirements. Setup may fail."
        }
    }
elif [[ "$OS" == *"Alpine"* ]]; then
    apk update
    apk add python3 py3-pip py3-virtualenv
else
    warning "Unrecognized operating system: $OS. Trying to install Python via generic method..."
    
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y python3 python3-venv
    elif command -v apk >/dev/null 2>&1; then
        apk update
        apk add python3 py3-virtualenv
    elif command -v yum >/dev/null 2>&1; then
        yum -y update
        yum -y install python3 python3-virtualenv
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

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv $VENV_DIR || {
        error "Failed to create virtual environment. Make sure python3-venv is installed."
        exit 1
    }
else
    log "Virtual environment already exists at $VENV_DIR"
fi

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
fi

# Upgrade pip in the virtual environment
$PIP_CMD install --upgrade pip

# Install dependencies
log "Installing dependencies in virtual environment..."
if [ -f "requirements.txt" ]; then
    $PIP_CMD install -r requirements.txt || {
        warning "Failed to install dependencies from requirements.txt."
        warning "Installing core dependencies..."
        $PIP_CMD install fastapi uvicorn sqlalchemy psycopg2-binary
    }
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
    
    log "Installing new dependencies..."
    $PIP_CMD install -r requirements.txt || {
        warning "Failed to install all dependencies. Trying minimal installation..."
        $PIP_CMD install fastapi uvicorn sqlalchemy
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
python run.py
EOF
chmod +x run_app.sh

# Create a basic init_db script if it doesn't exist
if [ ! -f "app/db/init_db.py" ]; then
    warning "app/db/init_db.py not found. Creating a basic one..."
    cat > app/db/init_db.py << EOF
# app/db/init_db.py
from sqlalchemy.orm import Session

def init_db(db: Session) -> None:
    """Initialize the database with default data."""
    # You can add code here to create initial data
    # Example:
    # from app.models.team import Team
    # team = db.query(Team).filter(Team.name == "Default").first()
    # if not team:
    #     team = Team(name="Default", description="Default team")
    #     db.add(team)
    #     db.commit()
    
    print("Database initialized!")
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
