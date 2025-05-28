#!/bin/bash
# scripts/deploy.sh

# This script deploys the application to Google Cloud Run

# Variables
PROJECT_ID=$(gcloud config get-value project)
IMAGE_NAME="image-management-api"
REGION="europe-west1"  # Change to your preferred region
SERVICE_NAME="img-manag-api"

# Build the Docker image
echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME .

# Push to Container Registry
echo "Pushing image to Container Registry..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated

echo "Deployment complete!"
