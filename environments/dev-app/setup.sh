#!/bin/bash
# setup.sh

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    echo "Virtual environment created and dependencies installed."
else
    echo "Virtual environment already exists."
    source .venv/bin/activate
fi

# Set up database
echo "Setting up database..."
python -c "from app.db.session import Base, engine; from app.models.base import *; Base.metadata.create_all(engine)"

# Initialize data
echo "Initializing seed data..."
python -c "from app.db.init_db import init_db; from app.db.session import SessionLocal; db = SessionLocal(); init_db(db); db.close()"

echo "Setup complete! You can now run the application with 'python run.py'"
