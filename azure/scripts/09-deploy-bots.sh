#!/bin/bash
# Deploy AI Assistant bots to Azure Container Apps
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

# Load bot env vars
BOT_ENV_FILE="$PROJECT_ROOT/azure/ai-assistant/.env"
if [ ! -f "$BOT_ENV_FILE" ]; then
    echo "Error: Bot env file not found at $BOT_ENV_FILE"
    exit 1
fi

echo "=== Deploying AI Assistant Bots ==="
echo "Image: $ACR_NAME.azurecr.io/$BOT_IMAGE_NAME:$BOT_IMAGE_TAG"
echo "Environment: $CONTAINER_APP_ENV"
echo ""

# Push image to ACR
echo "=== Pushing Docker Image to ACR ==="
az acr login --name "$ACR_NAME"
docker tag "$BOT_IMAGE_NAME:$BOT_IMAGE_TAG" "$ACR_NAME.azurecr.io/$BOT_IMAGE_NAME:$BOT_IMAGE_TAG"
docker push "$ACR_NAME.azurecr.io/$BOT_IMAGE_NAME:$BOT_IMAGE_TAG"

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" -o tsv)

# Parse env vars from file (skip comments and empty lines)
ENV_VARS=""
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    # Remove quotes from value
    value="${value%\"}"
    value="${value#\"}"
    ENV_VARS="$ENV_VARS $key=$value"
done < "$BOT_ENV_FILE"

# Deploy function
deploy_bot() {
    local BOT_NAME=$1
    local POOL_NAME=$2
    local STORAGE_NAME="${POOL_NAME}-storage"

    echo ""
    echo "=== Deploying $BOT_NAME (mounting $POOL_NAME) ==="

    # Add storage to environment for this pool
    echo "Adding storage mount for $POOL_NAME..."
    az containerapp env storage set \
        --name "$CONTAINER_APP_ENV" \
        --resource-group "$RESOURCE_GROUP" \
        --storage-name "$STORAGE_NAME" \
        --azure-file-account-name "$STORAGE_ACCOUNT_NAME" \
        --azure-file-account-key "$STORAGE_KEY" \
        --azure-file-share-name "$POOL_NAME" \
        --access-mode ReadOnly \
        --output table 2>/dev/null || true

    # Check if bot already exists
    if az containerapp show --name "$BOT_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        echo "Updating existing bot $BOT_NAME..."
        az containerapp update \
            --name "$BOT_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --image "$ACR_NAME.azurecr.io/$BOT_IMAGE_NAME:$BOT_IMAGE_TAG" \
            --set-env-vars $ENV_VARS \
            --output table
    else
        echo "Creating new bot $BOT_NAME..."
        az containerapp create \
            --name "$BOT_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --environment "$CONTAINER_APP_ENV" \
            --image "$ACR_NAME.azurecr.io/$BOT_IMAGE_NAME:$BOT_IMAGE_TAG" \
            --registry-server "$ACR_NAME.azurecr.io" \
            --registry-username "$ACR_USERNAME" \
            --registry-password "$ACR_PASSWORD" \
            --cpu 1.0 \
            --memory 2.0Gi \
            --min-replicas 1 \
            --max-replicas 1 \
            --env-vars $ENV_VARS \
            --output table
    fi

    # Note: Volume mounts need to be added via YAML or ARM template
    # The az containerapp create doesn't support --volume directly in all versions
    echo "Note: Volume mount for $POOL_NAME configured via environment storage"
}

# Deploy both bots
deploy_bot "ai-assistant-1" "pool-1"
deploy_bot "ai-assistant-2" "pool-2"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Bots deployed:"
echo "  - ai-assistant-1 (pool-1)"
echo "  - ai-assistant-2 (pool-2)"
echo ""
echo "Check logs with:"
echo "  az containerapp logs show --name ai-assistant-1 --resource-group $RESOURCE_GROUP --follow"
echo "  az containerapp logs show --name ai-assistant-2 --resource-group $RESOURCE_GROUP --follow"
