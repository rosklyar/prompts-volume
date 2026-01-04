#!/bin/bash
# Build and push Docker image to Azure Container Registry
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

echo "=== Building and Pushing Docker Image ==="
echo "Registry: $ACR_NAME"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Get ACR login server
LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
IMAGE_TAG="$LOGIN_SERVER/prompts-backend:latest"

echo "Image: $IMAGE_TAG"
echo ""

# Login to ACR
echo "=== Logging in to ACR ==="
az acr login --name "$ACR_NAME"

# Build the image locally
echo ""
echo "=== Building Docker Image ==="
echo "This may take several minutes (ML models are pre-downloaded during build)..."
docker build -t "$IMAGE_TAG" "$PROJECT_ROOT/backend"

# Push to ACR
echo ""
echo "=== Pushing to ACR ==="
docker push "$IMAGE_TAG"

echo ""
echo "=== Image pushed successfully ==="
echo "Image: $IMAGE_TAG"
echo ""
echo "Next step: ./05-deploy-container-app.sh"
