#!/bin/bash
# Create Azure Storage Account and upload session files for AI Assistant bots
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

echo "=== Creating Bot Storage ==="
echo "Storage Account: $STORAGE_ACCOUNT_NAME"
echo "Location: $LOCATION"
echo ""

# Register storage provider if needed
az provider register --namespace Microsoft.Storage --wait 2>/dev/null || true

# Create storage account
echo "=== Creating Storage Account ==="
if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Storage account '$STORAGE_ACCOUNT_NAME' already exists."
else
    az storage account create \
        --name "$STORAGE_ACCOUNT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --output table
fi

# Get storage key
STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" -o tsv)

export AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT_NAME"
export AZURE_STORAGE_KEY="$STORAGE_KEY"

# Create file shares
echo ""
echo "=== Creating File Shares ==="
for pool in pool-1 pool-2; do
    if az storage share show --name "$pool" &>/dev/null 2>&1; then
        echo "Share '$pool' already exists."
    else
        az storage share create --name "$pool" --quota 1 --output table
        echo "Created share: $pool"
    fi
done

# Upload session files
echo ""
echo "=== Uploading Session Files ==="
SESSIONS_DIR="$PROJECT_ROOT/azure/ai-assistant/sessions"

echo "Uploading pool_1 sessions..."
az storage file upload-batch \
    --destination pool-1 \
    --source "$SESSIONS_DIR/pool_1" \
    --output table

echo "Uploading pool_2 sessions..."
az storage file upload-batch \
    --destination pool-2 \
    --source "$SESSIONS_DIR/pool_2" \
    --output table

# List uploaded files
echo ""
echo "=== Uploaded Files ==="
echo "pool-1:"
az storage file list --share-name pool-1 --query "[].name" -o tsv
echo ""
echo "pool-2:"
az storage file list --share-name pool-2 --query "[].name" -o tsv

echo ""
echo "=== Storage Setup Complete ==="
echo "Storage Account: $STORAGE_ACCOUNT_NAME"
echo "File Shares: pool-1, pool-2"
echo ""
echo "Next step: ./09-deploy-bots.sh"
