# Multi-Agent Inventory Optimization Platform

## Context

- **Database**: Postgres Neon (suppliers, products, purchase_orders, purchase_order_items)
- **Amazon API**: `amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io`
- **Azure AI Foundry**: `bhattaraikusum51-8374`

---

## End-to-End Workflow

```
STEP 1: User clicks "Analyze Inventory" → Orchestrator triggered
STEP 2: Demand Forecasting (cached baseline + Prophet on-the-fly)
STEP 3: Price Monitoring → get_realtime_quotes → rank suppliers
STEP 4: Ordering → optimize cart → execute order
STEP 5: Result Aggregation → Orchestrator collects outputs
STEP 6-7: Dashboard Update → order confirmation + tracking
```

---

## Project Structure

```
supply-chain-agents/
├── agents/
│   ├── orchestrator/
│   │   ├── agent.py
│   │   └── Dockerfile
│   ├── demand_forecasting/
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── Dockerfile
│   ├── price_monitoring/
│   │   ├── agent.py
│   │   ├── tools.py           # get_realtime_quotes, fuzzy_match, rank_by_criteria
│   │   └── Dockerfile
│   └── automated_ordering/
│       ├── agent.py
│       ├── tools.py           # simulate_cart, execute_order, update_inventory
│       └── Dockerfile
│
├── mcp-servers/
│   ├── pos-server/
│   ├── supplier-server/
│   ├── analytics-server/      # Prophet model
│   └── finance-server/        # ExchangeRate-API
│
├── workflows/
│   └── optimization_workflow.py
│
├── docker-compose.yml
└── README.md
```

---

## Orchestrator Agent

```python
# agents/orchestrator/agent.py
from agent_framework import Agent
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
import os

# Create LLM client
llm_client = ChatCompletionsClient(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY"))
)

# Create orchestrator agent
orchestrator_agent = Agent(
    name="OrchestratorAgent",
    model_client=llm_client,
    system_prompt="""You are the Orchestrator for an inventory optimization system.
    Route queries to specialized agents:
    - DEMAND_FORECAST: For restocking, predictions, demand analysis
    - PRICE_MONITORING: For supplier comparisons, price queries
    - ORDER_EXECUTION: For placing orders, purchasing
    
    Collect results from each agent and synthesize final response.""",
    tools=["route_to_agent", "aggregate_results"]
)
```

---

## Optimization Workflow

```python
# workflows/optimization_workflow.py
from agent_framework import Workflow

# Import agents
from agents.orchestrator.agent import orchestrator_agent
from agents.price_monitoring.agent import price_monitoring_agent
from agents.demand_forecasting.agent import demand_forecasting_agent
from agents.automated_ordering.agent import ordering_agent

# Create optimization workflow
optimization_workflow = Workflow(
    name="OptimizationWorkflow",
    agents=[
        orchestrator_agent,
        price_monitoring_agent,
        demand_forecasting_agent,
        ordering_agent
    ],
    root_agent=orchestrator_agent  # Entry point
)

# Execute workflow
async def run_optimization(user_message: str):
    result = await optimization_workflow.run(user_message)
    return result
```

---

## Price Monitoring Tools

```python
# agents/price_monitoring/tools.py

@tool
def get_realtime_quotes(items: list, suppliers: str = "all") -> list:
    """Query supplier APIs for live pricing"""
    # Calls supplier MCP server
    return mcp_call("supplier-server", "get_quotes", items=items)

@tool  
def fuzzy_match_suppliers(target_sku: str, catalogs: list) -> list:
    """Match SKUs across supplier catalogs using Levenshtein + embeddings"""
    matches = []
    for catalog in catalogs:
        similarity = calculate_similarity(target_sku, catalog["sku"])
        if similarity > 0.75:
            matches.append({"supplier": catalog["name"], "confidence": similarity})
    return sorted(matches, key=lambda x: x["confidence"], reverse=True)

@tool
def rank_by_criteria(quotes: list, weights: dict) -> list:
    """Score suppliers by price/quality/speed
    weights = {"cost": 0.5, "delivery_speed": 0.3, "quality": 0.2}
    """
    for quote in quotes:
        score = (quote["price_score"] * weights["cost"] +
                 quote["speed_score"] * weights["delivery_speed"] +
                 quote["quality_score"] * weights["quality"])
        quote["overall_score"] = score
    return sorted(quotes, key=lambda x: x["overall_score"], reverse=True)
```

---

## Ordering Tools

```python
# agents/automated_ordering/tools.py

@tool
def simulate_cart_permutations(supplier_matrix: list, constraints: dict) -> dict:
    """Optimize cart across multiple suppliers
    constraints = {"max_budget": 10000, "delivery_deadline": "2026-01-05"}
    """
    permutations = generate_permutations(supplier_matrix)
    scored = []
    for perm in permutations:
        if perm["total_cost"] <= constraints["max_budget"]:
            scored.append({"cart": perm, "score": calculate_score(perm)})
    return max(scored, key=lambda x: x["score"])

@tool
def execute_order(cart: dict) -> dict:
    """Place order via database/ERP integration"""
    po_number = f"PO-{uuid.uuid4().hex[:6].upper()}"
    # Insert into purchase_orders table
    db.execute("INSERT INTO purchase_orders ...")
    return {"status": "PROCESSED", "po_number": po_number}

@tool
def update_inventory(po_number: str, items: list) -> dict:
    """Adjust stock levels after order placement"""
    for item in items:
        db.execute(f"UPDATE products SET quantity_reserved += {item['qty']} ...")
    return {"updated": len(items)}
```

---

## Analytics Server (Prophet)

```python
# mcp-servers/analytics-server/server.py
import pickle
from prophet import Prophet

with open("models/prophet_model.pkl", "rb") as f:
    model = pickle.load(f)

@tool
def forecast_demand(sku: str, periods: int = 7) -> dict:
    """Generate demand forecast using Prophet"""
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    return {"sku": sku, "forecast": forecast[["ds", "yhat"]].to_dict()}
```

---

## Finance Server (ExchangeRate-API)

```python
# mcp-servers/finance-server/server.py
EXCHANGE_API = "https://v6.exchangerate-api.com/v6/{API_KEY}/pair"

@tool
def convert_currency(amount: float, from_curr: str, to_curr: str) -> dict:
    """Convert currency (170 currencies, 60s updates)"""
    resp = requests.get(f"{EXCHANGE_API}/{from_curr}/{to_curr}/{amount}")
    return {"converted": resp.json()["conversion_result"]}

@tool
def validate_budget(cart_total: float, max_budget: float) -> dict:
    return {"within_budget": cart_total <= max_budget}
```

---

## Docker Compose

```yaml
version: '3.8'
services:
  api-gateway:
    build: ./api
    ports: ["8000:8000"]
    
  pos-server:
    build: ./mcp-servers/pos-server
    ports: ["8001:8001"]
    
  supplier-server:
    build: ./mcp-servers/supplier-server
    ports: ["8002:8002"]
    
  analytics-server:
    build: ./mcp-servers/analytics-server
    ports: ["8004:8004"]
    volumes: ["./models:/app/models"]
    
  finance-server:
    build: ./mcp-servers/finance-server
    ports: ["8005:8005"]
```


