# Supply Chain Agents

A **programmed workflow automation system** for supply chain management, powered by [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) and the **Magentic Orchestration** pattern.

> ⚠️ **This is NOT a chat application.** This is a dashboard-driven automation system where workflows are triggered by buttons, not conversations.

## 🎯 What This System Does

This is an AI-powered supply chain automation system with **programmed workflows** triggered from a dashboard. When a user clicks a button (e.g., "Optimize Inventory"), the agents execute a predefined sequence:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DASHBOARD UI                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  OPTIMIZE   │  │   REORDER   │  │   PRICE     │                 │
│  │  INVENTORY  │  │    LOW      │  │   ALERT     │                 │
│  │   [BUTTON]  │  │   STOCK     │  │   REVIEW    │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
└─────────┼────────────────┼────────────────┼────────────────────────┘
          │                │                │
          ▼                ▼                ▼
    ┌───────────────────────────────────────────────────────────┐
    │              WORKFLOW ORCHESTRATION ENGINE                 │
    │        (Agents execute programmed sequences)               │
    └───────────────────────────────────────────────────────────┘
```

## 🔄 Programmed Workflow Example: "Optimize Inventory"

When the user clicks **"Optimize Inventory"**, this automated sequence runs:

```
STEP 1: Get Forecasted Demand
         │
         │  DemandForecastingAgent
         │  → Calls forecasting model (Prophet, ML)
         │  → Returns: "Next 7 days: 500 units butter needed"
         │
         ▼
STEP 2: Get Current Inventory
         │
         │  Query inventory database
         │  → Returns: "Current stock: 200 units butter"
         │
         ▼
STEP 3: Get Realtime Prices
         │
         │  PriceMonitoringAgent
         │  → Calls supplier APIs for live prices
         │  → Returns: "SupplierA: $4.50/lb, SupplierB: $4.20/lb"
         │
         ▼
STEP 4: Calculate Order Quantity
         │
         │  Compare demand (500) vs inventory (200)
         │  → Need to order: 300 units + safety buffer
         │
         ▼
STEP 5: Generate Purchase Order
         │
         │  AutomatedOrderingAgent
         │  → Selects best supplier (SupplierB @ $4.20)
         │  → Generates PO for 350 units
         │
         ▼
STEP 6: [Optional] Human Approval
         │
         │  → Dashboard shows: "Ready to order 350 units from SupplierB"
         │  → User clicks [APPROVE] or [REJECT]
         │
         ▼
STEP 7: Execute Order
         │
         │  → Send PO via EDI/API/Email
         │  → Update inventory system
         │  → Notify stakeholders
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DASHBOARD (Frontend)                             │
│                 Next.js / React / Vue                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  [Optimize Inventory]  [Reorder Low Stock]  [Review Prices]  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ REST API / SSE
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                                  │
│                    (main.py @ :8000)                                │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  POST /api/workflows/optimize-inventory                     │    │
│  │  POST /api/workflows/reorder-low-stock                      │    │
│  │  POST /api/workflows/price-alert-review                     │    │
│  │  POST /api/workflows/approve-order                          │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │           MAGENTIC WORKFLOW ORCHESTRATOR                    │    │
│  │                                                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │    │
│  │  │    PRICE     │  │   DEMAND     │  │   ORDERING   │      │    │
│  │  │  MONITORING  │  │ FORECASTING  │  │              │      │    │
│  │  │    AGENT     │  │    AGENT     │  │    AGENT     │      │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                     MCP TOOLS                               │    │
│  │  Supplier API │ Inventory DB │ Finance │ EDI/Email         │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
realtime_price_agent/
│
├── main.py                         # FastAPI - workflow trigger endpoints
├── Dockerfile                      # Container build
├── pyproject.toml                  # Dependencies
├── .env                            # Environment secrets (gitignored)
├── .env.sample                     # Environment template
│
├── agents/                         # 🤖 AI AGENT LAYER
│   ├── config.py                   # Azure OpenAI, MCP URLs config
│   │
│   ├── orchestrator/               # 🎯 Workflow orchestration
│   │   ├── magentic_workflow.py    # Programmed workflow execution
│   │   └── tools/
│   │       ├── tool_config.py      # MCP server definitions
│   │       └── tool_registry.py    # Tool connection manager
│   │
│   ├── price_monitoring/           # 💰 Price Analysis Agent
│   │   └── agent.py                # Fetches realtime prices, compares suppliers
│   │
│   ├── demand_forecasting/         # 📈 Demand Prediction Agent
│   │   └── agent.py                # Runs forecasting models (Prophet, ML)
│   │
│   └── automated_ordering/         # 🛒 Order Generation Agent
│       └── agent.py                # Creates POs, executes orders
│
├── database/                       # 🗄️ Data Access Layer
│   ├── config.py                   # PostgreSQL connection
│   └── models.py                   # SQLAlchemy models
│
├── services/                       # ⚙️ Business Logic
│   ├── inventory_service.py        # Stock levels, adjustments
│   ├── supplier_service.py         # Supplier management
│   ├── order_service.py            # Order creation, tracking
│   └── price_service.py            # Price sync, comparisons
│
└── legacy/                         # 📦 Archived old code
```

## � API Endpoints

### Workflow Trigger Endpoints (Dashboard Buttons)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/workflows/optimize-inventory` | Run full inventory optimization |
| `POST` | `/api/workflows/reorder-low-stock` | Reorder items below threshold |
| `POST` | `/api/workflows/price-alert-review` | Review and act on price changes |
| `POST` | `/api/workflows/approve-order/{order_id}` | Human approval for pending order |

### Current Endpoints (Already Implemented)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | System health check |
| `GET` | `/api/tools` | List available MCP tools |
| `POST` | `/api/chat` | Legacy: Natural language trigger |
| `GET` | `/products` | List inventory products |
| `GET` | `/suppliers` | List suppliers |
| `GET` | `/orders` | List purchase orders |

## 🚀 Quick Start

### 1. Setup

```bash
cd realtime_price_agent
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 2. Configure Environment

```bash
# Copy and edit .env
cp .env.sample .env

# Required:
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### 3. Run

```bash
uvicorn main:app --reload --port 8000
```

### 4. Trigger a Workflow

```bash
# From dashboard or CLI:
curl -X POST http://localhost:8000/api/workflows/optimize-inventory
```

## � How Agents Execute Workflows

### Key Difference from Chat Applications

| Aspect | Chat Application | This System (Programmed Workflows) |
|--------|------------------|-----------------------------------|
| Trigger | User types message | Button click / API call |
| Flow | Open-ended conversation | Predefined step sequence |
| Agency | High (LLM decides everything) | Low (Steps are programmed) |
| Exceptions | Many edge cases | Minimal, predictable |
| Human-in-loop | During conversation | Only at approval step |

### Workflow Execution Flow

```python
# Example: Optimize Inventory Workflow
async def optimize_inventory_workflow():
    # Step 1: Get demand forecast
    forecast = await demand_agent.get_forecast(days=7)
    
    # Step 2: Get current inventory
    inventory = await inventory_service.get_levels()
    
    # Step 3: Get realtime prices
    prices = await price_agent.get_supplier_prices()
    
    # Step 4: Calculate order needs
    order_needs = calculate_order_quantity(forecast, inventory)
    
    # Step 5: Generate purchase order
    order = await ordering_agent.generate_order(order_needs, prices)
    
    # Step 6: Wait for human approval (optional)
    if requires_approval(order):
        yield {"status": "pending_approval", "order": order}
    else:
        await ordering_agent.execute_order(order)
        yield {"status": "completed", "order": order}
```

## 🔒 Human-in-the-Loop (Optional)

For high-value orders, the workflow can pause for human approval:

```
┌────────────────────────────────────────────────────────────┐
│  PENDING APPROVAL                                          │
│                                                            │
│  Order: 350 units of Butter from SupplierB                 │
│  Total: $1,470.00                                          │
│  Reason: Stock optimization based on 7-day forecast        │
│                                                            │
│  ┌──────────────┐    ┌──────────────┐                     │
│  │   APPROVE    │    │   REJECT     │                     │
│  └──────────────┘    └──────────────┘                     │
└────────────────────────────────────────────────────────────┘
```

## 🐳 Deployment

```bash
# Build
docker build -t supply-chain-agents .

# Run
docker run -p 8000:8000 --env-file .env supply-chain-agents
```

## 📚 Next Steps

1. **Add workflow endpoints** - Create specific `/api/workflows/*` routes
2. **Implement MCP tools** - Connect to real supplier/inventory APIs
3. **Build dashboard UI** - React/Next.js frontend with workflow buttons
4. **Add approval system** - Human-in-the-loop for high-value orders

## 📚 References

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Magentic Orchestration](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic)
- [Azure AI Travel Agents (Reference)](https://github.com/Azure-Samples/azure-ai-travel-agents)
