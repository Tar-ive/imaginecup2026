#!/bin/bash
set -e  # Exit on error

# ============================================================================
# SupplyMind Backend - Azure Deployment Script
# Deploys FastAPI backend to Azure Container Apps
# ============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="ImagineCup"
ACR_NAME="imaginecupreg999"
APP_NAME="supplymind-backend"
IMAGE_NAME="supply-chain-api"
# Get absolute path to .env file (works from azure-agents directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)/.env"

# Parse command line arguments
TAG="latest"
CREATE_NEW=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --tag)
      TAG="$2"
      shift 2
      ;;
    --create)
      CREATE_NEW=true
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Auto-generate version tag based on timestamp
VERSION_TAG="v$(date +%Y%m%d-%H%M%S)"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  SupplyMind Backend Deployment${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Version: ${VERSION_TAG}${NC}"
echo -e "${BLUE}App Name: ${APP_NAME}${NC}"
echo -e "${BLUE}================================================${NC}"

# Step 1: Check prerequisites
echo -e "\n${GREEN}Step 1: Checking prerequisites...${NC}"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}✗ Azure CLI not found. Please install: https://aka.ms/InstallAzureCLI${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Azure CLI found${NC}"

# Check login status
if ! az account show &> /dev/null; then
    echo -e "${RED}✗ Not logged in to Azure. Please run: az login${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Logged in to Azure${NC}"

# Check .env file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ .env file not found at: $ENV_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env file found${NC}"

# Step 2: Load and validate environment variables
echo -e "\n${GREEN}Step 2: Loading environment variables...${NC}"

# Source .env file
set -a
source "$ENV_FILE"
set +a

# Validate required variables
REQUIRED_VARS=(
    "DATABASE_URL"
    "AZURE_OPENAI_ENDPOINT"
    "AZURE_OPENAI_API_KEY"
    "AZURE_OPENAI_DEPLOYMENT_NAME"
    "AZURE_OPENAI_API_VERSION"
    "MCP_SUPPLIER_DATA_URL"
    "MCP_INVENTORY_MGMT_URL"
    "MCP_FINANCE_DATA_URL"
    "MCP_ANALYTICS_FORECAST_URL"
    "MCP_INTEGRATIONS_URL"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    exit 1
fi

echo -e "${GREEN}✓ All required environment variables validated${NC}"

# Step 3: Build image in Azure Container Registry
echo -e "\n${GREEN}Step 3: Building Docker image in ACR...${NC}"
echo -e "${BLUE}Building from: realtime_price_agent/${NC}"
echo -e "${BLUE}Tags: ${VERSION_TAG}, latest${NC}"

cd realtime_price_agent

az acr build \
  --registry $ACR_NAME \
  --image $IMAGE_NAME:$VERSION_TAG \
  --image $IMAGE_NAME:latest \
  --file Dockerfile \
  --platform linux/amd64 \
  .

cd ..

echo -e "${GREEN}✓ Image built successfully!${NC}"

# Step 4: Deploy or update Container App
echo -e "\n${GREEN}Step 4: Deploying to Container Apps...${NC}"

# Check if app exists
APP_EXISTS=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  2>/dev/null || echo "not_found")

if [ "$APP_EXISTS" == "not_found" ]; then
    echo -e "${YELLOW}⚠ App does not exist. Creating new Container App...${NC}"
    CREATE_NEW=true
fi

if [ "$CREATE_NEW" = true ]; then
    echo -e "${BLUE}Creating new Container App: ${APP_NAME}${NC}"

    # Get Container Apps Environment
    ENV_NAME=$(az containerapp env list \
      --resource-group $RESOURCE_GROUP \
      --query "[0].name" \
      -o tsv)

    if [ -z "$ENV_NAME" ]; then
        echo -e "${RED}✗ No Container Apps Environment found in resource group${NC}"
        exit 1
    fi

    az containerapp create \
      --name $APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --environment $ENV_NAME \
      --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$VERSION_TAG \
      --target-port 8000 \
      --ingress external \
      --cpu 1.0 \
      --memory 2Gi \
      --min-replicas 1 \
      --max-replicas 3 \
      --env-vars \
        "DATABASE_URL=$DATABASE_URL" \
        "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
        "AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY" \
        "AZURE_OPENAI_DEPLOYMENT_NAME=$AZURE_OPENAI_DEPLOYMENT_NAME" \
        "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
        "MCP_SUPPLIER_DATA_URL=$MCP_SUPPLIER_DATA_URL" \
        "MCP_INVENTORY_MGMT_URL=$MCP_INVENTORY_MGMT_URL" \
        "MCP_FINANCE_DATA_URL=$MCP_FINANCE_DATA_URL" \
        "MCP_ANALYTICS_FORECAST_URL=$MCP_ANALYTICS_FORECAST_URL" \
        "MCP_INTEGRATIONS_URL=$MCP_INTEGRATIONS_URL" \
        "PORT=8000" \
        "LOG_LEVEL=INFO" \
      --registry-server $ACR_NAME.azurecr.io

    echo -e "${GREEN}✓ Container App created!${NC}"
else
    echo -e "${BLUE}Updating existing Container App: ${APP_NAME}${NC}"

    az containerapp update \
      --name $APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$VERSION_TAG \
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
        "MCP_SUPPLIER_DATA_URL=$MCP_SUPPLIER_DATA_URL" \
        "MCP_INVENTORY_MGMT_URL=$MCP_INVENTORY_MGMT_URL" \
        "MCP_FINANCE_DATA_URL=$MCP_FINANCE_DATA_URL" \
        "MCP_ANALYTICS_FORECAST_URL=$MCP_ANALYTICS_FORECAST_URL" \
        "MCP_INTEGRATIONS_URL=$MCP_INTEGRATIONS_URL" \
        "PORT=8000" \
        "LOG_LEVEL=INFO"

    echo -e "${GREEN}✓ Container App updated!${NC}"
fi

# Step 5: Get application URL
echo -e "\n${GREEN}Step 5: Retrieving application URL...${NC}"

BACKEND_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

# Step 6: Health check
echo -e "\n${GREEN}Step 6: Running health check...${NC}"
echo -e "${BLUE}Waiting for app to be ready...${NC}"

sleep 10  # Give app time to start

HEALTH_URL="https://$BACKEND_URL/api/health"
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf "$HEALTH_URL" > /dev/null; then
        echo -e "${GREEN}✓ Health check passed!${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}⚠ Health check failed, retrying ($RETRY_COUNT/$MAX_RETRIES)...${NC}"
            sleep 5
        else
            echo -e "${YELLOW}⚠ Health check failed after $MAX_RETRIES attempts${NC}"
            echo -e "${YELLOW}  App may still be starting up. Check logs if issues persist.${NC}"
        fi
    fi
done

# Step 7: Summary
echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}✓ Backend Deployment Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "\n${GREEN}Backend URL:${NC}"
echo -e "  🌐 https://$BACKEND_URL"
echo -e "\n${GREEN}Test Endpoints:${NC}"
echo -e "  Health:     https://$BACKEND_URL/api/health"
echo -e "  API Docs:   https://$BACKEND_URL/docs"
echo -e "  Products:   https://$BACKEND_URL/products"
echo -e "  Suppliers:  https://$BACKEND_URL/suppliers"
echo -e "  Workflows:  https://$BACKEND_URL/api/workflows/optimize-inventory/stream"

echo -e "\n${GREEN}Quick Tests:${NC}"
echo -e "  curl https://$BACKEND_URL/api/health"
echo -e "  curl https://$BACKEND_URL/products?limit=5"

echo -e "\n${GREEN}View Logs:${NC}"
echo -e "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"

echo -e "\n${GREEN}Deployment Info:${NC}"
echo -e "  Version: $VERSION_TAG"
echo -e "  Image: $ACR_NAME.azurecr.io/$IMAGE_NAME:$VERSION_TAG"
echo -e "  Resources: 1.0 CPU, 2Gi RAM"
echo -e "  Replicas: 1-3 (auto-scaling)"

echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}Next: Deploy frontend with this backend URL${NC}"
echo -e "${BLUE}================================================${NC}"

# Save backend URL for frontend deployment
echo "export BACKEND_URL=https://$BACKEND_URL" > .backend-url.sh
echo -e "\n${GREEN}✓ Backend URL saved to .backend-url.sh${NC}"
