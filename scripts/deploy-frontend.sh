#!/bin/bash
set -e  # Exit on error

# ============================================================================
# SupplyMind Frontend - Azure Deployment Script
# Deploys Next.js frontend to Azure Container Apps
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
APP_NAME="supplymind-frontend"
IMAGE_NAME="supplymind-frontend"

# Parse command line arguments
BACKEND_URL=""
TAG="latest"
CREATE_NEW=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --backend-url)
      BACKEND_URL="$2"
      shift 2
      ;;
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
echo -e "${BLUE}  SupplyMind Frontend Deployment${NC}"
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

# Check Dockerfile exists
if [ ! -f "frontend/Dockerfile" ]; then
    echo -e "${RED}✗ Dockerfile not found at: frontend/Dockerfile${NC}"
    echo -e "${YELLOW}Please create the frontend Dockerfile first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dockerfile found${NC}"

# Step 2: Get or validate backend URL
echo -e "\n${GREEN}Step 2: Configuring backend URL...${NC}"

# Try to load from saved file if not provided
if [ -z "$BACKEND_URL" ]; then
    if [ -f ".backend-url.sh" ]; then
        source .backend-url.sh
        echo -e "${GREEN}✓ Loaded backend URL from .backend-url.sh${NC}"
    else
        echo -e "${RED}✗ Backend URL not provided and .backend-url.sh not found${NC}"
        echo -e "${YELLOW}Usage: $0 --backend-url https://your-backend-url${NC}"
        echo -e "${YELLOW}Or run deploy-backend.sh first to generate .backend-url.sh${NC}"
        exit 1
    fi
fi

# Validate URL format
if [[ ! "$BACKEND_URL" =~ ^https?:// ]]; then
    echo -e "${RED}✗ Invalid backend URL format: $BACKEND_URL${NC}"
    echo -e "${YELLOW}URL must start with http:// or https://${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend URL: ${BACKEND_URL}${NC}"

# Step 3: Build image in Azure Container Registry
echo -e "\n${GREEN}Step 3: Building Docker image in ACR...${NC}"
echo -e "${BLUE}Building from: frontend/${NC}"
echo -e "${BLUE}Tags: ${VERSION_TAG}, latest${NC}"
echo -e "${BLUE}Backend URL: ${BACKEND_URL}${NC}"

cd frontend

# Build with backend URL as build arg
az acr build \
  --registry $ACR_NAME \
  --image $IMAGE_NAME:$VERSION_TAG \
  --image $IMAGE_NAME:latest \
  --file Dockerfile \
  --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_API_URL=$BACKEND_URL \
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
      --target-port 3000 \
      --ingress external \
      --cpu 0.5 \
      --memory 1Gi \
      --min-replicas 1 \
      --max-replicas 3 \
      --env-vars \
        "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
        "NODE_ENV=production" \
      --registry-server $ACR_NAME.azurecr.io

    echo -e "${GREEN}✓ Container App created!${NC}"
else
    echo -e "${BLUE}Updating existing Container App: ${APP_NAME}${NC}"

    az containerapp update \
      --name $APP_NAME \
      --resource-group $RESOURCE_GROUP \
      --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$VERSION_TAG \
      --cpu 0.5 \
      --memory 1Gi \
      --min-replicas 1 \
      --max-replicas 3 \
      --set-env-vars \
        "NEXT_PUBLIC_API_URL=$BACKEND_URL" \
        "NODE_ENV=production"

    echo -e "${GREEN}✓ Container App updated!${NC}"
fi

# Step 5: Get application URL
echo -e "\n${GREEN}Step 5: Retrieving application URL...${NC}"

FRONTEND_URL=$(az containerapp show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

# Step 6: Health check
echo -e "\n${GREEN}Step 6: Running health check...${NC}"
echo -e "${BLUE}Waiting for app to be ready...${NC}"

sleep 15  # Next.js takes a bit longer to start

MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf "https://$FRONTEND_URL" > /dev/null; then
        echo -e "${GREEN}✓ Frontend is accessible!${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}⚠ Frontend not ready, retrying ($RETRY_COUNT/$MAX_RETRIES)...${NC}"
            sleep 5
        else
            echo -e "${YELLOW}⚠ Frontend not responding after $MAX_RETRIES attempts${NC}"
            echo -e "${YELLOW}  App may still be starting up. Check logs if issues persist.${NC}"
        fi
    fi
done

# Step 7: Test backend connectivity
echo -e "\n${GREEN}Step 7: Testing frontend-to-backend connectivity...${NC}"

if curl -sf "https://$FRONTEND_URL/api/proxy/api/health" > /dev/null; then
    echo -e "${GREEN}✓ Frontend can reach backend!${NC}"
else
    echo -e "${YELLOW}⚠ Frontend-to-backend connection test failed${NC}"
    echo -e "${YELLOW}  This may be expected if backend is not running.${NC}"
fi

# Step 8: Summary
echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}✓ Frontend Deployment Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "\n${GREEN}Frontend URL:${NC}"
echo -e "  🌐 https://$FRONTEND_URL"
echo -e "\n${GREEN}Backend URL:${NC}"
echo -e "  🔗 $BACKEND_URL"

echo -e "\n${GREEN}Test Application:${NC}"
echo -e "  Open in browser: https://$FRONTEND_URL"
echo -e "  Test proxy:      curl https://$FRONTEND_URL/api/proxy/api/health"

echo -e "\n${GREEN}View Logs:${NC}"
echo -e "  az containerapp logs show --name $APP_NAME --resource-group $RESOURCE_GROUP --follow"

echo -e "\n${GREEN}Deployment Info:${NC}"
echo -e "  Version: $VERSION_TAG"
echo -e "  Image: $ACR_NAME.azurecr.io/$IMAGE_NAME:$VERSION_TAG"
echo -e "  Resources: 0.5 CPU, 1Gi RAM"
echo -e "  Replicas: 1-3 (auto-scaling)"

echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}Your SupplyMind application is now live!${NC}"
echo -e "${BLUE}================================================${NC}"
