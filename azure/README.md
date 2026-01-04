# Azure Deployment

Deploy the prompts-volume backend to Azure.

## Prerequisites

1. **Azure CLI** installed: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
2. **Docker** installed (for local image builds)
3. Azure account with active subscription

## Quick Start

### 1. Configure Secrets

```bash
# Copy template and fill in values
cp config/secrets.sh.template secrets/secrets.sh

# Edit secrets/secrets.sh with your values:
# - PG_ADMIN_PASSWORD: Strong password for PostgreSQL
# - SECRET_KEY: Run `openssl rand -hex 32` to generate
# - FIRST_SUPERUSER_EMAIL: Your admin email
# - FIRST_SUPERUSER_PASSWORD: Your admin password
```

### 2. Deploy Step by Step

```bash
cd azure/scripts

# Step 1: Login to Azure
./00-login.sh

# Step 2: Create resource group
./01-create-resource-group.sh

# Step 3: Create PostgreSQL with pgvector
./02-create-database.sh

# Step 4: Create Container Registry
./03-create-container-registry.sh

# Step 5: Build and push Docker image
./04-build-and-push.sh

# Step 6: Deploy to Container Apps
./05-deploy-container-app.sh
```

### 3. Verify Deployment

After deployment, you'll get a URL like:
```
https://prompts-backend.<random>.westeurope.azurecontainerapps.io
```

Test it:
```bash
curl https://<your-app-url>/health
# Should return: {"status":"UP"}
```

## Configuration

### Non-Secret Variables (`config/variables.sh`)

| Variable | Default | Description |
|----------|---------|-------------|
| LOCATION | westeurope | Azure region |
| RESOURCE_GROUP | prompts-rg | Resource group name |
| PG_SERVER_NAME | prompts-pg-server | PostgreSQL server name |
| ACR_NAME | promptsacr | Container registry name |
| PG_SKU | Standard_B1ms | PostgreSQL tier |

### Secrets (`secrets/secrets.sh`)

| Variable | Description |
|----------|-------------|
| PG_ADMIN_PASSWORD | PostgreSQL admin password |
| OPENAI_API_KEY | OpenAI API key |
| DATAFORSEO_USERNAME | DataForSEO username |
| DATAFORSEO_PASSWORD | DataForSEO password |
| SECRET_KEY | JWT signing key |
| FIRST_SUPERUSER_EMAIL | Admin user email |
| FIRST_SUPERUSER_PASSWORD | Admin user password |
| EVALUATION_API_TOKENS | Bot API tokens |

## Estimated Costs

| Service | SKU | Monthly Cost |
|---------|-----|--------------|
| PostgreSQL Flexible Server | Standard_B1ms | ~$16 |
| Container Apps | Consumption | ~$5-20 |
| Container Registry | Basic | ~$5 |
| **Total** | | **~$26-41** |

## Cleanup

To delete all Azure resources:

```bash
./scripts/99-cleanup.sh
```

**Warning:** This permanently deletes all data!

## Troubleshooting

### Check Container Logs

```bash
az containerapp logs show \
  --name prompts-backend \
  --resource-group prompts-rg \
  --follow
```

### Check Container Status

```bash
az containerapp show \
  --name prompts-backend \
  --resource-group prompts-rg \
  --output table
```

### Restart Container

```bash
az containerapp revision restart \
  --name prompts-backend \
  --resource-group prompts-rg \
  --revision <revision-name>
```

### Connect to PostgreSQL

```bash
# Get connection info
az postgres flexible-server show \
  --name prompts-pg-server \
  --resource-group prompts-rg

# Connect via psql (requires allowing your IP in firewall)
psql "host=prompts-pg-server.postgres.database.azure.com port=5432 dbname=prompts user=pgadmin sslmode=require"
```
