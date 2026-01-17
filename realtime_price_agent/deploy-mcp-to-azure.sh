#!/bin/bash
set -e  # Exit on error

# ============================================================================
# MCP Servers - Azure Deployment Script
# Deploys all 5 MCP servers to Azure Container Apps
# Compatible with macOS default bash (3.2+)
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
LOCATION="eastus"
ENVIRONMENT_NAME="supply-chain-env"

# MCP Server Configuration (bash 3.2 compatible)
# Format: server-name:port:directory_name
MCP_SERVERS="supplier-data:3001:supplier_data inventory-mgmt:3002:inventory_management finance-data:3003:finance_data analytics-forecast:3004:analytics_forecast integrations:3005:integrations"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  MCP Servers Azure Deployment${NC}"
echo -e "${BLUE}  Deploying 5 specialized MCP servers${NC}"
echo -e "${BLUE}================================================${NC}"

# Step 1: Check prerequisites
echo -e "\n${GREEN}Step 1: Checking prerequisites...${NC}"

# Check if logged into Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}❌ Not logged into Azure. Please run: az login${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f mcp_servers/.env ]; then
    echo -e "${YELLOW}⚠ Warning: mcp_servers/.env file not found${NC}"
    echo "Creating from template..."
    if [ -f .env ]; then
        # Copy main .env to mcp_servers
        cp .env mcp_servers/.env
    fi
fi

# Load environment variables
if [ -f mcp_servers/.env ]; then
    export $(cat mcp_servers/.env | grep -v '^#' | xargs)
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"

# Step 2: Create Container App Environment if it doesn't exist
echo -e "\n${GREEN}Step 2: Setting up Container App Environment...${NC}"

if ! az containerapp env show --name $ENVIRONMENT_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "Creating new environment: $ENVIRONMENT_NAME"
    az containerapp env create \
        --name $ENVIRONMENT_NAME \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION
    echo -e "${GREEN}✓ Environment created${NC}"
else
    echo -e "${GREEN}✓ Environment already exists${NC}"
fi

# Step 3: Build and deploy each MCP server
echo -e "\n${GREEN}Step 3: Building and deploying MCP servers...${NC}"

for server_config in $MCP_SERVERS; do
    # Parse server:port:directory
    SERVER=$(echo $server_config | cut -d: -f1)
    PORT=$(echo $server_config | cut -d: -f2)
    SERVER_DIR=$(echo $server_config | cut -d: -f3)

    APP_NAME="mcp-${SERVER}"
    IMAGE_NAME="mcp-${SERVER}"

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Deploying: ${SERVER} (Port: ${PORT})${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Build image in Azure (build context is project root)
    echo -e "${GREEN}Building image in ACR...${NC}"
    az acr build \
        --registry $ACR_NAME \
        --image $IMAGE_NAME:latest \
        --file mcp_servers/${SERVER_DIR}/Dockerfile \
        --platform linux/amd64 \
        .

    echo -e "${GREEN}✓ Image built: $IMAGE_NAME:latest${NC}"

    # Check if container app exists
    if az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
        echo "Updating existing container app: $APP_NAME"
        az containerapp update \
            --name $APP_NAME \
            --resource-group $RESOURCE_GROUP \
            --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
            --set-env-vars \
                "DATABASE_URL=${DATABASE_URL}" \
                "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
                "AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}" \
                "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME}" \
                "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}" \
                "PORT=${PORT}"
    else
        echo "Creating new container app: $APP_NAME"
        az containerapp create \
            --name $APP_NAME \
            --resource-group $RESOURCE_GROUP \
            --environment $ENVIRONMENT_NAME \
            --image $ACR_NAME.azurecr.io/$IMAGE_NAME:latest \
            --target-port $PORT \
            --ingress external \
            --registry-server $ACR_NAME.azurecr.io \
            --cpu 0.5 \
            --memory 1Gi \
            --min-replicas 0 \
            --max-replicas 2 \
            --env-vars \
                "DATABASE_URL=${DATABASE_URL}" \
                "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
                "AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}" \
                "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME}" \
                "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}" \
                "PORT=${PORT}"
    fi

    echo -e "${GREEN}✓ Deployed: $APP_NAME${NC}"
done

# Step 4: Get all URLs
echo -e "\n${GREEN}Step 4: Getting MCP server URLs...${NC}"

echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "\n${GREEN}Your MCP servers are now live:${NC}\n"

# Store URLs in a temp file
URLS_FILE=$(mktemp)

for server_config in $MCP_SERVERS; do
    SERVER=$(echo $server_config | cut -d: -f1)
    APP_NAME="mcp-${SERVER}"

    URL=$(az containerapp show \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --query properties.configuration.ingress.fqdn \
        -o tsv 2>/dev/null || echo "not-deployed")

    if [ "$URL" != "not-deployed" ]; then
        echo "${SERVER}:https://$URL" >> $URLS_FILE
        echo -e "  🔌 ${SERVER}: ${GREEN}https://$URL${NC}"
    fi
done

# Step 5: Generate environment variables for .env
echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}Environment Variables for .env:${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

echo "# MCP Server URLs (Azure)"
while IFS=: read -r server url; do
    VAR_NAME=$(echo "MCP_${server}" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    echo "${VAR_NAME}_URL=${url}"
done < $URLS_FILE

# Step 6: Test MCP servers
echo -e "\n${BLUE}================================================${NC}"
echo -e "${GREEN}Testing MCP Servers:${NC}"
echo -e "${BLUE}================================================${NC}"

while IFS=: read -r server url; do
    echo -ne "\n  Testing ${server}... "

    HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "${url}/" || echo "000")

    if [ "$HEALTH_CHECK" == "200" ]; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${YELLOW}⚠ Status: $HEALTH_CHECK${NC}"
    fi
done < $URLS_FILE

# Clean up
rm -f $URLS_FILE

echo -e "\n${BLUE}================================================${NC}"
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update your .env file with the MCP server URLs above"
echo "2. Redeploy your main app to use the cloud MCP servers"
echo "3. Run: python3 simple_e2e_test.py (update URLs in test first)"
echo -e "${BLUE}================================================${NC}"
