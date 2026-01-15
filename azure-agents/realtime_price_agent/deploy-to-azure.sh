#!/bin/bash
set -e  # Exit on error

# ============================================================================
# Supply Chain API - Azure Deployment Script
# Builds image in Azure (ACR Build) and deploys to Container Apps
# ============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="ImagineCup"
ACR_NAME="imaginecupreg999"
APP_NAME="amazon-api-app"  # Update existing app
IMAGE_NAME="supply-chain-api"
NEW_TAG="v11"  # New version with full API

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Supply Chain API Deployment${NC}"
echo -e "${BLUE}================================================${NC}"

# Step 1: Build image in Azure (no local Docker needed!)
echo -e "\n${GREEN}Step 1: Building image in Azure Container Registry...${NC}"
echo "This builds the image directly in Azure - no local Docker needed!"

az acr build \
  --registry $ACR_NAME \
  --image $IMAGE_NAME:$NEW_TAG \
  --image $IMAGE_NAME:latest \
  --file Dockerfile \
  --platform linux/amd64 \
  .

echo -e "${GREEN}✓ Image built successfully in Azure!${NC}"

# Step 2: Prepare environment variables
echo -e "\n${GREEN}Step 2: Loading environment variables from .env...${NC}"

# Source .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ Warning: .env file not found. Please create it first.${NC}"
    exit 1
fi

source .env

# Validate required variables
REQUIRED_VARS=(
    "DATABASE_URL"
    "AZURE_OPENAI_ENDPOINT"
    "AZURE_OPENAI_API_KEY"
    "AZURE_OPENAI_DEPLOYMENT_NAME"
    "AZURE_OPENAI_API_VERSION"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${YELLOW}⚠ Error: $var is not set in .env${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Environment variables validated${NC}"

# Step 3: Update Container App with new image
echo -e "\n${GREEN}Step 3: Updating Container App...${NC}"
echo "Deploying to: $APP_NAME"

az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$NEW_TAG \
  --cpu 1.0 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --set-env-vars \
    "DATABASE_URL=$DATABASE_URL" \
    "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
    "AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY" \
    "AZURE_OPENAI_DEPLOYMENT_NAME=$AZURE_OPENAI_DEPLOYMENT_NAME" \
    "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
    "PORT=8000" \
    "LOG_LEVEL=INFO"

echo -e "${GREEN}✓ Container App updated!${NC}"

# Step 4: Get the URL
echo -e "\n${GREEN}Step 4: Getting application URL...${NC}"

APP_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "\n${GREEN}Your API is now live at:${NC}"
echo -e "  🌐 https://$APP_URL"
echo -e "\n${GREEN}Test endpoints:${NC}"
echo -e "  Health Check:  https://$APP_URL/api/health"
echo -e "  Dashboard:     https://$APP_URL/"
echo -e "  API Docs:      https://$APP_URL/docs"
echo -e "  Products:      https://$APP_URL/products"
echo -e "  Workflows:     https://$APP_URL/api/workflows/optimize-inventory"
echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Test health check: curl https://$APP_URL/api/health"
echo "2. Open dashboard in browser"
echo "3. Test the optimization workflow"
echo -e "\n${BLUE}================================================${NC}"
