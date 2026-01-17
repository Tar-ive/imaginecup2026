# Resolved Deployment Plan: Full Supply Chain API

## Why In-Place Update vs Blue-Green?

### My Initial Recommendation: In-Place Update

I initially suggested in-place update for these reasons:

| Factor | In-Place Update | Blue-Green |
|--------|-----------------|------------|
| **Speed** | ✅ 10 min | ⏱️ 30+ min (new resources) |
| **Cost** | ✅ No extra resources | 💰 2x Container Apps until cutover |
| **Complexity** | ✅ Simple `az containerapp update` | ⚙️ New app, DNS/traffic config |
| **URL Preservation** | ✅ Same URL | ❌ Different URL initially |
| **Rollback** | ✅ `--image v5` | ✅ Point traffic back |

### When You SHOULD Use Blue-Green Instead

> [!IMPORTANT]
> **Use Blue-Green if ANY of these are true:**

1. **Production Dependencies Exist**
   - Other services call the old `/products` or `/products/{asin}` endpoints
   - You need to test the new API without affecting existing consumers
   
2. **Zero-Downtime Required**
   - Regulatory or SLA requirements for uptime
   - Users actively using the legacy API during deployment

3. **Significant Schema Changes**
   - Database migrations that could break rollback
   - API contract changes that could break clients

4. **Risk Appetite is Low**
   - This is a demo/hackathon → In-place is fine
   - This is production with paying customers → Blue-Green

### Your Situation Assessment

| Question | Answer | Implication |
|----------|--------|-------------|
| Is the legacy API in active use? | Probably not (just CSV demo) | In-place OK |
| Are other services calling it? | Unknown - you'd need to verify | If yes → Blue-Green |
| Is this production? | Hackathon/ImagineCup project | In-place OK |
| Can you afford brief downtime? | Likely yes | In-place OK |

---

## Recommended: Blue-Green with Traffic Splitting

Given your question, let's do **Blue-Green properly** using Azure Container Apps' built-in revision management:

### How Azure Container Apps Handles This

Azure Container Apps has **built-in blue-green support** via revisions:

```
┌─────────────────────────────────────────────────────────────────┐
│                   AZURE CONTAINER APPS REVISIONS                │
│                                                                 │
│   ┌──────────────────────┐    ┌──────────────────────┐         │
│   │  Revision: v5        │    │  Revision: v6        │         │
│   │  (Legacy API)        │    │  (Full API)          │         │
│   │  Image: amazon-api:v5│    │  Image: amazon-api:v6│         │
│   └──────────────────────┘    └──────────────────────┘         │
│              │                           │                      │
│              │ 0% traffic                │ 100% traffic         │
│              │ (after cutover)           │ (after cutover)      │
│              ▼                           ▼                      │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  Single URL: amazon-api-app.purplepebble-*.azurecontain │  │
│   │  apps.io                                                 │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Blue-Green Deployment Steps

#### Step 1: Build and Push v6

```bash
# Login to ACR
az acr login --name imaginecupreg999

# Build with v6 tag
docker build -t imaginecupreg999.azurecr.io/amazon-api:v6 \
  -f Dockerfile .

# Push to registry
docker push imaginecupreg999.azurecr.io/amazon-api:v6
```

#### Step 2: Add Required Secrets

```bash
# Add DATABASE_URL secret (your Neon PostgreSQL connection)
az containerapp secret set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --secrets "database-url=postgresql://user:pass@host/db"

# Add Azure OpenAI key
az containerapp secret set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --secrets "azure-openai-key=YOUR_OPENAI_KEY"
```

#### Step 3: Create New Revision (Blue-Green)

```bash
# Create new revision with v6 image but 0% traffic initially
az containerapp revision copy \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/amazon-api:v6 \
  --set-env-vars \
    "DATABASE_URL=secretref:database-url" \
    "AZURE_OPENAI_ENDPOINT=https://Imagine-Cup-TeamCosmos.openai.azure.com" \
    "AZURE_OPENAI_API_KEY=secretref:azure-openai-key" \
    "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini" \
    "AZURE_OPENAI_API_VERSION=2024-02-15-preview" \
    "LOG_LEVEL=INFO"
```

#### Step 4: Test New Revision Independently

```bash
# Get the new revision name
az containerapp revision list \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --query "[].name" -o tsv

# The new revision has its own URL for testing:
# amazon-api-app--<revision-suffix>.purplepebble-*.azurecontainerapps.io

# Test health
curl https://amazon-api-app--<new-revision>.purplepebble-8d2a2163.eastus.azurecontainerapps.io/api/health
```

#### Step 5: Gradual Traffic Cutover

```bash
# Send 10% to new revision (canary)
az containerapp ingress traffic set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision-weight amazon-api-app--0000003=10 amazon-api-app--0000004=90

# If tests pass, send 50%
az containerapp ingress traffic set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision-weight amazon-api-app--0000003=50 amazon-api-app--0000004=50

# Full cutover to new revision
az containerapp ingress traffic set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision-weight amazon-api-app--0000004=100
```

#### Step 6: Deactivate Old Revision (Optional)

```bash
# Deactivate old revision (keeps it for rollback)
az containerapp revision deactivate \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision amazon-api-app--0000003
```

### Rollback (If Needed)

```bash
# Instantly route all traffic back to old revision
az containerapp ingress traffic set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision-weight amazon-api-app--0000003=100
```

---

## MCP Server Deployment with Telemetry

### Current MCP Server Architecture

Your codebase expects these MCP servers:

| Server ID | Name | Expected URL | Tools |
|-----------|------|--------------|-------|
| `SUPPLIER` | Supplier Data | `http://supplier-data-server:8000/mcp` | get_suppliers, get_supplier_products |
| `INVENTORY` | Inventory Mgmt | `http://inventory-mgmt-server:8001/mcp` | get_stock_levels, update_inventory |
| `FINANCE` | Finance Data | `http://finance-data-server:8002/mcp` | get_exchange_rates, get_budget |
| `ANALYTICS` | Analytics Forecast | `http://analytics-forecast-server:8003/mcp` | run_prophet_forecast |
| `INTEGRATIONS` | Integrations | `http://integrations-server:8004/mcp` | send_email, create_po |

### Do You Need MCPs for Initial Deployment?

> [!TIP]
> **NO!** The core API works without MCP servers.

Your FastAPI backend has direct database access and can:
- Serve inventory data from PostgreSQL
- Run forecasting with XGBoost model
- Create purchase orders

MCPs are **optional** - they provide:
- Protocol-standard tool interface for agents
- Separation of concerns for external integrations
- Ability to swap implementations without changing agent code

### Deploying Custom MCPs with OpenTelemetry

Based on [/docs/mcp_deploy.md](file:///Users/tarive/imaginecup/azure-agents/realtime_price_agent/docs/mcp_deploy.md), here's how to deploy your supply chain MCPs:

#### Option A: Use the azd Template Pattern

```bash
# 1. Create MCP server directory
mkdir -p mcp-servers/supplier-data

# 2. Create Dockerfile for MCP server
cat > mcp-servers/supplier-data/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install OpenTelemetry for observability
RUN pip install opentelemetry-api opentelemetry-sdk \
                opentelemetry-exporter-otlp-proto-grpc \
                opentelemetry-instrumentation-fastapi

COPY . .
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 3. Create MCP server with OpenTelemetry
cat > mcp-servers/supplier-data/server.py << 'EOF'
from fastapi import FastAPI
from mcp.server.fastapi import add_mcp_routes
from mcp import Tool
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup OpenTelemetry
provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317")
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI()

# MCP Tools
@app.tool()
async def get_suppliers():
    """Get all suppliers."""
    with tracer.start_as_current_span("get_suppliers"):
        # Your implementation
        return {"suppliers": [...]}

add_mcp_routes(app, path="/mcp")
EOF
```

#### Option B: Deploy to Same Container Apps Environment

```bash
# Build MCP server image
docker build -t imaginecupreg999.azurecr.io/mcp-supplier:v1 \
  -f mcp-servers/supplier-data/Dockerfile \
  mcp-servers/supplier-data/

docker push imaginecupreg999.azurecr.io/mcp-supplier:v1

# Deploy as new Container App in same environment
az containerapp create \
  --name mcp-supplier-server \
  --resource-group ImagineCup \
  --environment imagine-cup-env \
  --image imaginecupreg999.azurecr.io/mcp-supplier:v1 \
  --target-port 8000 \
  --ingress internal \
  --min-replicas 1 \
  --set-env-vars \
    "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317" \
    "OTEL_SERVICE_NAME=mcp-supplier-server"
```

#### Connecting MCPs to Main API

Once MCP servers are deployed, update your Container App:

```bash
az containerapp update \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --set-env-vars \
    "MCP_SUPPLIER_URL=https://mcp-supplier-server.internal.eastus.azurecontainerapps.io" \
    "MCP_INVENTORY_URL=https://mcp-inventory-server.internal.eastus.azurecontainerapps.io"
```

### OpenTelemetry Integration

Your infrastructure already has Application Insights (`imaginecup7299870127`). To enable telemetry:

```bash
# Get the Application Insights connection string
az monitor app-insights component show \
  --app imaginecup7299870127 \
  --resource-group ImagineCup \
  --query connectionString -o tsv

# Add to your Container App
az containerapp update \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --set-env-vars \
    "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;..."
```

Then in your FastAPI code (already in implementation plan):

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Export to Azure Monitor
exporter = AzureMonitorTraceExporter.from_connection_string(
    os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)
```

---

## Summary: Recommended Deployment Order

1. **Phase 1: Deploy Main API** (Today)
   - Build and push v6 image
   - Add secrets (DATABASE_URL, AZURE_OPENAI_KEY)
   - Blue-green deploy with traffic splitting
   - Verify `/api/health`, `/docs`, dashboard works

2. **Phase 2: Add OpenTelemetry** (Next)
   - Connect to existing Application Insights
   - Add instrumentation code
   - Deploy updated image

3. **Phase 3: Deploy MCP Servers** (Optional/Later)
   - Create MCP server containers
   - Deploy to same Container Apps environment
   - Update main API with MCP URLs
   - Enable agent tool calls

---

## Pre-Deployment Checklist

- [ ] **DATABASE_URL ready?** (Neon PostgreSQL connection string)
- [ ] **Azure OpenAI key ready?** (from Imagine-Cup-TeamCosmos)
- [ ] **Docker build tested locally?** (`docker build .`)
- [ ] **Which OpenAI deployment?** (gpt-4o-mini or gpt-5-mini)
- [ ] **MCP servers needed for v1?** (Recommend: No, add later)