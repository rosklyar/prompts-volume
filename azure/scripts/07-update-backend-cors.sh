#!/bin/bash
# Update backend CORS to allow frontend URL
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"
source "$SCRIPT_DIR/../secrets/secrets.sh"

echo "=== Updating Backend CORS ==="

# Custom domain for frontend
FRONTEND_URL="https://app.tryllmhero.com"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Update backend container app
echo "=== Updating Container App Environment Variable ==="
az containerapp update \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --set-env-vars FRONTEND_URL="$FRONTEND_URL" \
    --output table

echo ""
echo "=== CORS Updated ==="
echo "Backend now allows requests from: $FRONTEND_URL"
echo ""
echo "Test the full flow:"
echo "  1. Open: $FRONTEND_URL"
echo "  2. Try logging in with your credentials"
