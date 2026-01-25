#!/bin/bash
#
# Supply Chain Agents - Setup & Launch Script
# ============================================
# Prerequisites:
#   - Python 3.11+ installed
#   - PostgreSQL database configured (or Neon connection string)
#   - Environment variables set in .env file
#
# Usage:
#   chmod +x scripts/setup.sh
#   ./scripts/setup.sh
#

set -e

echo "=================================================="
echo "  Supply Chain Agents - Setup Script (uv)"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env 2>/dev/null || true
fi

echo -e "${GREEN}✅ uv $(uv --version | head -1)${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.sample...${NC}"
    if [ -f ".env.sample" ]; then
        cp .env.sample .env
        echo -e "${YELLOW}📝 Please edit .env with your actual credentials before running the app.${NC}"
        echo ""
    else
        echo -e "${RED}❌ .env.sample not found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Check required environment variables
source .env 2>/dev/null || true

missing_vars=0
check_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}❌ Missing: $1${NC}"
        missing_vars=1
    else
        echo -e "${GREEN}✅ $1 is set${NC}"
    fi
}

echo "Checking environment variables..."
echo ""
check_var "DATABASE_URL"
check_var "AZURE_OPENAI_ENDPOINT"
check_var "AZURE_OPENAI_API_KEY"
check_var "AZURE_OPENAI_DEPLOYMENT_NAME"

if [ $missing_vars -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Some environment variables are missing. Please update .env${NC}"
    echo ""
fi

# Install dependencies using uv
echo ""
echo "Installing dependencies with uv..."
uv sync --all-extras

# Check for libomp on macOS (required for XGBoost)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! brew list libomp &>/dev/null 2>&1; then
        echo ""
        echo -e "${YELLOW}⚠️  XGBoost requires libomp on macOS.${NC}"
        echo "   Run: brew install libomp"
        echo ""
    fi
fi

echo ""
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Check if forecasting model exists
if [ -f "realtime_price_agent/agents/demand_forecasting/models/demand_forecaster.pkl" ]; then
    echo -e "${GREEN}✅ Forecasting model found${NC}"
else
    echo -e "${YELLOW}⚠️  Forecasting model not found${NC}"
    echo "   Train the model using: notebooks/demand_forecasting_training.py"
fi

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "To start the application:"
echo ""
echo "  # Start the backend API server"
echo "  cd realtime_price_agent"
echo "  uv run uvicorn main:app --reload --port 8000"
echo ""
echo "  # In another terminal, start the frontend"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "  # Open the dashboard"
echo "  open http://localhost:3000"
echo ""
echo "=================================================="

