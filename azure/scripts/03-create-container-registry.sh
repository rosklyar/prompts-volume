#!/bin/bash
# Create Azure Container Registry
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

echo "=== Creating Azure Container Registry ==="
echo "Name: $ACR_NAME"
echo "SKU: Basic"
echo ""

# Check if ACR already exists
if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Container Registry '$ACR_NAME' already exists."
else
    echo "Creating Container Registry..."
    az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic \
        --admin-enabled true \
        --output table

    echo ""
    echo "Container Registry created successfully!"
fi

echo ""
echo "=== Container Registry Info ==="
az acr show --name "$ACR_NAME" --output table

# Get login server
LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
echo ""
echo "Login Server: $LOGIN_SERVER"
echo ""
echo "Next step: ./04-build-and-push.sh"
