#!/bin/bash
# Azure CLI login script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

echo "=== Azure CLI Login ==="
echo ""
echo "This will open a browser for Azure authentication."
echo "Make sure you log in with your account that has the $1000 startup credits."
echo ""

# Login to Azure
az login

# List available subscriptions
echo ""
echo "=== Available Subscriptions ==="
az account list --output table

echo ""
echo "Current subscription:"
az account show --output table

echo ""
echo "If you need to switch subscriptions, run:"
echo "  az account set --subscription \"<subscription-name-or-id>\""
echo ""
echo "Then proceed with: ./01-create-resource-group.sh"
