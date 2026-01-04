#!/bin/bash
# Cleanup all Azure resources
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

echo "=== Azure Resource Cleanup ==="
echo ""
echo "WARNING: This will DELETE all resources in the resource group:"
echo "  - Resource Group: $RESOURCE_GROUP"
echo "  - PostgreSQL Server: $PG_SERVER_NAME"
echo "  - Container Registry: $ACR_NAME"
echo "  - Container App: $CONTAINER_APP_NAME"
echo "  - Container Environment: $CONTAINER_APP_ENV"
echo ""
echo "ALL DATA WILL BE PERMANENTLY DELETED!"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Deleting resource group '$RESOURCE_GROUP'..."
echo "This may take several minutes..."

az group delete \
    --name "$RESOURCE_GROUP" \
    --yes \
    --no-wait

echo ""
echo "Resource group deletion initiated."
echo "The deletion is running in the background."
echo ""
echo "You can check the status with:"
echo "  az group show --name $RESOURCE_GROUP"
echo ""
echo "When the resource group no longer exists, all resources have been deleted."
