#!/bin/bash
# Deploy frontend to Azure Static Web Apps
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"

# Static Web Apps only available in: westus2, centralus, eastus2, westeurope, eastasia
SWA_LOCATION="centralus"

echo "=== Deploying Frontend to Azure Static Web Apps ==="
echo "App Name: $STATIC_WEB_APP_NAME"
echo "Location: $SWA_LOCATION (Static Web Apps region)"
echo "Backend URL: $BACKEND_URL"
echo ""

# Register provider if needed
echo "=== Checking Microsoft.Web provider ==="
az provider register --namespace Microsoft.Web --wait 2>/dev/null || true

# Build frontend with production API URL
echo ""
echo "=== Building Frontend ==="
cd "$PROJECT_ROOT/frontend"
VITE_API_URL="$BACKEND_URL" npm run build
echo "Build complete: $PROJECT_ROOT/frontend/dist"

# Create Static Web App
echo ""
echo "=== Creating Static Web App ==="
if az staticwebapp show --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Static Web App '$STATIC_WEB_APP_NAME' already exists."
else
    az staticwebapp create \
        --name "$STATIC_WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$SWA_LOCATION" \
        --sku Free \
        --output table
fi

# Get deployment token
echo ""
echo "=== Deploying to Static Web App ==="
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.apiKey" -o tsv)

# Deploy using SWA CLI
cd "$PROJECT_ROOT/frontend"
npx --yes @azure/static-web-apps-cli deploy ./dist \
    --deployment-token "$DEPLOYMENT_TOKEN" \
    --env production

# Get the app URL
echo ""
echo "=== Getting App URL ==="
FRONTEND_URL=$(az staticwebapp show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" -o tsv)

echo ""
echo "=== Deployment Complete ==="
echo "Frontend URL: https://$FRONTEND_URL"
echo ""
echo "Next step: Update backend CORS with this URL"
echo "Run: ./07-update-backend-cors.sh"
