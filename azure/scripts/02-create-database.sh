#!/bin/bash
# Create Azure PostgreSQL Flexible Server with pgvector
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config/variables.sh"
source "$SCRIPT_DIR/../secrets/secrets.sh"

echo "=== Creating PostgreSQL Flexible Server ==="
echo "Server: $PG_SERVER_NAME"
echo "Location: $LOCATION"
echo "SKU: $PG_SKU"
echo "Version: $PG_VERSION"
echo ""

# Check if server already exists
if az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$PG_SERVER_NAME" &>/dev/null; then
    echo "PostgreSQL server '$PG_SERVER_NAME' already exists."
else
    echo "Creating PostgreSQL Flexible Server (this may take several minutes)..."
    az postgres flexible-server create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PG_SERVER_NAME" \
        --location "$LOCATION" \
        --admin-user "$PG_ADMIN_USER" \
        --admin-password "$PG_ADMIN_PASSWORD" \
        --tier Burstable \
        --sku-name "$PG_SKU" \
        --storage-size "$PG_STORAGE_SIZE" \
        --version "$PG_VERSION" \
        --yes \
        --output table

    echo ""
    echo "PostgreSQL server created successfully!"
fi

echo ""
echo "=== Enabling pgvector Extension ==="
az postgres flexible-server parameter set \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$PG_SERVER_NAME" \
    --name azure.extensions \
    --value vector \
    --output table

echo ""
echo "=== Creating Databases ==="

# Create prompts database
echo "Creating database: $DB_PROMPTS"
az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$PG_SERVER_NAME" \
    --database-name "$DB_PROMPTS" \
    --output table 2>/dev/null || echo "Database '$DB_PROMPTS' may already exist"

# Create users database
echo "Creating database: $DB_USERS"
az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$PG_SERVER_NAME" \
    --database-name "$DB_USERS" \
    --output table 2>/dev/null || echo "Database '$DB_USERS' may already exist"

# Create evals database
echo "Creating database: $DB_EVALS"
az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$PG_SERVER_NAME" \
    --database-name "$DB_EVALS" \
    --output table 2>/dev/null || echo "Database '$DB_EVALS' may already exist"

echo ""
echo "=== Configuring Firewall Rules ==="
echo "Allowing Azure services to connect..."
az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PG_SERVER_NAME" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    --output table 2>/dev/null || echo "Firewall rule may already exist"

echo ""
echo "=== PostgreSQL Server Info ==="
az postgres flexible-server show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PG_SERVER_NAME" \
    --output table

# Display connection info
PG_HOST="$PG_SERVER_NAME.postgres.database.azure.com"
echo ""
echo "=== Connection Information ==="
echo "Host: $PG_HOST"
echo "Port: 5432"
echo "Admin User: $PG_ADMIN_USER"
echo "Databases: $DB_PROMPTS, $DB_USERS, $DB_EVALS"
echo ""
echo "Connection string format:"
echo "postgresql+asyncpg://$PG_ADMIN_USER:<password>@$PG_HOST:5432/<database>?ssl=require"
echo ""
echo "Next step: ./03-create-container-registry.sh"
