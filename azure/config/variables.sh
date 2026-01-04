#!/bin/bash
# Azure deployment configuration variables
# This file is git-tracked and contains non-secret configuration

# Azure region
export LOCATION="canadacentral"

# Resource naming
export RESOURCE_GROUP="prompts-rg"
export PG_SERVER_NAME="prompts-pg-server"
export ACR_NAME="promptsacr"
export CONTAINER_APP_ENV="prompts-env"
export CONTAINER_APP_NAME="prompts-backend"

# PostgreSQL configuration
export PG_ADMIN_USER="pgadmin"
export PG_SKU="Standard_B1ms"
export PG_STORAGE_SIZE="32"
export PG_VERSION="16"

# Database names
export DB_PROMPTS="prompts"
export DB_USERS="users"
export DB_EVALS="evals"

# Container configuration
export CONTAINER_CPU="1.0"
export CONTAINER_MEMORY="2.0Gi"
export CONTAINER_MIN_REPLICAS="1"
export CONTAINER_MAX_REPLICAS="3"
export CONTAINER_PORT="8000"

# Application configuration (non-secret)
export TOPICS_PROVIDER_SIMILARITY_THRESHOLD="0.8"

# Frontend configuration
export STATIC_WEB_APP_NAME="prompts-frontend"
export BACKEND_URL="https://prompts-backend.jollydune-754acd02.canadacentral.azurecontainerapps.io"

# Bot configuration
export STORAGE_ACCOUNT_NAME="promptsbotstorage01"
export BOT_IMAGE_NAME="ai-assistant"
export BOT_IMAGE_TAG="v1.0.release"
