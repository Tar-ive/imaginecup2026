#!/bin/bash

# Start MCP Servers for Negotiation & AP2 Testing
# This script starts both supplier and finance MCP servers

echo "=================================================="
echo "Starting MCP Servers for SupplyMind"
echo "=================================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Killing process on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null
    sleep 1
}

# Check and kill existing servers
echo -e "${BLUE}Checking for existing MCP servers...${NC}"

if check_port 3001; then
    echo "  Port 3001 (Supplier MCP) is in use"
    kill_port 3001
fi

if check_port 3003; then
    echo "  Port 3003 (Finance MCP) is in use"
    kill_port 3003
fi

echo ""

# Start Supplier MCP Server
echo -e "${BLUE}Starting Supplier MCP Server (port 3001)...${NC}"
cd "$SCRIPT_DIR/mcp_servers/supplier_data"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start server in background
nohup python server.py > ../../logs/supplier_mcp.log 2>&1 &
SUPPLIER_PID=$!
echo -e "${GREEN}✓ Supplier MCP started (PID: $SUPPLIER_PID)${NC}"
echo "  Logs: $SCRIPT_DIR/logs/supplier_mcp.log"

# Wait for server to start
sleep 2

# Start Finance MCP Server
echo ""
echo -e "${BLUE}Starting Finance MCP Server (port 3003)...${NC}"
cd "$SCRIPT_DIR/mcp_servers/finance_data"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start server in background
nohup python server.py > ../../logs/finance_mcp.log 2>&1 &
FINANCE_PID=$!
echo -e "${GREEN}✓ Finance MCP started (PID: $FINANCE_PID)${NC}"
echo "  Logs: $SCRIPT_DIR/logs/finance_mcp.log"

# Wait for server to start
sleep 2

# Verify servers are running
echo ""
echo -e "${BLUE}Verifying servers...${NC}"

if check_port 3001; then
    echo -e "${GREEN}✓ Supplier MCP Server is running on port 3001${NC}"
else
    echo -e "${RED}✗ Supplier MCP Server failed to start${NC}"
fi

if check_port 3003; then
    echo -e "${GREEN}✓ Finance MCP Server is running on port 3003${NC}"
else
    echo -e "${RED}✗ Finance MCP Server failed to start${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}MCP Servers Started Successfully!${NC}"
echo "=================================================="
echo ""
echo "Supplier MCP: http://localhost:3001/mcp"
echo "Finance MCP:  http://localhost:3003/mcp"
echo ""
echo "To test the tools, run:"
echo "  cd $SCRIPT_DIR"
echo "  python test_negotiation_tools.py"
echo ""
echo "To view logs:"
echo "  tail -f $SCRIPT_DIR/logs/supplier_mcp.log"
echo "  tail -f $SCRIPT_DIR/logs/finance_mcp.log"
echo ""
echo "To stop servers:"
echo "  kill $SUPPLIER_PID $FINANCE_PID"
echo ""
