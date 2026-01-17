#!/bin/bash
set -e  # Exit on error

# ============================================================================
# SupplyMind - Complete Deployment Script
# Orchestrates deployment of both frontend and backend containers
# ============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE=".env"
BACKEND_SCRIPT="./deploy-backend.sh"
FRONTEND_SCRIPT="./deploy-frontend.sh"

# Parse command line arguments
SKIP_BACKEND=false
SKIP_FRONTEND=false
FRONTEND_ONLY=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-backend)
      SKIP_BACKEND=true
      shift
      ;;
    --skip-frontend)
      SKIP_FRONTEND=true
      shift
      ;;
    --frontend-only)
      FRONTEND_ONLY=true
      SKIP_BACKEND=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --skip-backend      Skip backend deployment"
      echo "  --skip-frontend     Skip frontend deployment"
      echo "  --frontend-only     Deploy only frontend (using existing backend)"
      echo "  --help              Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

clear

echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║                                                           ║${NC}"
echo -e "${BOLD}${BLUE}║              SupplyMind Deployment Manager                ║${NC}"
echo -e "${BOLD}${BLUE}║                                                           ║${NC}"
echo -e "${BOLD}${BLUE}║  Automated deployment of frontend and backend containers ║${NC}"
echo -e "${BOLD}${BLUE}║                                                           ║${NC}"
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Pre-flight checks
echo -e "${BOLD}${BLUE}[1/6] Pre-flight Checks${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}✗ Azure CLI not found${NC}"
    echo -e "${YELLOW}Install: https://aka.ms/InstallAzureCLI${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Azure CLI installed${NC}"

# Check login status
if ! az account show &> /dev/null; then
    echo -e "${RED}✗ Not logged in to Azure${NC}"
    echo -e "${YELLOW}Run: az login${NC}"
    exit 1
fi

ACCOUNT_NAME=$(az account show --query user.name -o tsv)
echo -e "${GREEN}✓ Logged in as: ${ACCOUNT_NAME}${NC}"

# Check .env file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ .env file not found: $ENV_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Environment file found${NC}"

# Check scripts exist
if [ ! -f "$BACKEND_SCRIPT" ]; then
    echo -e "${RED}✗ Backend deployment script not found: $BACKEND_SCRIPT${NC}"
    exit 1
fi

if [ ! -f "$FRONTEND_SCRIPT" ]; then
    echo -e "${RED}✗ Frontend deployment script not found: $FRONTEND_SCRIPT${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Deployment scripts found${NC}"

# Step 2: Show deployment plan
echo ""
echo -e "${BOLD}${BLUE}[2/6] Deployment Plan${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

if [ "$SKIP_BACKEND" = false ]; then
    echo -e "${GREEN}✓ Backend:  Will be deployed${NC}"
else
    echo -e "${YELLOW}⊘ Backend:  Skipped${NC}"
fi

if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${GREEN}✓ Frontend: Will be deployed${NC}"
else
    echo -e "${YELLOW}⊘ Frontend: Skipped${NC}"
fi

if [ "$FRONTEND_ONLY" = true ]; then
    echo -e "${YELLOW}ℹ Mode: Frontend-only deployment${NC}"
fi

# Confirmation
echo ""
echo -e "${YELLOW}This will deploy to Azure Container Apps.${NC}"
echo -e "${YELLOW}Continue? (y/n)${NC}"
read -r CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Start deployment timer
START_TIME=$(date +%s)

# Step 3: Deploy Backend
if [ "$SKIP_BACKEND" = false ]; then
    echo ""
    echo -e "${BOLD}${BLUE}[3/6] Deploying Backend${NC}"
    echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

    if bash "$BACKEND_SCRIPT"; then
        echo -e "${GREEN}✓ Backend deployment successful${NC}"

        # Load backend URL
        if [ -f ".backend-url.sh" ]; then
            source .backend-url.sh
            echo -e "${GREEN}✓ Backend URL captured: ${BACKEND_URL}${NC}"
        else
            echo -e "${RED}✗ Failed to capture backend URL${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Backend deployment failed${NC}"
        exit 1
    fi
else
    echo ""
    echo -e "${BOLD}${BLUE}[3/6] Deploying Backend${NC}"
    echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}⊘ Skipped${NC}"

    # Try to load existing backend URL
    if [ -f ".backend-url.sh" ]; then
        source .backend-url.sh
        echo -e "${GREEN}✓ Using existing backend URL: ${BACKEND_URL}${NC}"
    else
        echo -e "${RED}✗ Backend URL not found. Cannot deploy frontend.${NC}"
        echo -e "${YELLOW}Run without --skip-backend first, or manually create .backend-url.sh${NC}"
        exit 1
    fi
fi

# Step 4: Deploy Frontend
if [ "$SKIP_FRONTEND" = false ]; then
    echo ""
    echo -e "${BOLD}${BLUE}[4/6] Deploying Frontend${NC}"
    echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

    if bash "$FRONTEND_SCRIPT" --backend-url "$BACKEND_URL"; then
        echo -e "${GREEN}✓ Frontend deployment successful${NC}"
    else
        echo -e "${RED}✗ Frontend deployment failed${NC}"
        exit 1
    fi
else
    echo ""
    echo -e "${BOLD}${BLUE}[4/6] Deploying Frontend${NC}"
    echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}⊘ Skipped${NC}"
fi

# Step 5: Retrieve URLs
echo ""
echo -e "${BOLD}${BLUE}[5/6] Retrieving Application URLs${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

BACKEND_FQDN=$(az containerapp show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query properties.configuration.ingress.fqdn \
  -o tsv 2>/dev/null || echo "not_deployed")

FRONTEND_FQDN=$(az containerapp show \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --query properties.configuration.ingress.fqdn \
  -o tsv 2>/dev/null || echo "not_deployed")

if [ "$BACKEND_FQDN" != "not_deployed" ]; then
    echo -e "${GREEN}✓ Backend:  https://${BACKEND_FQDN}${NC}"
else
    echo -e "${YELLOW}⊘ Backend:  Not deployed${NC}"
fi

if [ "$FRONTEND_FQDN" != "not_deployed" ]; then
    echo -e "${GREEN}✓ Frontend: https://${FRONTEND_FQDN}${NC}"
else
    echo -e "${YELLOW}⊘ Frontend: Not deployed${NC}"
fi

# Step 6: Health Checks
echo ""
echo -e "${BOLD}${BLUE}[6/6] Running Health Checks${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

HEALTH_PASSED=true

# Backend health check
if [ "$BACKEND_FQDN" != "not_deployed" ]; then
    if curl -sf "https://${BACKEND_FQDN}/api/health" > /dev/null; then
        echo -e "${GREEN}✓ Backend health check passed${NC}"
    else
        echo -e "${RED}✗ Backend health check failed${NC}"
        HEALTH_PASSED=false
    fi
fi

# Frontend health check
if [ "$FRONTEND_FQDN" != "not_deployed" ]; then
    if curl -sf "https://${FRONTEND_FQDN}" > /dev/null; then
        echo -e "${GREEN}✓ Frontend health check passed${NC}"
    else
        echo -e "${RED}✗ Frontend health check failed${NC}"
        HEALTH_PASSED=false
    fi
fi

# End-to-end connectivity test
if [ "$FRONTEND_FQDN" != "not_deployed" ] && [ "$BACKEND_FQDN" != "not_deployed" ]; then
    if curl -sf "https://${FRONTEND_FQDN}/api/proxy/api/health" > /dev/null; then
        echo -e "${GREEN}✓ Frontend-to-Backend connectivity verified${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend-to-Backend connectivity test failed${NC}"
        echo -e "${YELLOW}  Check that frontend has correct backend URL${NC}"
        HEALTH_PASSED=false
    fi
fi

# Calculate deployment time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Final Summary
echo ""
echo -e "${BOLD}${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
if [ "$HEALTH_PASSED" = true ]; then
    echo -e "${BOLD}${GREEN}║               ✓ DEPLOYMENT SUCCESSFUL                     ║${NC}"
else
    echo -e "${BOLD}${YELLOW}║            ⚠ DEPLOYMENT COMPLETED WITH WARNINGS          ║${NC}"
fi
echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Deployment Time:${NC} ${MINUTES}m ${SECONDS}s"
echo ""

if [ "$BACKEND_FQDN" != "not_deployed" ]; then
    echo -e "${BOLD}${GREEN}Backend Application:${NC}"
    echo -e "  🌐 URL:        https://${BACKEND_FQDN}"
    echo -e "  📊 Health:     https://${BACKEND_FQDN}/api/health"
    echo -e "  📖 API Docs:   https://${BACKEND_FQDN}/docs"
    echo ""
fi

if [ "$FRONTEND_FQDN" != "not_deployed" ]; then
    echo -e "${BOLD}${GREEN}Frontend Application:${NC}"
    echo -e "  🌐 URL:        https://${FRONTEND_FQDN}"
    echo -e "  🔗 Connects:   https://${BACKEND_FQDN}"
    echo ""
fi

echo -e "${BOLD}Quick Commands:${NC}"
echo -e "  Test backend:   curl https://${BACKEND_FQDN}/api/health"
echo -e "  Test frontend:  curl https://${FRONTEND_FQDN}"
echo -e "  Backend logs:   az containerapp logs show --name supplymind-backend --resource-group ImagineCup --follow"
echo -e "  Frontend logs:  az containerapp logs show --name supplymind-frontend --resource-group ImagineCup --follow"
echo ""

echo -e "${BOLD}${GREEN}Next Steps:${NC}"
echo -e "  1. Open https://${FRONTEND_FQDN} in your browser"
echo -e "  2. Test the supply chain optimization workflow"
echo -e "  3. Monitor logs for any issues"
echo -e "  4. Set up custom domain (optional)"
echo ""

if [ "$HEALTH_PASSED" = false ]; then
    echo -e "${YELLOW}⚠ Some health checks failed. Check the logs for details.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All systems operational${NC}"
echo ""
