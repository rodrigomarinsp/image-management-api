# app/api/endpoints/images.py
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db.session import get_db
from app.middleware.auth import get_current_user, team_access_required
from app.models.user import User
from app.models.image import Image
from app.services.storage import storage_service
from app.schemas.image import Image as ImageSchema, ImageUpdate, ImageResponse, ImageCreate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    tags: str = Form(None),  # JSON string of tags
    metadata: str = Form(None),  # JSON string of metadata
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a new image.
    """
    try:
        # Parse tags and metadata if provided
        tags_list = json.loads(tags) if tags else None
        metadata_dict = json.loads(metadata) if metadata else None
        
        # Upload file to storage
        upload_result = await storage_service.upload_file(file, current_user.team_id, current_user.id)
        
        # Create image record in database
        image_data = {
            **upload_result,
            "team_id": current_user.team_id,
            "user_id": current_user.id,
            "tags": tags_list,
            "image_metadata": metadata_dict,  # Using image_metadata instead of metadata
        }
        
        image_in = ImageCreate(**image_data)
        image = Image(
            filename=image_in.filename,
            original_filename=image_in.original_filename,
            storage_path=image_in.storage_path,
            media_type=image_in.media_type,
            size_bytes=image_in.size_bytes,
            width=image_in.width,
            height=image_in.height,
            team_id=image_in.team_id,
            user_id=image_in.user_id,
            tags=image_in.tags,
            image_metadata=image_in.image_metadata,  # Using image_metadata instead of metadata
        )
        
        db.add(image)
        db.commit()
        db.refresh(image)
        
        # Generate a signed URL for the image
        url = storage_service.generate_signed_url(image.storage_path)
        
        # Return response with url
        return ImageResponse(
            id=image.id,
            original_filename=image.original_filename,
            filename=image.filename,
            storage_path=image.storage_path,
            media_type=image.media_type,
            size_bytes=image.size_bytes,
            width=image.width,
            height=image.height,
            team_id=image.team_id,
            user_id=image.user_id,
            created_at=image.created_at,
            updated_at=image.updated_at,
            tags=image.tags,
            image_metadata=image.image_metadata,  # Using image_metadata instead of metadata
            embedding_id=image.embedding_id,
            embedding_model=image.embedding_model,
            url=url
        )
        
    except ValueError as e:
        logger.error(f"Error uploading image: {str(e)}", extra={"user_id": current_user.id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading image: {str(e)}", extra={"user_id": current_user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while uploading the image"
        )


@router.get("/", response_model=List[ImageResponse])
async def get_images(
    skip: int = 0,
    limit: int = 100,
    tags: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all images that belong to the user's team
    """
    try:
        # Build the base query
        query = db.query(Image).filter(Image.team_id == current_user.team_id)
        
        # Filter by tags if provided
        if tags:
            for tag in tags:
                # For JSON storage, this filtering approach may need adjustment based on db backend
                query = query.filter(Image.tags.contains([tag]))
        
        # Fetch images with pagination
        images = query.order_by(Image.created_at.desc()).offset(skip).limit(limit).all()
        
        # Generate signed URLs for each image
        result = []
        for image in images:
            url = storage_service.generate_signed_url(image.storage_path)
            result.append(ImageResponse(
                id=image.id,
                original_filename=image.original_filename,
                filename=image.filename,
                storage_path=image.storage_path,
                media_type=image.media_type,
                size_bytes=image.size_bytes,
                width=image.width,
                height=image.height,
                team_id=image.team_id,
                user_id=image.user_id,
                created_at=image.created_at,
                updated_at=image.updated_at,
                tags=image.tags,
                image_metadata=image.image_metadata,  # Using image_metadata instead of metadata
                embedding_id=image.embedding_id,
                embedding_model=image.embedding_model,
                url=url
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving images: {str(e)}", extra={"user_id": current_user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving images"
        )


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific image by ID
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Check if user has access to this image
    if not team_access_required(image.team_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this image"
        )
    
    # Generate a signed URL for the image
    url = storage_service.generate_signed_url(image.storage_path)
    
    return ImageResponse(
        id=image.id,
        original_filename=image.original_filename,
        filename=image.filename,
        storage_path=image.storage_path,
        media_type=image.media_type,
        size_bytes=image.size_bytes,
        width=image.width,
        height=image.height,
        team_id=image.team_id,
        user_id=image.user_id,
        created_at=image.created_at,
        updated_at=image.updated_at,
        tags=image.tags,
        image_metadata=image.image_metadata,  # Using image_metadata instead of metadata
        embedding_id=image.embedding_id,
        embedding_model=image.embedding_model,
        url=url
    )


@router.put("/{image_id}", response_model=ImageResponse)
async def update_image(
    image_id: int,
    image_in: ImageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update image tags and metadata
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Check if user has access to this image
    if not team_access_required(image.team_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this image"
        )
    
    # Update fields
    update_data = image_in.dict(exclude_unset=True)
    
    # Handle rename of metadata to image_metadata
    if "image_metadata" in update_data:
        image.image_metadata = update_data["image_metadata"]
    
    if "tags" in update_data:
        image.tags = update_data["tags"]
    
    db.commit()
    db.refresh(image)
    
    # Generate a signed URL for the image
    url = storage_service.generate_signed_url(image.storage_path)
    
    return ImageResponse(
        id=image.id,
        original_filename=image.original_filename,
        filename=image.filename,
        storage_path=image.storage_path,
        media_type=image.media_type,
        size_bytes=image.size_bytes,
        width=image.width,
        height=image.height,
        team_id=image.team_id,
        user_id=image.user_id,
        created_at=image.created_at,
        updated_at=image.updated_at,
        tags=image.tags,
        image_metadata=image.image_metadata,  # Using image_metadata instead of metadata
        embedding_id=image.embedding_id,
        embedding_model=image.embedding_model,
        url=url
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an image
    """
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Check if user has access to this image
    if not team_access_required(image.team_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this image"
        )
    
    try:
        # Delete from storage
        deleted = storage_service.delete_file(image.storage_path)
        if not deleted:
            logger.warning(f"Storage file not found when deleting image: {image.storage_path}")
        
        # Delete from database
        db.delete(image)
        db.commit()
        
        return None
        
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}", extra={"user_id": current_user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the image"
        )


@router.get("/team/{team_id}", response_model=List[ImageResponse])
async def get_team_images(
    team_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all images for a specific team (admin only or own team)
    """
    # Check if user has access to this team's images
    if not team_access_required(team_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this team's images"
        )
    
    try:
        images = db.query(Image).filter(Image.team_id == team_id).order_by(Image.created_at.desc()).offset(skip).limit(limit).all()
        
        # Generate signed URLs for each image
        result = []
        for image in images:
            url = storage_service.generate_signed_url(image.storage_path)
            result.append(ImageResponse(
                id=image.id,
                original_filename=image.original_filename,
                filename=image.filename,
                storage_path=image.storage_path,
                media_type=image.media_type,
                size_bytes=image.size_bytes,
                width=image.width,
                height=image.height,
                team_id=image.team_id,
                user_id=image.user_id,
                created_at=image.created_at,
                updated_at=image.updated_at,
                tags=image.tags,
                image_metadata=image.image_metadata,  # Using image_metadata instead of metadata
                embedding_id=image.embedding_id,
                embedding_model=image.embedding_model,
                url=url
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving team images: {str(e)}", extra={"user_id": current_user.id, "team_id": team_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving team images"
        )
