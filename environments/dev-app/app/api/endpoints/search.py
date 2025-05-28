# app/api/endpoints/search.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import time
import json

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.image import Image
from app.schemas.image import ImageResponse, ImageSearchResult
from app.services.storage import storage_service
from app.services.vector_search import vector_search_service
from app.core.config import settings
from app.core.logging import logger

class SearchQuery(BaseModel):
    """Model for semantic search queries"""
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)

class SearchStats(BaseModel):
    """Model for search statistics"""
    query: str
    result_count: int
    processing_time_ms: float

router = APIRouter()

@router.post("/semantic", response_model=List[ImageSearchResult])
async def semantic_search(
    query: SearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search images using semantic similarity (vector search)
    
    This endpoint allows searching images using natural language queries.
    Results are ranked by semantic similarity to the query text.
    """
    if not settings.ENABLE_VECTOR_SEARCH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Semantic search is not enabled on this server"
        )
        
    start_time = time.time()
    
    try:
        # Get search results
        search_results = await vector_search_service.search_by_text(
            query.query,
            current_user.team_id,
            query.limit,
            query.min_score
        )
        
        if not search_results:
            # Log empty results for monitoring
            logger.info(
                f"Semantic search returned no results",
                extra={
                    "user_id": current_user.id,
                    "team_id": current_user.team_id,
                    "query": query.query,
                    "processing_time_ms": (time.time() - start_time) * 1000
                }
            )
            return []
            
        # Get image IDs from search results
        image_ids = [int(result["image_id"]) for result in search_results]
        
        # Query the database for these images
        images = db.query(Image).filter(Image.id.in_(image_ids)).all()
        
        # Create a lookup dictionary
        image_dict = {str(image.id): image for image in images}
        
        # Create response with signed URLs
        results = []
        for result in search_results:
            image_id = result["image_id"]
            if image_id in image_dict:
                image = image_dict[image_id]
                url = storage_service.generate_signed_url(image.storage_path)
                
                # Convert SQLAlchemy model to dict
                image_data = {
                    "id": image.id,
                    "original_filename": image.original_filename,
                    "filename": image.filename,
                    "storage_path": image.storage_path,
                    "media_type": image.media_type,
                    "size_bytes": image.size_bytes,
                    "width": image.width,
                    "height": image.height,
                    "team_id": image.team_id,
                    "user_id": image.user_id,
                    "created_at": image.created_at,
                    "updated_at": image.updated_at,
                    "tags": image.tags,
                    "image_metadata": image.image_metadata,
                    "embedding_id": image.embedding_id,
                    "embedding_model": image.embedding_model,
                    "url": url
                }
                
                image_response = ImageResponse(**image_data)
                results.append(
                    ImageSearchResult(
                        image=image_response,
                        score=result["score"]
                    )
                )
        
        # Log successful search for analytics
        processing_time = (time.time() - start_time) * 1000
        logger.info(
            f"Semantic search completed",
            extra={
                "user_id": current_user.id,
                "team_id": current_user.team_id,
                "query": query.query,
                "results_count": len(results),
                "processing_time_ms": processing_time
            }
        )
        
        return results
        
    except Exception as e:
        logger.error(
            f"Error in semantic search: {str(e)}",
            extra={
                "user_id": current_user.id,
                "team_id": current_user.team_id,
                "query": query.query
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during search: {str(e)}"
        )

@router.post("/image-similarity", response_model=List[ImageSearchResult])
async def image_similarity_search(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search for similar images by uploading a reference image
    
    This endpoint allows finding images similar to the uploaded reference image.
    Results are ranked by visual similarity.
    """
    if not settings.ENABLE_VECTOR_SEARCH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vector search is not enabled on this server"
        )
    
    try:
        # Search by image
        search_results = await vector_search_service.search_by_image(
            file, 
            current_user.team_id,
            limit
        )
        
        if not search_results:
            return []
            
        # Get image IDs from search results
        image_ids = [int(result["image_id"]) for result in search_results]
        
        # Query the database for these images
        images = db.query(Image).filter(Image.id.in_(image_ids)).all()
        
        # Create a lookup dictionary
        image_dict = {str(image.id): image for image in images}
        
        # Create response with signed URLs
        results = []
        for result in search_results:
            image_id = result["image_id"]
            if image_id in image_dict:
                image = image_dict[image_id]
                url = storage_service.generate_signed_url(image.storage_path)
                
                # Convert SQLAlchemy model to dict
                image_data = {
                    "id": image.id,
                    "original_filename": image.original_filename,
                    "filename": image.filename,
                    "storage_path": image.storage_path,
                    "media_type": image.media_type,
                    "size_bytes": image.size_bytes,
                    "width": image.width,
                    "height": image.height,
                    "team_id": image.team_id,
                    "user_id": image.user_id,
                    "created_at": image.created_at,
                    "updated_at": image.updated_at,
                    "tags": image.tags,
                    "image_metadata": image.image_metadata,
                    "embedding_id": image.embedding_id,
                    "embedding_model": image.embedding_model,
                    "url": url
                }
                
                image_response = ImageResponse(**image_data)
                results.append(
                    ImageSearchResult(
                        image=image_response,
                        score=result["score"]
                    )
                )
        
        # Delete temporary uploaded file in background
        background_tasks.add_task(file.file.close)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in image similarity search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during image search: {str(e)}"
        )

@router.get("/similar/{image_id}", response_model=List[ImageSearchResult])
async def find_similar_images(
    image_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Find images similar to a given image by ID
    
    This endpoint finds and returns images that are visually similar
    to the specified image, ranked by similarity score.
    """
    if not settings.ENABLE_VECTOR_SEARCH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vector search is not enabled on this server"
        )
    
    # Verify user has access to the reference image
    reference_image = db.query(Image).filter(Image.id == image_id).first()
    if not reference_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found"
        )
        
    if reference_image.team_id != current_user.team_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this image"
        )
    
    try:
        # Find similar images
        search_results = await vector_search_service.get_similar_images(
            str(image_id),
            current_user.team_id,
            limit
        )
        
        if not search_results:
            return []
        
        # Get image IDs from search results
        image_ids = [int(result["image_id"]) for result in search_results]
        
        # Query the database for these images
        images = db.query(Image).filter(Image.id.in_(image_ids)).all()
        
        # Create a lookup dictionary
        image_dict = {str(image.id): image for image in images}
        
        # Create response with signed URLs
        results = []
        for result in search_results:
            image_id = result["image_id"]
            if image_id in image_dict:
                image = image_dict[image_id]
                url = storage_service.generate_signed_url(image.storage_path)
                
                # Convert SQLAlchemy model to dict
                image_data = {
                    "id": image.id,
                    "original_filename": image.original_filename,
                    "filename": image.filename,
                    "storage_path": image.storage_path,
                    "media_type": image.media_type,
                    "size_bytes": image.size_bytes,
                    "width": image.width,
                    "height": image.height,
                    "team_id": image.team_id,
                    "user_id": image.user_id,
                    "created_at": image.created_at,
                    "updated_at": image.updated_at,
                    "tags": image.tags,
                    "image_metadata": image.image_metadata,
                    "embedding_id": image.embedding_id,
                    "embedding_model": image.embedding_model,
                    "url": url
                }
                
                image_response = ImageResponse(**image_data)
                results.append(
                    ImageSearchResult(
                        image=image_response,
                        score=result["score"]
                    )
                )
        
        return results
        
    except Exception as e:
        logger.error(f"Error finding similar images: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while finding similar images: {str(e)}"
        )

@router.get("/by-tag", response_model=List[ImageResponse])
async def search_by_tags(
    tags: List[str] = Query(...),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search images by tags
    
    This endpoint returns images that match all specified tags.
    """
    query = db.query(Image).filter(Image.team_id == current_user.team_id)
    
    # Add tag filters
    for tag in tags:
        query = query.filter(Image.tags.contains([tag]))
    
    # Execute query with pagination
    images = query.offset(skip).limit(limit).all()
    
    # Generate signed URLs for each image
    result = []
    for image in images:
        url = storage_service.generate_signed_url(image.storage_path)
        
        # Convert SQLAlchemy model to dict
        image_data = {
            "id": image.id,
            "original_filename": image.original_filename,
            "filename": image.filename,
            "storage_path": image.storage_path,
            "media_type": image.media_type,
            "size_bytes": image.size_bytes,
            "width": image.width,
            "height": image.height,
            "team_id": image.team_id,
            "user_id": image.user_id,
            "created_at": image.created_at,
            "updated_at": image.updated_at,
            "tags": image.tags,
            "image_metadata": image.image_metadata,
            "embedding_id": image.embedding_id,
            "embedding_model": image.embedding_model,
            "url": url
        }
        
        result.append(ImageResponse(**image_data))
    
    return result

@router.post("/analytics", response_model=Dict[str, Any])
async def search_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics about search usage (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access search analytics"
        )
        
    # In a real implementation, this would query analytics data
    # Here we'll return sample data for demonstration
    return {
        "total_searches": 150,
        "average_results": 7.8,
        "average_processing_time_ms": 320.5,
        "top_queries": [
            {"query": "mountain landscape", "count": 12},
            {"query": "product photo", "count": 10},
            {"query": "blue sky", "count": 8},
            {"query": "city nightscape", "count": 7},
            {"query": "portrait", "count": 6}
        ],
        "search_volume_by_day": [
            {"date": "2025-05-21", "count": 23},
            {"date": "2025-05-22", "count": 31},
            {"date": "2025-05-23", "count": 28},
            {"date": "2025-05-24", "count": 18},
            {"date": "2025-05-25", "count": 15},
            {"date": "2025-05-26", "count": 25},
            {"date": "2025-05-27", "count": 30}
        ]
    }

# Add integration with image uploads to automatically process embeddings
@router.post("/process-image-embedding/{image_id}", status_code=status.HTTP_200_OK)
async def process_image_embedding(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process an existing image to generate and store its embedding
    
    This endpoint is useful for batch processing existing images
    or manually triggering embedding generation for specific images.
    """
    if not settings.ENABLE_VECTOR_SEARCH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vector search is not enabled on this server"
        )
    
    # Get image
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Check authorization
    if image.team_id != current_user.team_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to process this image"
        )
    
    # Get full image path
    if settings.GCS_BUCKET_NAME and storage_service.use_gcs:
        # For Google Cloud Storage, we need to download the image temporarily
        try:
            temp_file = await storage_service.download_file_temporarily(image.storage_path)
            result = await vector_search_service.process_image_upload(
                temp_file,
                image.id,
                image.team_id,
                image.image_metadata or {}
            )
            # Remove temporary file
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            logger.error(f"Error downloading image for embedding: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing image embedding: {str(e)}"
            )
    else:
        # For local storage
        image_path = os.path.join(storage_service.storage_dir, image.storage_path)
        result = await vector_search_service.process_image_upload(
            image_path,
            image.id,
            image.team_id,
            image.image_metadata or {}
        )
    
    # Update image with embedding info
    if result["success"]:
        image.embedding_id = result.get("embedding_id")
        image.embedding_model = result.get("embedding_model")
        db.commit()
        
        return {
            "success": True,
            "message": "Image embedding processed successfully",
            "embedding_id": image.embedding_id,
            "embedding_model": image.embedding_model
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image embedding: {result.get('reason', 'Unknown error')}"
        )

# Extend the storage service to support downloading files temporarily
# Add this method to storage.py
async def download_file_temporarily(self, storage_path: str) -> str:
    """Download a file from storage to a temporary location and return the path"""
    import tempfile
    import os
    
    if not self.use_gcs:
        # For local storage, just return the full path
        return os.path.join(self.storage_dir, storage_path)
    
    try:
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(storage_path)[1])
        os.close(fd)
        
        # Download from GCS
        blob = self.bucket.blob(storage_path)
        blob.download_to_filename(temp_path)
        
        return temp_path
    except Exception as e:
        logger.error(f"Error downloading file temporarily: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file temporarily: {str(e)}"
        )