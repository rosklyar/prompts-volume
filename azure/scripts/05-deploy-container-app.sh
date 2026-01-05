#!/bin/bash
# Deploy backend to Azure Container Apps
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"
source "$SCRIPT_DIR/../secrets/secrets.sh"

echo "=== Deploying to Azure Container Apps ==="
echo "Environment: $CONTAINER_APP_ENV"
echo "App Name: $CONTAINER_APP_NAME"
echo ""

# Get ACR credentials
LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
IMAGE_TAG="$LOGIN_SERVER/prompts-backend:latest"

# Build database connection URLs
PG_HOST="$PG_SERVER_NAME.postgres.database.azure.com"
DATABASE_URL="postgresql+asyncpg://$PG_ADMIN_USER:$PG_ADMIN_PASSWORD@$PG_HOST:5432/$DB_PROMPTS?ssl=require"
USERS_DATABASE_URL="postgresql+asyncpg://$PG_ADMIN_USER:$PG_ADMIN_PASSWORD@$PG_HOST:5432/$DB_USERS?ssl=require"
EVALS_DATABASE_URL="postgresql+asyncpg://$PG_ADMIN_USER:$PG_ADMIN_PASSWORD@$PG_HOST:5432/$DB_EVALS?ssl=require"

echo "Image: $IMAGE_TAG"
echo "Database Host: $PG_HOST"
echo ""

# Check if Container Apps environment exists
if az containerapp env show --name "$CONTAINER_APP_ENV" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Container Apps environment '$CONTAINER_APP_ENV' already exists."
else
    echo "=== Creating Container Apps Environment ==="
    az containerapp env create \
        --name "$CONTAINER_APP_ENV" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output table
fi

echo ""
echo "=== Deploying Container App ==="

# Check if app already exists
if az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo "Updating existing container app..."
    az containerapp update \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$IMAGE_TAG" \
        --set-env-vars \
            DATABASE_URL="$DATABASE_URL" \
            USERS_DATABASE_URL="$USERS_DATABASE_URL" \
            EVALS_DATABASE_URL="$EVALS_DATABASE_URL" \
            OPENAI_API_KEY="$OPENAI_API_KEY" \
            DATAFORSEO_USERNAME="$DATAFORSEO_USERNAME" \
            DATAFORSEO_PASSWORD="$DATAFORSEO_PASSWORD" \
            SECRET_KEY="$SECRET_KEY" \
            FIRST_SUPERUSER_EMAIL="$FIRST_SUPERUSER_EMAIL" \
            FIRST_SUPERUSER_PASSWORD="$FIRST_SUPERUSER_PASSWORD" \
            FRONTEND_URL="https://placeholder-frontend.com" \
            EVALUATION_API_TOKENS="$EVALUATION_API_TOKENS" \
            TOPICS_PROVIDER_SIMILARITY_THRESHOLD="$TOPICS_PROVIDER_SIMILARITY_THRESHOLD" \
            BREVO_API_KEY="$BREVO_API_KEY" \
        --output table
else
    echo "Creating new container app..."
    az containerapp create \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --environment "$CONTAINER_APP_ENV" \
        --image "$IMAGE_TAG" \
        --registry-server "$LOGIN_SERVER" \
        --registry-username "$ACR_USERNAME" \
        --registry-password "$ACR_PASSWORD" \
        --target-port "$CONTAINER_PORT" \
        --ingress external \
        --cpu "$CONTAINER_CPU" \
        --memory "$CONTAINER_MEMORY" \
        --min-replicas "$CONTAINER_MIN_REPLICAS" \
        --max-replicas "$CONTAINER_MAX_REPLICAS" \
        --env-vars \
            DATABASE_URL="$DATABASE_URL" \
            USERS_DATABASE_URL="$USERS_DATABASE_URL" \
            EVALS_DATABASE_URL="$EVALS_DATABASE_URL" \
            OPENAI_API_KEY="$OPENAI_API_KEY" \
            DATAFORSEO_USERNAME="$DATAFORSEO_USERNAME" \
            DATAFORSEO_PASSWORD="$DATAFORSEO_PASSWORD" \
            SECRET_KEY="$SECRET_KEY" \
            FIRST_SUPERUSER_EMAIL="$FIRST_SUPERUSER_EMAIL" \
            FIRST_SUPERUSER_PASSWORD="$FIRST_SUPERUSER_PASSWORD" \
            FRONTEND_URL="https://placeholder-frontend.com" \
            EVALUATION_API_TOKENS="$EVALUATION_API_TOKENS" \
            TOPICS_PROVIDER_SIMILARITY_THRESHOLD="$TOPICS_PROVIDER_SIMILARITY_THRESHOLD" \
            BREVO_API_KEY="$BREVO_API_KEY" \
        --output table
fi

echo ""
echo "=== Deployment Complete ==="

# Get the app URL
APP_URL=$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "=== Application Info ==="
echo "App URL: https://$APP_URL"
echo "Health Check: https://$APP_URL/health"
echo "API Docs: https://$APP_URL/docs"
echo ""
echo "Test with:"
echo "  curl https://$APP_URL/health"
