# app/api/endpoints/test.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()

@router.get("/")
def test_endpoint(db: Session = Depends(get_db)):
    """
    Test endpoint to verify API and database connection
    """
    return {
        "status": "ok",
        "message": "Test endpoint working",
        "database_connected": db is not None
    }
