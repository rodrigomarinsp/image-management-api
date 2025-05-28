# app/services/storage.py
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import UploadFile
import io
import logging
from PIL import Image as PILImage
import imghdr

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """
    Storage service for handling file operations.
    
    For local development, this uses a simple file system storage.
    In production, this would be replaced with Google Cloud Storage.
    """
    
    def __init__(self):
        # Set up local storage directory for development
        self.storage_dir = os.path.join(os.getcwd(), "storage")
        os.makedirs(self.storage_dir, exist_ok=True)
        logger.info(f"Storage service initialized with directory: {self.storage_dir}")
        
        # Set up GCS client if configured
        self.use_gcs = False
        if settings.GCS_BUCKET_NAME and settings.GCS_PROJECT_ID:
            try:
                from google.cloud import storage
                
                if settings.GCS_CREDENTIALS_FILE and os.path.exists(settings.GCS_CREDENTIALS_FILE):
                    self.client = storage.Client.from_service_account_json(
                        settings.GCS_CREDENTIALS_FILE
                    )
                else:
                    # Use Application Default Credentials
                    self.client = storage.Client(project=settings.GCS_PROJECT_ID)
                
                self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)
                
                # Ensure bucket exists
                if not self.bucket.exists():
                    logger.info(f"Creating bucket {settings.GCS_BUCKET_NAME}")
                    self.bucket = self.client.create_bucket(settings.GCS_BUCKET_NAME)
                
                self.use_gcs = True
                logger.info(f"Using Google Cloud Storage: {settings.GCS_BUCKET_NAME}")
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud Storage: {str(e)}")
                logger.info("Falling back to local file storage")
    
    async def validate_image(self, file: UploadFile) -> Tuple[bool, str, Optional[dict]]:
        """
        Validates if the uploaded file is a valid image and returns its properties
        """
        # Check file size
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > settings.MAX_UPLOAD_SIZE:
            return False, f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024} MB", None
            
        # Read the file content
        content = await file.read()
        await file.seek(0)
        
        # Check if it's a valid image
        img_format = imghdr.what(None, content)
        if not img_format:
            return False, "Invalid image format", None
            
        allowed_extensions = settings.ALLOWED_IMAGE_EXTENSIONS
        if isinstance(allowed_extensions, str):
            # Handle case where extensions might come as a string
            try:
                allowed_extensions = allowed_extensions.replace(" ", "").split(",")
            except:
                allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
                
        if img_format not in allowed_extensions:
            return False, f"Invalid image format. Allowed formats: {', '.join(allowed_extensions)}", None
            
        # Get image dimensions
        try:
            img = PILImage.open(io.BytesIO(content))
            width, height = img.size
            image_info = {
                "width": width,
                "height": height,
                "format": img.format.lower() if img.format else img_format,
                "size_bytes": size
            }
            return True, "Valid image", image_info
        except Exception as e:
            logger.error(f"Error validating image: {str(e)}")
            return False, f"Error processing image: {str(e)}", None

    async def upload_file(
        self, file: UploadFile, team_id: int, user_id: int
    ) -> dict:
        """
        Uploads a file to storage and returns its metadata
        """
        # Validate the image first
        is_valid, message, image_info = await self.validate_image(file)
        if not is_valid:
            raise ValueError(message)
        
        # Generate a unique filename
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        original_filename = file.filename
        extension = original_filename.split(".")[-1].lower()
        
        # Create storage path: teams/{team_id}/images/{year}/{month}/{filename}
        year_month = datetime.now().strftime("%Y/%m")
        storage_path = f"teams/{team_id}/images/{year_month}/{unique_id}_{timestamp}.{extension}"
        
        content = await file.read()
        
        if self.use_gcs:
            # Upload to GCS
            try:
                blob = self.bucket.blob(storage_path)
                blob.upload_from_string(
                    content,
                    content_type=file.content_type
                )
                logger.info(f"Uploaded file to GCS: {storage_path}")
            except Exception as e:
                logger.error(f"Error uploading to GCS: {str(e)}")
                raise ValueError(f"Error uploading file to cloud storage: {str(e)}")
        else:
            # Upload to local filesystem
            try:
                # Create directory structure
                local_dir = os.path.join(self.storage_dir, f"teams/{team_id}/images/{year_month}")
                os.makedirs(local_dir, exist_ok=True)
                
                local_path = os.path.join(self.storage_dir, storage_path)
                with open(local_path, "wb") as f:
                    f.write(content)
                logger.info(f"Uploaded file to local storage: {local_path}")
            except Exception as e:
                logger.error(f"Error uploading to local storage: {str(e)}")
                raise ValueError(f"Error saving file: {str(e)}")
        
        # Return metadata
        return {
            "original_filename": original_filename,
            "filename": f"{unique_id}_{timestamp}.{extension}",
            "storage_path": storage_path,
            "media_type": file.content_type,
            "size_bytes": image_info["size_bytes"],
            "width": image_info["width"],
            "height": image_info["height"]
        }
        
    def generate_signed_url(self, storage_path: str, expiration_minutes: int = 15) -> str:
        """
        Generate a URL for accessing the file
        
        For GCS, this generates a signed URL
        For local storage, this returns a direct path
        """
        try:
            if self.use_gcs:
                blob = self.bucket.blob(storage_path)
                
                if not blob.exists():
                    logger.warning(f"File does not exist in GCS: {storage_path}")
                    raise ValueError("File does not exist")
                    
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(minutes=expiration_minutes),
                    method="GET"
                )
                return url
            else:
                # For local development, return a relative path
                local_path = f"/storage/{storage_path}"
                # In a real app, this would be a proper URL with domain
                return f"http://localhost:8000{local_path}"
        except Exception as e:
            logger.error(f"Error generating URL for {storage_path}: {str(e)}")
            # Return a placeholder to prevent the app from breaking
            return f"http://localhost:8000/placeholder-image"
        
    def delete_file(self, storage_path: str) -> bool:
        """
        Deletes a file from storage
        """
        try:
            if self.use_gcs:
                blob = self.bucket.blob(storage_path)
                
                if not blob.exists():
                    logger.warning(f"File does not exist in GCS when attempting to delete: {storage_path}")
                    return False
                    
                blob.delete()
                logger.info(f"Deleted file from GCS: {storage_path}")
            else:
                # Delete from local filesystem
                local_path = os.path.join(self.storage_dir, storage_path)
                if not os.path.exists(local_path):
                    logger.warning(f"File does not exist in local storage when attempting to delete: {local_path}")
                    return False
                
                os.remove(local_path)
                logger.info(f"Deleted file from local storage: {local_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting file {storage_path}: {str(e)}")
            return False


# Create a singleton instance
storage_service = StorageService()
