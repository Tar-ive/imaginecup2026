#!/bin/bash
# SupplyMind E2E Health Check Script
# Tests all services: Backend, Frontend, and MCP Servers

echo "🧪 SupplyMind E2E Health Check"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

failed=0
total=0

check_endpoint() {
  local name=$1
  local url=$2
  ((total++))
  
  if curl -sf "$url" --max-time 5 > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} $name"
    return 0
  else
    echo -e "${RED}❌${NC} $name - FAILED ($url)"
    ((failed++))
    return 1
  fi
}

echo "Backend API:"
echo "------------"
check_endpoint "Health Check" "http://localhost:8000/api/health"
check_endpoint "Products API" "http://localhost:8000/api/products?limit=1"

echo ""
echo "Frontend:"
echo "---------"
check_endpoint "Next.js App" "http://localhost:3000"

echo ""
echo "MCP Servers:"
echo "------------"
check_endpoint "Supplier Data (3001)" "http://localhost:3001/health"
check_endpoint "Inventory Mgmt (3002)" "http://localhost:3002/health"
check_endpoint "Finance Data (3003)" "http://localhost:3003/health"
check_endpoint "Analytics (3004)" "http://localhost:3004/health"
check_endpoint "Integrations (3005)" "http://localhost:3005/health"

echo ""
echo "=============================="
if [ $failed -eq 0 ]; then
  echo -e "${GREEN}✅ All $total endpoints healthy!${NC}"
  exit 0
else
  echo -e "${RED}❌ $failed of $total endpoint(s) failed${NC}"
  echo ""
  echo -e "${YELLOW}Tips:${NC}"
  echo "  - Backend: cd realtime_price_agent && uvicorn main:app --reload"
  echo "  - Frontend: cd frontend && pnpm dev"
  echo "  - All services: docker-compose up --build"
  exit 1
fi
