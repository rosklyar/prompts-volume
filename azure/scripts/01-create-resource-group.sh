#!/bin/bash
# Create Azure resource group
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

echo "=== Creating Resource Group ==="
echo "Name: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Check if resource group already exists
if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    echo "Resource group '$RESOURCE_GROUP' already exists."
    az group show --name "$RESOURCE_GROUP" --output table
else
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output table

    echo ""
    echo "Resource group '$RESOURCE_GROUP' created successfully!"
fi

echo ""
echo "Next step: ./02-create-database.sh"
