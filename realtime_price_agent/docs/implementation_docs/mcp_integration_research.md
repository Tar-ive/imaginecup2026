# MCP Integration & Workflow Architecture Research

## Executive Summary

This document analyzes why the SupplyMind workflow isn't working correctly and provides a clear path to fix it. The issues are configuration-based, not architectural.

---

## Q1: Why "Model Not Loaded" Errors?

### The Problem

```
WARNING:agents.demand_forecasting.model_service:Model not loaded, returning empty forecast for B0B5DM42BQ
```

### Root Cause

The **pickle model file does not exist** in the repository.

```
Expected path: agents/demand_forecasting/models/demand_forecaster.pkl
Actual state:  File does not exist
```

The `DemandForecasterService` looks for a trained model at that path. When not found, it returns empty forecasts with confidence level "none".

### Solution

Either:
1. **Train and commit the model** (requires historical sales data)
2. **Use the Analytics MCP server** for forecasting instead of local pickle

---

## Q2: What is MCP Protocol?

### Simple Explanation

**MCP (Model Context Protocol)** is a standardized HTTP-based protocol for AI agents to call external tools. Think of it as a "REST API specifically designed for AI tool calls."

### Protocol Format

All MCP servers expose a single endpoint: `POST /mcp`

**Two operations:**

1. **List Tools** - Get available tools
```json
{
  "method": "tools/list"
}
```

Response:
```json
{
  "tools": [
    {
      "name": "forecast_demand",
      "description": "ML-based demand prediction",
      "inputSchema": { "type": "object", "properties": {...} }
    }
  ]
}
```

2. **Call Tool** - Execute a tool
```json
{
  "method": "tools/call",
  "params": {
    "name": "forecast_demand",
    "arguments": {
      "sku": "B001ABC123",
      "days_ahead": 7
    }
  }
}
```

Response:
```json
{
  "content": [{ "type": "text", "text": "{...json result...}" }],
  "isError": false
}
```

### Why MCP Over Regular REST?

| Regular REST | MCP |
|--------------|-----|
| Different endpoints per action | Single `/mcp` endpoint |
| Custom authentication | Standardized |
| Varies by service | Consistent across all tools |
| Manual integration per API | Agent framework handles it |

---

## Q3: Can MCP Work with Pickle Models?

**Yes, absolutely.** MCP is just HTTP - it can do anything.

### Current Architecture (Analytics MCP Server)

```
┌──────────────────────────────────────────────────────────────┐
│              analytics_forecast/server.py                     │
│                         Port 3004                             │
│                                                               │
│  POST /mcp ──────► execute_tool("forecast_demand")           │
│                           │                                   │
│                           ▼                                   │
│               DemandForecasterService.get_instance()         │
│                           │                                   │
│                           ▼                                   │
│                   Load demand_forecaster.pkl                  │
│                           │                                   │
│                           ▼                                   │
│                  Return forecast result                       │
└──────────────────────────────────────────────────────────────┘
```

**The MCP server imports the same pickle model code:**
```python
# analytics_forecast/server.py line 34
from agents.demand_forecasting.model_service import DemandForecasterService
```

**Same problem:** If model file doesn't exist, MCP also returns empty forecasts.

---

## Q4: Configuration Issues

### Wrong MCP URLs in config.py

| File | Current (Wrong) | Should Be (Local) | Should Be (Azure) |
|------|-----------------|-------------------|-------------------|
| `agents/config.py` | `http://supplier-data-server:8000` | `http://localhost:3001` | `https://mcp-supplier-data.bluewave-ee01b5af.eastus.azurecontainerapps.io` |
| | `http://inventory-mgmt-server:8001` | `http://localhost:3002` | `https://mcp-inventory-mgmt.bluewave-ee01b5af.eastus.azurecontainerapps.io` |
| | `http://finance-data-server:8002` | `http://localhost:3003` | `https://mcp-finance-data.bluewave-ee01b5af.eastus.azurecontainerapps.io` |
| | `http://analytics-forecast-server:8003` | `http://localhost:3004` | `https://mcp-analytics-forecast.bluewave-ee01b5af.eastus.azurecontainerapps.io` |
| | `http://integrations-server:8004` | `http://localhost:3005` | `https://mcp-integrations.bluewave-ee01b5af.eastus.azurecontainerapps.io` |

### Azure Deployed Services (Already Running)

```
Name                    URL
amazon-api-app          amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io
supply-chain-api-new    supply-chain-api-new.purplepebble-8d2a2163.eastus.azurecontainerapps.io
mcp-supplier-data       mcp-supplier-data.bluewave-ee01b5af.eastus.azurecontainerapps.io
mcp-inventory-mgmt      mcp-inventory-mgmt.bluewave-ee01b5af.eastus.azurecontainerapps.io
mcp-finance-data        mcp-finance-data.bluewave-ee01b5af.eastus.azurecontainerapps.io
mcp-analytics-forecast  mcp-analytics-forecast.bluewave-ee01b5af.eastus.azurecontainerapps.io
mcp-integrations        mcp-integrations.bluewave-ee01b5af.eastus.azurecontainerapps.io
```

---

## Q5: Are Agents Configured Correctly?

### Agent → MCP Tool Creation Flow

```python
# magentic_workflow.py
supplier_tool = self._create_mcp_tool("supplier-data")  # Creates MCPStreamableHTTPTool
inventory_tool = self._create_mcp_tool("inventory-mgmt")
finance_tool = self._create_mcp_tool("finance-data")
analytics_tool = self._create_mcp_tool("analytics-forecast")
integrations_tool = self._create_mcp_tool("integrations")
```

The `_create_mcp_tool()` method:
1. Gets metadata from `tool_registry`
2. Creates `MCPStreamableHTTPTool` with URL from config
3. Returns tool for agent to use

### Current Problem

`tool_config.py` builds URLs like:
```python
f"{settings.mcp_supplier_url}{MCP_API_HTTP_PATH}"
# = "http://supplier-data-server:8000/mcp"  ← WRONG!
```

Should be:
```python
# Local: "http://localhost:3001/mcp"
# Azure: "https://mcp-supplier-data.bluewave-ee01b5af.eastus.azurecontainerapps.io/mcp"
```

---

## Q6: Data Flow - End to End

### Current (Broken) Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           CURRENT (BROKEN)                                  │
│                                                                             │
│  Frontend (Next.js)                                                        │
│       │                                                                     │
│       ▼ GET /api/proxy-stream/api/workflows/optimize-inventory/stream      │
│       │                                                                     │
│  Backend (FastAPI) ────► workflow_service.py                               │
│       │                         │                                           │
│       │                         ▼                                           │
│       │                  forecaster.forecast(asin)  ← DIRECT CALL         │
│       │                         │                                           │
│       │                         ▼                                           │
│       │                  Model not loaded! ← NO PICKLE FILE                │
│       │                         │                                           │
│       │                         ▼                                           │
│       │                  Empty forecast returned                            │
│       │                                                                     │
│       └──► Agents try MCP tools ─────► Wrong URLs ─────► Connection refused│
└────────────────────────────────────────────────────────────────────────────┘
```

### Should Be Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           CORRECT FLOW                                      │
│                                                                             │
│  Frontend (Next.js)                                                        │
│       │                                                                     │
│       ▼ GET /api/workflows/optimize-inventory/stream                       │
│       │                                                                     │
│  Backend (FastAPI)                                                         │
│       │                                                                     │
│       ├──► Agent starts workflow                                           │
│       │         │                                                           │
│       │         ▼                                                           │
│       │    MCPStreamableHTTPTool (analytics-forecast)                      │
│       │         │                                                           │
│       │         ▼ POST /mcp {"method": "tools/call", ...}                  │
│       │         │                                                           │
│       │    MCP Server (port 3004 or Azure URL)                             │
│       │         │                                                           │
│       │         ▼                                                           │
│       │    DemandForecasterService.forecast() ← Model loaded here          │
│       │         │                                                           │
│       │         ▼                                                           │
│       │    Return forecast to agent                                         │
│       │                                                                     │
│       ▼ SSE stream events to frontend                                      │
│                                                                             │
│  Frontend receives and displays results                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Q7: What Output Do Agents Produce?

### Agent Response Format

Agents produce streaming SSE events:

```json
{
  "type": "metadata",
  "event": "AgentMessage",
  "kind": "supply-chain-agents",
  "data": {
    "agent": "PriceMonitoringAgent",
    "message": "Analyzing supplier prices..."
  }
}
```

```json
{
  "type": "content",
  "event": "TextContent",
  "kind": "supply-chain-agents",
  "data": {
    "text": "Based on my analysis, Amazon offers the best price at $4.50/lb..."
  }
}
```

### Frontend Expectations

The frontend `use-workflow-stream.ts` expects:
```typescript
interface WorkflowEvent {
  type: string       // "metadata" | "content" | "error"
  data?: any         // Event payload
  timestamp: number  // Added by frontend
  stage?: string     // Current workflow stage
  progress?: number  // 0-100
  message?: string   // Human readable message
}
```

### Current Gap

The workflow streaming endpoint (`main.py`) sends:
```json
{"event": "start", "message": "Workflow started", "timestamp": 1234}
{"event": "products_loaded", "count": 50, "timestamp": 1235}
{"event": "complete", "result": {...}, "timestamp": 1240}
```

But the **agent chat endpoint** (`/api/chat`) sends the proper agent format.

---

## Summary of Issues

| Issue | Impact | Fix Priority |
|-------|--------|--------------|
| Wrong MCP URLs in config.py | Agents can't connect to MCP | **CRITICAL** |
| No pickle model file | All forecasts return empty | **CRITICAL** |
| workflow_service.py bypasses MCP | Doesn't use agent architecture | HIGH |
| Frontend proxy timeouts | 300s+ wait times | HIGH |
| Missing pending-approvals endpoint | 404 errors | DONE ✓ |

---

## Recommended Fix Order

1. **Fix MCP URLs** in `agents/config.py` (or via .env)
2. **Train and commit** the pickle model (or remove model requirement)
3. **Test MCP servers** are reachable: `curl https://mcp-analytics-forecast.bluewave.../health`
4. **Restart backend** to pick up config changes
5. **Test workflow** end-to-end

---

## Local vs Azure Deployment

### Local Development

```bash
# MCP Servers (via docker-compose)
docker-compose up --build

# Or individual servers
cd mcp_servers/analytics_forecast
python server.py  # Port 3004

# Backend
cd realtime_price_agent
MCP_SUPPLIER_URL=http://localhost:3001 \
MCP_INVENTORY_URL=http://localhost:3002 \
# ... etc
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm dev
```

### Azure Production

```bash
# MCP servers already deployed (bluewave environment)
# Backend already deployed (purplepebble environment)

# Just need to update backend env vars:
az containerapp update --name amazon-api-app -g ImagineCup \
  --set-env-vars \
    MCP_SUPPLIER_URL=https://mcp-supplier-data.bluewave-ee01b5af.eastus.azurecontainerapps.io \
    MCP_INVENTORY_URL=https://mcp-inventory-mgmt.bluewave-ee01b5af.eastus.azurecontainerapps.io \
    MCP_FINANCE_URL=https://mcp-finance-data.bluewave-ee01b5af.eastus.azurecontainerapps.io \
    MCP_ANALYTICS_URL=https://mcp-analytics-forecast.bluewave-ee01b5af.eastus.azurecontainerapps.io \
    MCP_INTEGRATIONS_URL=https://mcp-integrations.bluewave-ee01b5af.eastus.azurecontainerapps.io

# Frontend on Vercel:
# Set NEXT_PUBLIC_API_URL=https://amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io
```

---

## References

- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Azure Container Apps Docs](https://learn.microsoft.com/en-us/azure/container-apps/)
