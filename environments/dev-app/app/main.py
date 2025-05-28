# app/main.py
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response

# Root endpoint for basic testing
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Image Management API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Create tables and initialize database
try:
    from app.db.session import Base, engine, SessionLocal
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Initialize seed data
    from app.db.init_db import init_db
    db = SessionLocal()
    try:
        init_db(db)
        logger.info("Database initialized with seed data")
    except Exception as e:
        logger.error(f"Error initializing database with seed data: {str(e)}")
    finally:
        db.close()
except Exception as e:
    logger.error(f"Error setting up database: {str(e)}")

# Import API router after defining basic endpoints
try:
    from app.api.api import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    logger.info("API router included")
except Exception as e:
    logger.error(f"Error including API router: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting {settings.PROJECT_NAME} in development mode")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
