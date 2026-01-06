#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

VERSION=${1:-""}

if [ -z "$VERSION" ]; then
  echo "Usage: ./rollback.sh <version>"
  echo "Example: ./rollback.sh 0.1.5"
  echo ""
  echo "Available versions:"
  az acr repository show-tags --name "$ACR_NAME" --repository prompts-backend --orderby time_desc --top 10
  exit 1
fi

echo "Rolling back backend to v$VERSION..."
az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_NAME.azurecr.io/prompts-backend:v$VERSION"

echo "Done. Frontend requires manual rebuild from tag v$VERSION"
