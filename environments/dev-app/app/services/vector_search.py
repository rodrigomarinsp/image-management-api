# app/services/vector_search.py
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import pinecone
import numpy as np
from sentence_transformers import SentenceTransformer
from google.cloud import vision
from PIL import Image as PILImage
import io
import time
import hashlib
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger

class VectorSearchService:
    def __init__(self):
        """Initialize the vector search service with CLIP model and Pinecone database"""
        if not settings.ENABLE_VECTOR_SEARCH:
            logger.warning("Vector search is disabled. Set ENABLE_VECTOR_SEARCH=true to enable it.")
            self.enabled = False
            return

        self.enabled = True
        
        try:
            # Initialize the embedding model
            self._initialize_embedding_model()
            
            # Initialize the vector database
            self._initialize_vector_database()
            
            # Initialize Vision client for Google Vision API alternative
            self._initialize_vision_client()
            
            logger.info("Vector search service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vector search service: {str(e)}")
            self.enabled = False

    def _initialize_embedding_model(self):
        """Initialize the CLIP embedding model"""
        logger.info("Initializing CLIP model...")
        try:
            self.model = SentenceTransformer('clip-ViT-B-32')
            logger.info("CLIP model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing CLIP model: {str(e)}")
            raise

    def _initialize_vector_database(self):
        """Initialize the Pinecone vector database"""
        logger.info(f"Initializing Pinecone with environment: {settings.PINECONE_ENVIRONMENT}")
        try:
            pinecone.init(
                api_key=settings.PINECONE_API_KEY,
                environment=settings.PINECONE_ENVIRONMENT
            )
            
            # Check if index exists, create if it doesn't
            index_name = settings.PINECONE_INDEX_NAME
            if index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {index_name}")
                pinecone.create_index(
                    name=index_name,
                    dimension=512,  # CLIP embedding dimension
                    metric="cosine"
                )
                logger.info(f"Created Pinecone index: {index_name}")

            self.index = pinecone.Index(index_name)
            self.namespace = f"{settings.ENVIRONMENT}-images" if hasattr(settings, "ENVIRONMENT") else "default-images"
            logger.info(f"Connected to Pinecone index: {index_name}, namespace: {self.namespace}")
        except Exception as e:
            logger.error(f"Error initializing Pinecone: {str(e)}")
            raise

    def _initialize_vision_client(self):
        """Initialize Google Vision client as a backup for image understanding"""
        try:
            self.vision_client = vision.ImageAnnotatorClient()
            logger.info("Google Vision client initialized")
        except Exception as e:
            logger.warning(f"Google Vision client initialization failed: {str(e)}")
            self.vision_client = None

    async def process_image_upload(self, image_path: str, image_id: int, team_id: int, 
                                 metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process an uploaded image to generate and store embeddings"""
        if not self.enabled:
            logger.warning("Attempted to process image upload but vector search is disabled")
            return {"success": False, "reason": "Vector search disabled"}

        try:
            # Generate embedding from image
            embedding = await self.get_embedding_from_image_file(image_path)
            if not embedding:
                return {"success": False, "reason": "Failed to generate embedding"}
            
            # Prepare metadata for storage
            vector_metadata = {
                "image_id": str(image_id),
                "team_id": str(team_id),
                "original_metadata": metadata,
                "processed_at": time.time()
            }
            
            # Store in Pinecone
            success = await self.store_embedding(str(image_id), embedding, vector_metadata)
            
            return {
                "success": success,
                "embedding_id": str(image_id) if success else None,
                "embedding_model": "clip-ViT-B-32",
            }
        except Exception as e:
            logger.error(f"Error processing image upload: {str(e)}")
            return {"success": False, "reason": str(e)}

    async def get_embedding_from_image_file(self, image_path: str) -> List[float]:
        """Generate embedding from an image file using CLIP model"""
        if not self.enabled:
            logger.warning("Attempted to get embedding but vector search is disabled")
            return []

        try:
            # Handle both local path and file-like objects
            if isinstance(image_path, str):
                if os.path.exists(image_path):
                    image = PILImage.open(image_path)
                else:
                    logger.error(f"Image file not found: {image_path}")
                    return []
            else:
                # Assume it's a file-like object
                image = PILImage.open(image_path)
                
            # Process image for CLIP
            embedding = self.model.encode(image)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Fallback to Google Vision API if available
            return await self._fallback_vision_embedding(image_path)

    async def _fallback_vision_embedding(self, image_path: str) -> List[float]:
        """Fallback method to get image features using Google Vision API"""
        if not self.vision_client:
            return []
            
        try:
            # Read image content
            if isinstance(image_path, str):
                with open(image_path, "rb") as image_file:
                    content = image_file.read()
            else:
                # Assume it's a file-like object
                content = image_path.read()
                
            image = vision.Image(content=content)
            
            # Extract image properties
            response = self.vision_client.image_properties(image=image)
            props = response.image_properties_annotation
            
            # Create a simple embedding from color distribution
            # Not as good as CLIP but better than nothing
            features = []
            for color in props.dominant_colors.colors:
                features.extend([
                    color.color.red / 255.0,
                    color.color.green / 255.0,
                    color.color.blue / 255.0,
                    color.score,
                    color.pixel_fraction
                ])
            
            # Pad or truncate to get 512 dimensions
            if len(features) > 512:
                features = features[:512]
            else:
                features.extend([0.0] * (512 - len(features)))
                
            return features
        except Exception as e:
            logger.error(f"Error in Vision API fallback: {str(e)}")
            return []

    async def get_embedding_from_text(self, text: str) -> List[float]:
        """Generate embedding from text using CLIP model"""
        if not self.enabled:
            logger.warning("Attempted to get text embedding but vector search is disabled")
            return []

        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating text embedding: {str(e)}")
            return []

    async def store_embedding(self, image_id: str, embedding: List[float], 
                            metadata: Dict[str, Any]) -> bool:
        """Store an embedding in Pinecone"""
        if not self.enabled or not embedding:
            logger.warning("Attempted to store embedding but vector search is disabled or embedding is empty")
            return False

        try:
            # Create a unique ID to avoid collisions
            self.index.upsert(
                vectors=[(image_id, embedding, metadata)],
                namespace=self.namespace
            )
            logger.info(f"Stored embedding for image {image_id} in namespace {self.namespace}")
            return True
        except Exception as e:
            logger.error(f"Error storing embedding: {str(e)}")
            return False

    async def search_by_text(
            self, 
            text_query: str, 
            team_id: int, 
            limit: int = 10,
            min_score: float = 0.5
        ) -> List[Dict[str, Any]]:
        """Search images by text query using semantic similarity"""
        if not self.enabled:
            logger.warning("Attempted to search by text but vector search is disabled")
            return []

        try:
            # Get embedding for the text query
            logger.info(f"Generating embedding for query: '{text_query}'")
            query_embedding = await self.get_embedding_from_text(text_query)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []

            # Filter by team_id for access control
            filter_dict = {"team_id": str(team_id)}

            # Search Pinecone
            logger.info(f"Searching Pinecone with filter: {filter_dict}, top_k: {limit}")
            results = self.index.query(
                vector=query_embedding,
                filter=filter_dict,
                top_k=limit,
                namespace=self.namespace,
                include_metadata=True
            )

            logger.info(f"Search returned {len(results['matches'])} results")

            # Filter by minimum score and format results
            filtered_results = []
            for match in results["matches"]:
                if match["score"] < min_score:
                    continue
                    
                filtered_results.append({
                    "image_id": match["id"],
                    "score": float(match["score"]),
                    "metadata": match["metadata"]
                })
                
            return filtered_results
        except Exception as e:
            logger.error(f"Error searching by text: {str(e)}")
            return []

    async def search_by_image(self, image_file: UploadFile, team_id: int, 
                            limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar images using image-to-image similarity"""
        if not self.enabled:
            logger.warning("Attempted to search by image but vector search is disabled")
            return []

        try:
            # Read image content
            content = await image_file.read()
            
            # Create a temporary file for the image
            image = PILImage.open(io.BytesIO(content))
            
            # Generate embedding
            query_embedding = self.model.encode(image).tolist()
            
            # Filter by team_id for access control
            filter_dict = {"team_id": str(team_id)}

            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                filter=filter_dict,
                top_k=limit,
                namespace=self.namespace,
                include_metadata=True
            )
            
            return [
                {
                    "image_id": match["id"],
                    "score": float(match["score"]),
                    "metadata": match["metadata"]
                }
                for match in results["matches"]
            ]
        except Exception as e:
            logger.error(f"Error searching by image: {str(e)}")
            return []

    async def delete_embedding(self, image_id: str) -> bool:
        """Delete an embedding from Pinecone"""
        if not self.enabled:
            return False

        try:
            self.index.delete(ids=[image_id], namespace=self.namespace)
            logger.info(f"Deleted embedding for image {image_id} from namespace {self.namespace}")
            return True
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            return False
            
    async def get_similar_images(self, image_id: str, team_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Find images similar to a given image by ID"""
        if not self.enabled:
            logger.warning("Attempted to get similar images but vector search is disabled")
            return []
        
        try:
            # Get the vector for the reference image
            vector_response = self.index.fetch(ids=[image_id], namespace=self.namespace)
            
            if not vector_response or image_id not in vector_response["vectors"]:
                logger.error(f"Reference image vector not found: {image_id}")
                return []
                
            reference_vector = vector_response["vectors"][image_id]["values"]
            
            # Filter by team_id for access control
            filter_dict = {"team_id": str(team_id)}
            
            # Search Pinecone (excluding the reference image itself)
            results = self.index.query(
                vector=reference_vector,
                filter=filter_dict,
                top_k=limit + 1,  # +1 because we'll remove the reference image itself
                namespace=self.namespace,
                include_metadata=True
            )
            
            # Filter out the reference image
            similar_images = [
                {
                    "image_id": match["id"],
                    "score": float(match["score"]),
                    "metadata": match["metadata"]
                }
                for match in results["matches"]
                if match["id"] != image_id
            ]
            
            return similar_images[:limit]  # Ensure we return only the requested number
        except Exception as e:
            logger.error(f"Error finding similar images: {str(e)}")
            return []

# Initialize the service
vector_search_service = VectorSearchService()