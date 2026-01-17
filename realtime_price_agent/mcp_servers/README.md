# MCP Servers for Supply Chain Agents

This directory contains 5 specialized MCP (Model Context Protocol) servers that provide tools for the supply chain AI agents.

## 📁 Architecture

```
mcp_servers/
├── supplier_data/        # Port 3001 - Supplier pricing & comparison
├── inventory_management/ # Port 3002 - Inventory & stock management
├── finance_data/         # Port 3003 - Financial calculations
├── analytics_forecast/   # Port 3004 - Demand forecasting & analytics
├── integrations/         # Port 3005 - External system integrations
├── docker-compose.yml    # Run all servers together
├── test_mcp_servers.py   # Test script
└── README.md             # This file
```

## 🚀 Quick Start

### Local Development

1. **Set environment variables:**
```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
```

2. **Run all MCP servers with Docker Compose:**
```bash
cd mcp_servers
docker-compose up --build
```

3. **Test all servers:**
```bash
python test_mcp_servers.py
```

### Run Individual Server

```bash
cd mcp_servers/inventory_management
pip install -r requirements.txt
python server.py
```

## 📊 MCP Servers Overview

### 1. Supplier Data Server (Port 3001)
**Purpose:** Supplier pricing, reliability, and comparison

**Tools:**
- `get_supplier_prices` - Get current prices from supplier
- `fuzzy_match_product` - Match SKUs across suppliers
- `get_supplier_reliability` - Get quality/delivery metrics
- `compare_suppliers` - Rank suppliers by criteria
- `get_alternative_suppliers` - Find backup suppliers
- `get_supplier_payment_terms` - Get payment terms
- `get_supplier_min_order` - Get minimum order quantities

### 2. Inventory Management Server (Port 3002)
**Purpose:** Inventory levels, stock management, sales velocity

**Tools:**
- `get_product_details` - Get product information
- `get_inventory_levels` - Get current stock levels
- `get_sales_velocity` - Calculate sales rate
- `predict_stockout` - Predict stockout date
- `update_inventory` - Update stock levels
- `get_historical_sales` - Get past sales data
- `get_low_stock_products` - Get products needing reorder

### 3. Finance Data Server (Port 3003)
**Purpose:** Financial calculations, cost analysis, cash management

**Tools:**
- `get_cash_position` - Get available cash
- `calculate_margin_impact` - Calculate profit impact
- `get_product_cost_structure` - Get cost breakdown
- `calculate_payment_terms_value` - Calculate NPV
- `get_accounts_payable` - Get payment obligations
- `convert_currency` - Currency conversion

### 4. Analytics & Forecasting Server (Port 3004)
**Purpose:** Demand forecasting, trend analysis, predictions

**Tools:**
- `forecast_demand` - ML-based demand prediction
- `analyze_seasonality` - Detect seasonal patterns
- `get_weather_forecast` - Get weather data
- `get_local_events` - Get events calendar
- `detect_trends` - Analyze sales trends
- `predict_stockouts_batch` - Batch stockout predictions

### 5. Integrations Server (Port 3005)
**Purpose:** External system integrations (EDI, email, APIs)

**Tools:**
- `send_purchase_order_edi` - Send PO via EDI
- `send_purchase_order_api` - Send PO via API
- `send_purchase_order_email` - Send PO via email
- `send_email` - Send notification email
- `sync_amazon_prices` - Sync prices from Amazon API

## 🔌 MCP Protocol

All servers implement the MCP protocol with two main endpoints:

### 1. List Tools
```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

### 2. Call Tool
```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "get_supplier_prices",
      "arguments": {
        "supplier_name": "Amazon",
        "sku_list": ["B001ABC123", "B002XYZ789"]
      }
    }
  }'
```

## 🧪 Testing

### Test All Servers
```bash
python test_mcp_servers.py
```

### Test Individual Server Health
```bash
curl http://localhost:3001/health
```

### Test Tool Functionality
```bash
# Example: Test inventory server
curl -X POST http://localhost:3002/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "get_low_stock_products",
      "arguments": {"limit": 10}
    }
  }'
```

## 🐳 Docker Deployment

### Build All Images
```bash
docker-compose build
```

### Run All Servers
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f
```

### Stop All Servers
```bash
docker-compose down
```

## ☁️ Azure Deployment

Each MCP server can be deployed to Azure Container Apps:

```bash
# Deploy inventory server
az containerapp create \
  --name mcp-inventory-mgmt \
  --resource-group imaginecup2026 \
  --image <your-registry>/mcp-inventory-mgmt:latest \
  --target-port 3002 \
  --ingress external \
  --env-vars DATABASE_URL=<connection-string>
```

See main deployment guide for full Azure setup.

## 📝 Development

### Adding a New Tool

1. Add tool definition to `TOOLS` list in server.py:
```python
{
    "name": "my_new_tool",
    "description": "What this tool does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
}
```

2. Implement tool in `execute_tool` function:
```python
elif tool_name == "my_new_tool":
    param1 = arguments.get("param1")
    # Implementation here
    return {"result": "..."}
```

### Testing Changes

1. Restart the server
2. Run test script: `python test_mcp_servers.py`
3. Test specific tool with curl

## 🔧 Troubleshooting

### Server Won't Start
- Check DATABASE_URL is set correctly
- Verify port is not already in use: `lsof -i :3001`
- Check logs: `docker-compose logs <service-name>`

### Tools Not Working
- Verify database connection
- Check agent instructions match tool names
- Validate input schema matches what agent sends

### Slow Performance
- Check database query performance
- Consider caching frequently accessed data
- Monitor with health endpoints

## 📚 References

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
