# scripts/seed_data.py
import sys
import os
import requests
import argparse
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.core.logging import logger


def seed_database():
    """Seed the database with initial data"""
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Seed database for Image Management API')
    parser.add_argument('--service-url', type=str, help='URL of the API service for testing')
    
    args = parser.parse_args()
    
    # Seed database
    logger.info("Seeding database...")
    seed_database()
    logger.info("Database seeded successfully.")
    
    # Test API if service URL provided
    if args.service_url:
        base_url = args.service_url.rstrip('/')
        
        # Try accessing the health check endpoint
        try:
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                logger.info(f"API health check successful: {response.json()}")
            else:
                logger.error(f"API health check failed: {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Error accessing API: {str(e)}")


if __name__ == "__main__":
    main()
