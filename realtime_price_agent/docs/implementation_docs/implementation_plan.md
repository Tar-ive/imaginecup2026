# Supply Chain Agents - Implementation Plan

## Overview

This document outlines the implementation plan for building **bulletproof programmed workflow automations** using Microsoft Agent Framework (MAF). The system leverages:

- **Type Safety** - Typed messages between executors
- **Checkpointing** - State saving and recovery
- **Human-in-the-Loop** - Approval workflows
- **Observability** - OpenTelemetry integration
- **Handoff Orchestration** - Agent coordination

### Workflow Goals

1. **Forecast demand** using Prophet (ML) derived from order history
2. **Get realtime prices** from Amazon API (already implemented)
3. **Get current inventory** from PostgreSQL Neon (already implemented)
4. **Compare and decide** order quantities
5. **Execute orders** with human approval modal in dashboard
6. **Deploy** to Azure using `azd`

---

## MAF Advanced Features Reference

### Available Classes in agent-framework-core

```python
# Checkpointing
from agent_framework import (
    CheckpointStorage,
    FileCheckpointStorage,
    InMemoryCheckpointStorage,
    WorkflowCheckpoint,
    WorkflowCheckpointSummary,
    get_checkpoint_summary,
)

# Human-in-the-Loop
from agent_framework import (
    MagenticHumanInputRequest,
    MagenticHumanInterventionDecision,
    MagenticHumanInterventionKind,
    MagenticHumanInterventionReply,
    MagenticHumanInterventionRequest,
    HandoffUserInputRequest,
)

# Handoff Orchestration
from agent_framework import HandoffBuilder

# Observability
from agent_framework import observability
```

### MagenticBuilder Methods

| Method | Purpose |
|--------|---------|
| `.participants(...)` | Define agents in workflow |
| `.with_standard_manager(...)` | Set orchestration manager |
| `.with_checkpointing(storage)` | Enable state persistence |
| `.with_human_input_on_stall()` | Request human help when stuck |
| `.with_plan_review()` | Human reviews agent plans |
| `.start_with(executor)` | Set starting executor |
| `.build()` | Build the workflow |

### HandoffBuilder Methods

| Method | Purpose |
|--------|---------|
| `.participants(...)` | Define agents |
| `.set_coordinator(agent)` | Set coordinator agent |
| `.add_handoff(from, to, condition)` | Define handoff rules |
| `.with_checkpointing(storage)` | Enable checkpoints |
| `.with_interaction_mode(mode)` | Set interaction mode |
| `.with_termination_condition(fn)` | Define when to stop |
| `.enable_return_to_previous()` | Allow backtracking |

---

## Architecture: Bulletproof Workflow Design

### Single Responsibility Principle

Each component has ONE job:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW ARCHITECTURE                           │
│                  (Single Responsibility Design)                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     WORKFLOW EXECUTOR                        │   │
│  │            (Coordinates steps, manages state)                │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│    ┌────────────────────────┼────────────────────────────┐         │
│    │                        │                            │         │
│    ▼                        ▼                            ▼         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │  FORECASTER  │    │    PRICE     │    │   ORDERER    │         │
│  │   EXECUTOR   │    │   EXECUTOR   │    │   EXECUTOR   │         │
│  │              │    │              │    │              │         │
│  │ Job: Predict │    │ Job: Fetch   │    │ Job: Create  │         │
│  │   demand     │    │   prices     │    │    POs       │         │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘         │
│         │                   │                   │                  │
│         ▼                   ▼                   ▼                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │   PROPHET    │    │  AMAZON API  │    │  ORDER DB    │         │
│  │    MODEL     │    │  / SUPPLIERS │    │   SERVICE    │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│                                                                     │
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    APPROVAL EXECUTOR                         │   │
│  │              (Human-in-the-Loop checkpoint)                  │   │
│  │                                                              │   │
│  │  Job: Pause workflow, await human approval via dashboard     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   OBSERVABILITY LAYER                        │   │
│  │  • OpenTelemetry traces   • Metrics   • Dashboard events    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Checkpointing Implementation

### Why Checkpointing?

- **Fault Tolerance**: Resume after crashes
- **Human-in-the-Loop**: Pause for approval, resume later
- **Debugging**: Replay from any checkpoint
- **Long-Running**: Handle workflows spanning hours/days

### Checkpoint Storage Options

```python
from agent_framework import (
    FileCheckpointStorage,
    InMemoryCheckpointStorage,
)

# Option 1: File-based (development)
storage = FileCheckpointStorage(directory="./checkpoints")

# Option 2: In-memory (testing)
storage = InMemoryCheckpointStorage()

# Option 3: Azure Cosmos DB (production) - custom implementation
class CosmosCheckpointStorage(CheckpointStorage):
    async def save(self, checkpoint: WorkflowCheckpoint):
        await cosmos_client.upsert(checkpoint.to_dict())
    
    async def load(self, checkpoint_id: str) -> WorkflowCheckpoint:
        data = await cosmos_client.get(checkpoint_id)
        return WorkflowCheckpoint.from_dict(data)
```

### Using Checkpointing in Workflow

```python
from agent_framework import MagenticBuilder, FileCheckpointStorage

# Create checkpoint storage
checkpoint_storage = FileCheckpointStorage(directory="./checkpoints")

# Build workflow with checkpointing
workflow = (
    MagenticBuilder()
    .participants(
        ForecastAgent=...,
        PriceAgent=...,
        OrderAgent=...,
    )
    .with_checkpointing(checkpoint_storage)  # Enable checkpoints
    .with_standard_manager(agent=manager, max_round_count=8)
    .build()
)

# Checkpoints are automatically saved at each "superstep"
# A superstep = completion of one agent's turn

# Resume from checkpoint
checkpoint_id = "workflow-123"
resumed_workflow = await workflow.resume_from(checkpoint_id)
```

### Checkpoint Events for Dashboard

```python
# Capture checkpoint events for dashboard display
async def on_checkpoint(checkpoint: WorkflowCheckpoint):
    await dashboard_websocket.emit({
        "type": "checkpoint",
        "checkpoint_id": checkpoint.id,
        "step": checkpoint.current_step,
        "state": checkpoint.state_summary,
        "timestamp": checkpoint.created_at,
    })
```

---

## Human-in-the-Loop Implementation

### Approval Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HUMAN-IN-THE-LOOP FLOW                           │
│                                                                     │
│  1. Workflow reaches approval step                                  │
│     ┌─────────────────────────────────────┐                        │
│     │ OrderAgent generates PO:            │                        │
│     │ • 350 units Butter from SupplierB   │                        │
│     │ • Total: $1,470.00                  │                        │
│     └─────────────────┬───────────────────┘                        │
│                       │                                             │
│  2. Workflow pauses, checkpoint saved                               │
│     ┌─────────────────▼───────────────────┐                        │
│     │ CHECKPOINT: pending_approval        │                        │
│     │ State saved to storage              │                        │
│     └─────────────────┬───────────────────┘                        │
│                       │                                             │
│  3. Dashboard shows approval modal                                  │
│     ┌─────────────────▼───────────────────┐                        │
│     │  ┌─────────────────────────────┐    │                        │
│     │  │   PENDING APPROVAL           │    │                        │
│     │  │                              │    │                        │
│     │  │   Order: 350 units Butter    │    │                        │
│     │  │   Supplier: SupplierB        │    │                        │
│     │  │   Total: $1,470.00           │    │                        │
│     │  │                              │    │                        │
│     │  │  [APPROVE]  [REJECT]         │    │                        │
│     │  └─────────────────────────────┘    │                        │
│     └─────────────────┬───────────────────┘                        │
│                       │                                             │
│  4. User clicks APPROVE                                             │
│     ┌─────────────────▼───────────────────┐                        │
│     │ POST /api/workflows/approve/{id}    │                        │
│     │ Workflow resumes from checkpoint    │                        │
│     └─────────────────┬───────────────────┘                        │
│                       │                                             │
│  5. Order executed                                                  │
│     ┌─────────────────▼───────────────────┐                        │
│     │ ExecutionAgent sends PO via EDI     │                        │
│     │ Inventory updated                   │                        │
│     │ Confirmation sent                   │                        │
│     └─────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

### MAF Human Intervention Classes

```python
from agent_framework import (
    MagenticHumanInterventionRequest,
    MagenticHumanInterventionReply,
    MagenticHumanInterventionDecision,
    MagenticHumanInterventionKind,
)

# Request human input
request = MagenticHumanInterventionRequest(
    kind=MagenticHumanInterventionKind.APPROVAL,
    message="Approve purchase order for 350 units of Butter?",
    context={
        "order_id": "PO-123",
        "supplier": "SupplierB",
        "total": 1470.00,
        "items": [...],
    },
)

# Human provides reply (via dashboard API)
reply = MagenticHumanInterventionReply(
    decision=MagenticHumanInterventionDecision.APPROVE,
    message="Approved by user@company.com",
)

# Workflow resumes with reply
await workflow.resume_with_human_input(reply)
```

### Dashboard API for Approvals

```python
# main.py - Approval endpoints

@app.get("/api/workflows/pending-approvals")
async def get_pending_approvals():
    """Get all workflows awaiting human approval."""
    return await checkpoint_storage.get_pending_approvals()

@app.post("/api/workflows/approve/{workflow_id}")
async def approve_workflow(
    workflow_id: str,
    decision: Literal["approve", "reject"],
    comment: Optional[str] = None,
):
    """Human approves or rejects a pending workflow."""
    checkpoint = await checkpoint_storage.load(workflow_id)
    
    reply = MagenticHumanInterventionReply(
        decision=(
            MagenticHumanInterventionDecision.APPROVE 
            if decision == "approve" 
            else MagenticHumanInterventionDecision.REJECT
        ),
        message=comment,
    )
    
    # Resume workflow
    workflow = await build_workflow_from_checkpoint(checkpoint)
    result = await workflow.resume_with_human_input(reply)
    
    return {"status": "resumed", "result": result}
```

---

## Handoff Implementation

### Handoff Pattern for Supply Chain

```python
from agent_framework import HandoffBuilder, ChatAgent

# Build handoff workflow
workflow = (
    HandoffBuilder()
    .participants(
        ForecastAgent=forecast_agent,
        PriceAgent=price_agent,
        OrderAgent=order_agent,
        ApprovalAgent=approval_agent,
    )
    .set_coordinator(orchestrator_agent)
    .add_handoff(
        from_agent="ForecastAgent",
        to_agent="PriceAgent",
        condition=lambda result: result.get("needs_reorder", False),
    )
    .add_handoff(
        from_agent="PriceAgent",
        to_agent="OrderAgent",
        condition=lambda result: result.get("best_supplier") is not None,
    )
    .add_handoff(
        from_agent="OrderAgent",
        to_agent="ApprovalAgent",
        condition=lambda result: result.get("order_value", 0) > 500,
    )
    .with_checkpointing(checkpoint_storage)
    .enable_return_to_previous()  # Allow backtracking
    .build()
)
```

### Data Handoff Between Agents

```python
# Typed message passing between agents
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ForecastResult:
    asin: str
    predicted_demand: float
    confidence: float
    current_stock: int
    shortfall: int

@dataclass
class PriceResult:
    asin: str
    best_supplier: str
    best_price: float
    alternatives: List[dict]

@dataclass
class OrderResult:
    order_id: str
    supplier: str
    items: List[dict]
    total_value: float
    requires_approval: bool

# Agent receives typed input, produces typed output
class ForecastAgent:
    async def process(self, request: dict) -> ForecastResult:
        # Forecast logic
        return ForecastResult(
            asin=request["asin"],
            predicted_demand=...,
            confidence=...,
            current_stock=...,
            shortfall=...,
        )
```

---

## Observability Implementation

### OpenTelemetry Integration

MAF has built-in OpenTelemetry support:

```python
from agent_framework import observability
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure OpenTelemetry
provider = TracerProvider()
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="http://localhost:4317")
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Enable observability in MAF
observability.enable(
    include_sensitive_data=False,  # Don't log prompts in production
)
```

### Telemetry Interceptor Pattern

Use interceptors to inject telemetry into agent methods:

```python
import functools
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def telemetry_interceptor(func):
    """AOP-style decorator for telemetry."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(
            name=f"agent.{func.__name__}",
            attributes={
                "agent.name": args[0].__class__.__name__,
                "agent.method": func.__name__,
            }
        ) as span:
            try:
                result = await func(*args, **kwargs)
                span.set_attribute("agent.success", True)
                return result
            except Exception as e:
                span.set_attribute("agent.success", False)
                span.set_attribute("agent.error", str(e))
                raise
    return wrapper

# Apply to agent methods
class PriceMonitoringAgent:
    @telemetry_interceptor
    async def get_supplier_prices(self, asin: str):
        # ... implementation
```

### Dashboard Observability Events

```python
# Emit events for dashboard consumption
async def emit_workflow_event(event_type: str, data: dict):
    """Send workflow events to dashboard via WebSocket/SSE."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "trace_id": get_current_trace_id(),
        "span_id": get_current_span_id(),
        **data,
    }
    await dashboard_event_queue.put(event)

# Events to emit:
# - workflow.started
# - workflow.checkpoint
# - agent.started
# - agent.completed
# - agent.handoff
# - approval.requested
# - approval.received
# - workflow.completed
# - workflow.failed
```

---

## Azure Deployment Architecture

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AZURE CLOUD SERVICES                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               Azure Container Apps Environment               │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐          │   │
│  │  │   FastAPI Backend   │  │   Dashboard (React) │          │   │
│  │  │   (Container App)   │  │   (Container App)   │          │   │
│  │  └──────────┬──────────┘  └──────────┬──────────┘          │   │
│  └─────────────┼────────────────────────┼──────────────────────┘   │
│                │                        │                           │
│  ┌─────────────▼────────────────────────▼──────────────────────┐   │
│  │                    Azure OpenAI                              │   │
│  │                    (gpt-5-mini)                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │  MAF storing somewhere      │  │  Azure Key Vault    │                  │
│  │  (Checkpoints)      │  │  (Secrets)          │                  │
│  │                     │  │                     │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │  PostgreSQL (Neon)  │  │  MAF      │                  │
│  │  (Inventory/Orders) │  │  (Observability)    │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

### azd Configuration

```yaml
# azure.yaml
name: supply-chain-agents
metadata:
  template: supply-chain-agents

services:
  api:
    project: ./
    language: python
    host: containerapp
    docker:
      path: ./Dockerfile

hooks:
  postprovision:
    shell: bash
    run: |
      echo "Setting up OpenTelemetry connection..."
      az containerapp env update \
        --name $AZURE_CONTAINER_APPS_ENV \
        --resource-group $RESOURCE_GROUP \
        --dapr-instrumentation-key $APPINSIGHTS_KEY
```

### Bicep Infrastructure

```bicep
// infra/main.bicep

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'supply-chain-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    daprAIInstrumentationKey: appInsights.properties.InstrumentationKey
  }
}

resource apiApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'supply-chain-api'
  properties: {
    configuration: {
      secrets: [
        { name: 'azure-openai-key', value: openAiKey }
        { name: 'database-url', value: databaseUrl }
      ]
      ingress: {
        external: true
        targetPort: 8000
      }
    }
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: 'supply-chain-checkpoints'
  // ... checkpoint storage
}
```

---

## Implementation Phases

### Phase 1: Forecasting Model (Prophet)

```bash
# Create forecasting module
mkdir -p agents/forecasting
```

```python
# agents/forecasting/prophet_model.py
from prophet import Prophet
import pandas as pd
from database.models import PurchaseOrder, PurchaseOrderItem
from sqlalchemy.orm import Session

class DemandForecaster:
    def __init__(self):
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
    
    def get_sales_history_from_orders(
        self, db: Session, asin: str, days: int = 90
    ) -> pd.DataFrame:
        """Derive sales history from purchase orders."""
        query = """
            SELECT 
                DATE(po.created_at) as ds,
                SUM(poi.quantity) as y
            FROM purchase_order_items poi
            JOIN purchase_orders po ON poi.po_number = po.po_number
            WHERE poi.asin = :asin
              AND po.status = 'received'
              AND po.created_at >= NOW() - INTERVAL ':days days'
            GROUP BY DATE(po.created_at)
            ORDER BY ds
        """
        result = db.execute(query, {"asin": asin, "days": days})
        return pd.DataFrame(result.fetchall(), columns=["ds", "y"])
    
    def forecast(self, sales_data: pd.DataFrame, periods: int = 7) -> dict:
        """Forecast demand for next N days."""
        if len(sales_data) < 7:
            # Not enough data, use simple average
            avg = sales_data["y"].mean() if len(sales_data) > 0 else 0
            return {
                "predicted_demand": avg * periods,
                "confidence": "low",
                "method": "average",
            }
        
        self.model.fit(sales_data)
        future = self.model.make_future_dataframe(periods=periods)
        forecast = self.model.predict(future)
        
        return {
            "predicted_demand": forecast["yhat"].tail(periods).sum(),
            "daily_forecast": forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
                .tail(periods).to_dict("records"),
            "confidence": "high" if len(sales_data) >= 30 else "medium",
            "method": "prophet",
        }
```

### Phase 2: Workflow Integration

Create the workflow executor with checkpointing and handoffs:

```python
# agents/workflows/inventory_optimization.py

from agent_framework import (
    MagenticBuilder,
    FileCheckpointStorage,
    MagenticHumanInterventionRequest,
    MagenticHumanInterventionKind,
)
from agents.forecasting import DemandForecaster
from agents.price_monitoring import create_price_monitoring_agent
from agents.automated_ordering import create_automated_ordering_agent

class InventoryOptimizationWorkflow:
    def __init__(self, db, chat_client):
        self.db = db
        self.chat_client = chat_client
        self.forecaster = DemandForecaster()
        self.checkpoint_storage = FileCheckpointStorage("./checkpoints")
    
    async def execute(self, product_filter=None):
        """Execute optimization workflow with checkpointing."""
        
        # Build workflow with all MAF features
        workflow = (
            MagenticBuilder()
            .participants(
                ForecastExecutor=...,
                PriceExecutor=...,
                OrderExecutor=...,
            )
            .with_checkpointing(self.checkpoint_storage)
            .with_human_input_on_stall()
            .with_standard_manager(
                agent=self.manager_agent,
                max_round_count=10,
            )
            .build()
        )
        
        # Execute with streaming
        async for event in workflow.run_stream(product_filter):
            yield self._format_event(event)
```

### Phase 3: Testing

```bash
# Local testing
uvicorn main:app --reload --port 8000

# Test forecast
curl http://localhost:8000/api/forecast/B0EXAMPLE?days=7

# Test workflow (streaming)
curl -N -X POST http://localhost:8000/api/workflows/optimize-inventory

# Test approval
curl -X POST "http://localhost:8000/api/workflows/approve/wf-123?decision=approve"
```

### Phase 4: Deployment

See detailed Azure deployment instructions below.

---

## Azure Deployment with azd

### Prerequisites

- [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- Azure subscription with Owner or Contributor permissions
- Docker installed (for container builds)

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AZURE INFRASTRUCTURE                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                 AZURE CONTAINER APPS                         │    │
│  │  ┌──────────────────┐  ┌──────────────────┐                 │    │
│  │  │  supply-chain-   │  │  mcp-ordering-   │                 │    │
│  │  │  agents-api      │  │  server          │                 │    │
│  │  │  (FastAPI)       │  │  (MCP Tools)     │                 │    │
│  │  └────────┬─────────┘  └────────┬─────────┘                 │    │
│  │           │                     │                            │    │
│  │  ┌────────┴─────────────────────┴────────┐                  │    │
│  │  │           Container Apps Env          │                  │    │
│  │  │  • Managed Identity                   │                  │    │
│  │  │  • Ingress / HTTPS                    │                  │    │
│  │  │                                       │                  │    │
│  │  └───────────────────────────────────────┘                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Azure OpenAI   │  │  PostgreSQL     │  │  Application    │     │
│  │  (GPT-5 -mini)  │  │  Flexible/Neon  │  │  Insights       │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Step 1: Create azure.yaml

```yaml
# azure.yaml
name: supply-chain-agents
metadata:
  template: supply-chain-agents@0.0.1

services:
  api:
    project: .
    language: python
    host: containerapp
    docker:
      path: ./Dockerfile

hooks:
  postprovision:
    shell: sh
    run: |
      echo "Deployment complete!"
      echo "API URL: $SERVICE_API_ENDPOINT"
```

### Step 2: Create Bicep Infrastructure

```bicep
// infra/main.bicep
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Azure OpenAI endpoint')
param azureOpenAiEndpoint string

@secure()
@description('Azure OpenAI API key')
param azureOpenAiApiKey string

@description('Database connection string')
@secure()
param databaseUrl string

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-${environmentName}'
  location: location
}

// Container Apps Environment
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: 'container-apps-env'
  scope: rg
  params: {
    name: 'cae-${environmentName}'
    location: location
  }
}

// Supply Chain API
module api 'modules/container-app.bicep' = {
  name: 'supply-chain-api'
  scope: rg
  params: {
    name: 'supply-chain-api'
    location: location
    containerAppsEnvironmentId: containerAppsEnv.outputs.id
    containerImage: 'supply-chain-agents:latest'
    targetPort: 8000
    env: [
      { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAiEndpoint }
      { name: 'AZURE_OPENAI_API_KEY', secretRef: 'openai-key' }
      { name: 'DATABASE_URL', secretRef: 'database-url' }
    ]
    secrets: [
      { name: 'openai-key', value: azureOpenAiApiKey }
      { name: 'database-url', value: databaseUrl }
    ]
  }
}

// MCP Ordering Server
module mcpOrdering 'modules/container-app.bicep' = {
  name: 'mcp-ordering-server'
  scope: rg
  params: {
    name: 'mcp-ordering'
    location: location
    containerAppsEnvironmentId: containerAppsEnv.outputs.id
    containerImage: 'mcp-ordering-server:latest'
    targetPort: 3000
    env: [
      { name: 'DATABASE_URL', secretRef: 'database-url' }
    ]
    secrets: [
      { name: 'database-url', value: databaseUrl }
    ]
  }
}

// Application Insights
module appInsights 'modules/app-insights.bicep' = {
  name: 'app-insights'
  scope: rg
  params: {
    name: 'appi-${environmentName}'
    location: location
  }
}

output SERVICE_API_ENDPOINT string = api.outputs.fqdn
output SERVICE_MCP_ENDPOINT string = mcpOrdering.outputs.fqdn
```

### Step 3: Deploy

```bash
# Initialize azd project
azd init

# Login to Azure
azd auth login

# Set environment variables
azd env set AZURE_OPENAI_ENDPOINT "https://your-resource.openai.azure.com"
azd env set AZURE_OPENAI_API_KEY "your-api-key"
azd env set DATABASE_URL "postgresql://..."

# Deploy everything
azd up

# Get deployed URLs
azd env get-values
```

---

## MCP Server Setup for Ordering Agent

### Overview

MCP (Model Context Protocol) servers provide tools that agents can call. For the Ordering Agent, we need tools to:

1. **Create purchase orders**
2. **Get supplier catalogs**
3. **Submit orders via EDI/API**
4. **Track order status**

### MCP Server Implementation

Create a dedicated MCP server for ordering operations:

```typescript
// mcp-servers/ordering/src/server.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "ordering-server",
  version: "1.0.0",
});

// Tool: Create Purchase Order
server.tool(
  "create_purchase_order",
  "Create a new purchase order for a supplier",
  {
    supplier_id: { type: "string", description: "Supplier ID" },
    items: {
      type: "array",
      description: "Array of items to order",
      items: {
        type: "object",
        properties: {
          asin: { type: "string" },
          quantity: { type: "number" },
          unit_price: { type: "number" },
        },
      },
    },
    expected_delivery_date: { type: "string", description: "ISO date" },
  },
  async ({ supplier_id, items, expected_delivery_date }) => {
    // Call order service
    const order = await orderService.createOrder({
      supplierId: supplier_id,
      items,
      expectedDeliveryDate: new Date(expected_delivery_date),
    });
    
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            po_number: order.poNumber,
            status: "created",
            total: order.totalCost,
          }),
        },
      ],
    };
  }
);

// Tool: Get Supplier Catalog
server.tool(
  "get_supplier_catalog",
  "Get product catalog from a supplier",
  {
    supplier_id: { type: "string", description: "Supplier ID" },
  },
  async ({ supplier_id }) => {
    const products = await supplierService.getCatalog(supplier_id);
    return {
      content: [{ type: "text", text: JSON.stringify(products) }],
    };
  }
);

// Tool: Submit Order
server.tool(
  "submit_order",
  "Submit an approved order to the supplier",
  {
    po_number: { type: "string", description: "Purchase order number" },
  },
  async ({ po_number }) => {
    const result = await orderService.submitToSupplier(po_number);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            status: result.status,
            confirmation: result.supplierConfirmation,
          }),
        },
      ],
    };
  }
);

// Tool: Get Order Status
server.tool(
  "get_order_status",
  "Check the status of a purchase order",
  {
    po_number: { type: "string", description: "Purchase order number" },
  },
  async ({ po_number }) => {
    const order = await orderService.getOrderDetails(po_number);
    return {
      content: [{ type: "text", text: JSON.stringify(order) }],
    };
  }
);

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Dockerfile for MCP Server

```dockerfile
# mcp-servers/ordering/Dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["node", "dist/server.js"]
```

### Deploy MCP Server to Azure Container Apps

```bash
# Build and push MCP server
docker build -t mcp-ordering-server ./mcp-servers/ordering
az acr login --name <your-registry>
docker tag mcp-ordering-server <your-registry>.azurecr.io/mcp-ordering-server
docker push <your-registry>.azurecr.io/mcp-ordering-server

# Deploy via azd (included in main.bicep)
azd up
```

### Configure Agent to Use MCP Tools

Update the tool configuration:

```python
# agents/orchestrator/tools/tool_config.py
def get_mcp_tools_config():
    return {
        "ordering": {
            "config": {
                "url": f"{settings.mcp_ordering_url}/mcp",
                "type": "http",
                "verbose": True,
            },
            "id": "ordering",
            "name": "Ordering Tools",
        },
        # ... other MCP servers
    }
```

### Using MCP Tools in Ordering Agent

```python
# agents/automated_ordering/agent.py
ORDERING_AGENT_INSTRUCTIONS = """You are an automated ordering agent.

AVAILABLE MCP TOOLS:

ORDERING_MCP:
- create_purchase_order(supplier_id, items, expected_delivery_date)
- get_supplier_catalog(supplier_id)
- submit_order(po_number)
- get_order_status(po_number)

WORKFLOW:
1. Receive order recommendations from workflow
2. Create purchase orders using create_purchase_order
3. Wait for human approval (if required)
4. Submit approved orders using submit_order
5. Monitor status using get_order_status
"""
```

---

## MCP Deployment with OpenTelemetry

### Deployment Reference

See [mcp_deploy.md](../mcp_deploy.md) for the official Azure MCP Server deployment guide using `azd`.

### Custom MCP Server with Telemetry

For supply chain MCP servers, we extend the pattern with OpenTelemetry:

#### Python MCP Server Template

```python
# mcp-servers/supplier-data/server.py
from fastapi import FastAPI
from mcp.server.fastapi import add_mcp_routes
from mcp import Tool
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
import os

# ============ OpenTelemetry Setup ============
resource = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "mcp-supplier-server"),
    "service.version": "1.0.0",
})

provider = TracerProvider(resource=resource)

# Export to Azure Monitor if connection string provided
app_insights_conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if app_insights_conn:
    azure_exporter = AzureMonitorTraceExporter.from_connection_string(app_insights_conn)
    provider.add_span_processor(BatchSpanProcessor(azure_exporter))
else:
    # Local OTLP collector
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# ============ FastAPI App ============
app = FastAPI(title="Supplier Data MCP Server")

# ============ MCP Tools with Telemetry ============
@app.tool()
async def get_suppliers(category: str = None):
    """Get all suppliers, optionally filtered by category."""
    with tracer.start_as_current_span("mcp.get_suppliers") as span:
        span.set_attribute("supplier.category_filter", category or "all")
        
        # Your implementation
        suppliers = await db.fetch_suppliers(category)
        
        span.set_attribute("supplier.count", len(suppliers))
        return {"suppliers": suppliers}

@app.tool()
async def get_supplier_products(supplier_id: str):
    """Get products for a specific supplier."""
    with tracer.start_as_current_span("mcp.get_supplier_products") as span:
        span.set_attribute("supplier.id", supplier_id)
        
        products = await db.fetch_products_by_supplier(supplier_id)
        
        span.set_attribute("product.count", len(products))
        return {"products": products}

# Add MCP routes
add_mcp_routes(app, path="/mcp")

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-supplier-server"}
```

#### Dockerfile for MCP Server

```dockerfile
# mcp-servers/supplier-data/Dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### requirements.txt for MCP Server

```txt
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
mcp>=0.1.0
httpx>=0.27.0
opentelemetry-api>=1.30.0
opentelemetry-sdk>=1.30.0
opentelemetry-exporter-otlp-proto-grpc>=1.30.0
azure-monitor-opentelemetry-exporter>=1.0.0b12
sqlalchemy>=2.0.30
psycopg2-binary
```

### Deploy MCP to Same Container Apps Environment

```bash
# ============ Step 1: Build and Push ============
cd mcp-servers/supplier-data

# Login to ACR
az acr login --name imaginecupreg999

# Build and push
docker build -t imaginecupreg999.azurecr.io/mcp-supplier:v1 .
docker push imaginecupreg999.azurecr.io/mcp-supplier:v1

# ============ Step 2: Get App Insights Connection String ============
APP_INSIGHTS_CONN=$(az monitor app-insights component show \
  --app imaginecup7299870127 \
  --resource-group ImagineCup \
  --query connectionString -o tsv)

# ============ Step 3: Deploy as Container App ============
az containerapp create \
  --name mcp-supplier-server \
  --resource-group ImagineCup \
  --environment imagine-cup-env \
  --image imaginecupreg999.azurecr.io/mcp-supplier:v1 \
  --target-port 8000 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --registry-server imaginecupreg999.azurecr.io \
  --set-env-vars \
    "OTEL_SERVICE_NAME=mcp-supplier-server" \
    "APPLICATIONINSIGHTS_CONNECTION_STRING=${APP_INSIGHTS_CONN}" \
    "DATABASE_URL=secretref:database-url"

# ============ Step 4: Get Internal URL ============
MCP_SUPPLIER_URL=$(az containerapp show \
  --name mcp-supplier-server \
  --resource-group ImagineCup \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "MCP Supplier URL: https://${MCP_SUPPLIER_URL}"
```

### Connect MCP Servers to Main API

After deploying MCP servers, update the main API:

```bash
# Update main API with MCP URLs
az containerapp update \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --set-env-vars \
    "MCP_SUPPLIER_URL=https://mcp-supplier-server.internal.imagine-cup-env.eastus.azurecontainerapps.io" \
    "MCP_INVENTORY_URL=https://mcp-inventory-server.internal.imagine-cup-env.eastus.azurecontainerapps.io" \
    "MCP_FINANCE_URL=https://mcp-finance-server.internal.imagine-cup-env.eastus.azurecontainerapps.io"
```

### MCP Server Matrix

| Server | Purpose | Tools | Priority |
|--------|---------|-------|----------|
| `mcp-supplier-server` | Supplier data access | get_suppliers, get_supplier_products, get_supplier_prices | P1 |
| `mcp-inventory-server` | Inventory operations | get_stock_levels, update_inventory, get_low_stock | P1 |
| `mcp-ordering-server` | Order management | create_purchase_order, submit_order, get_order_status | P2 |
| `mcp-finance-server` | Financial data | get_exchange_rates, get_budget, calculate_cost | P2 |
| `mcp-logistics-server` | Shipment tracking | track_shipment, calculate_stockout_risk | P3 |

> [!NOTE]
> **MCP servers are optional for initial deployment.** The main FastAPI backend has direct database access and can function without MCP servers. Add MCPs incrementally as you expand agent capabilities.

## Files to Create

| File | Purpose |
|------|---------|
| `azure.yaml` | azd configuration |
| `infra/main.bicep` | Azure infrastructure |
| `infra/modules/*.bicep` | Bicep modules |
| `mcp-servers/ordering/` | MCP ordering server |
| `agents/demand_forecasting/model_service.py` | ✅ Created - Model loading |
| `services/workflow_service.py` | ✅ Created - Optimization workflow |
| `static/index.html` | ✅ Created - Dashboard UI |
| `scripts/setup.sh` | ✅ Created - Setup script |

---

## Dashboard: Central Intelligence Hub

### Design Philosophy

The dashboard is the **command center and intelligence panel** for the entire business and supply chain. It's not just a monitoring tool—it provides:

1. **Real-Time Visibility** - Live status of all workflows, inventory, and supplier performance
2. **Proactive Intelligence** - AI-generated insights and recommendations
3. **Quick Actions** - One-click approval/rejection of pending decisions
4. **Programmed Workflows** - Predefined automation patterns users can trigger

### Dashboard Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SUPPLY CHAIN INTELLIGENCE HUB                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  HEADER: Real-Time Status Bar                                       │   │
│  │  [🟢 System Health] [📦 12 Active Orders] [⚠️ 2 Alerts] [🔔 Pending] │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌───────────────────┬─────────────────────────────────────────────────┐   │
│  │                   │                                                  │   │
│  │  NAVIGATION       │   MAIN CONTENT AREA                             │   │
│  │                   │                                                  │   │
│  │  📊 Overview      │   (Dynamic based on selection)                  │   │
│  │  🔄 Workflows     │                                                  │   │
│  │  📦 Inventory     │                                                  │   │
│  │  🏭 Suppliers     │                                                  │   │
│  │  📈 Analytics     │                                                  │   │
│  │  ⚙️ Settings      │                                                  │   │
│  │                   │                                                  │   │
│  └───────────────────┴─────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  QUICK ACTIONS BAR                                                   │   │
│  │  [▶️ Run Optimization] [🚨 Emergency Restock] [📋 Generate Report]   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Programmed Workflows Panel

The Workflows page displays all available automated workflows as cards:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 PROGRAMMED WORKFLOWS                                        [+ New]    │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                │
│  │  📊 INVENTORY            │  │  🚨 DELAY RESPONSE        │                │
│  │     OPTIMIZATION         │  │                           │                │
│  │                          │  │  Status: ● Active         │                │
│  │  Status: ● Ready         │  │  Mode: Auto-Detect        │                │
│  │  Last Run: 2h ago        │  │  Triggers: 3 today        │                │
│  │  Next: Scheduled 6:00 AM │  │                           │                │
│  │                          │  │  [Configure] [View Logs]  │                │
│  │  [▶️ Run Now] [Schedule]  │  │                           │                │
│  └──────────────────────────┘  └──────────────────────────┘                │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                │
│  │  💰 PRICE MONITORING     │  │  📈 DEMAND FORECASTING    │                │
│  │                          │  │                           │                │
│  │  Status: ● Running       │  │  Status: ● Ready          │                │
│  │  Tracking: 156 ASINs     │  │  Model: XGBoost + Prophet │                │
│  │  Alerts: 4 price drops   │  │  Accuracy: 94.2%          │                │
│  │                          │  │                           │                │
│  │  [View Alerts] [Pause]   │  │  [▶️ Generate] [Retrain]   │                │
│  └──────────────────────────┘  └──────────────────────────┘                │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                │
│  │  🔔 APPROVAL QUEUE       │  │  📊 SUPPLIER SCORECARD    │                │
│  │                          │  │                           │                │
│  │  Pending: 3 orders       │  │  Status: ● Updated        │                │
│  │  Total Value: $12,450    │  │  Last Refresh: 1h ago     │                │
│  │  Oldest: 45 min          │  │  Suppliers: 24 tracked    │                │
│  │                          │  │                           │                │
│  │  [Review All] [Bulk OK]  │  │  [View Scores] [Export]   │                │
│  └──────────────────────────┘  └──────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Approval Modal Component

When human approval is required, a modal appears:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚠️ APPROVAL REQUIRED                                            [✕ Close] │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  ORDER DETAILS                                                        │ │
│  │                                                                        │ │
│  │  PO Number: PO-2024-0147                                              │ │
│  │  Supplier: AgroFresh Distributors                                     │ │
│  │  Total Value: $8,750.00                                               │ │
│  │  Urgency: MEDIUM (7 days stock remaining)                             │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │ ITEM          │ QTY  │ UNIT PRICE │ TOTAL    │ vs. LAST ORDER │  │ │
│  │  ├───────────────┼──────┼────────────┼──────────┼────────────────┤  │ │
│  │  │ Butter (1lb)  │ 500  │ $4.20      │ $2,100   │ ↑ 3.2%         │  │ │
│  │  │ Heavy Cream   │ 200  │ $6.50      │ $1,300   │ ↓ 1.5%         │  │ │
│  │  │ Whole Milk    │ 800  │ $3.80      │ $3,040   │ = Same         │  │ │
│  │  │ Eggs (dozen)  │ 350  │ $6.60      │ $2,310   │ ↑ 8.1%         │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                        │ │
│  │  AI RECOMMENDATION: ✅ Approve                                        │ │
│  │  "Prices are within 5% of historical average. Demand forecast         │ │
│  │   indicates reorder is necessary. Supplier reliability: 96%."         │ │
│  │                                                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────────┐ │
│  │ ✅ APPROVE   │  │ ❌ REJECT    │  │ ✏️ MODIFY (Edit quantities)     │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────────────┘ │
│                                                                             │
│  Comment (optional): [_______________________________________________]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Real-Time Updates via SSE

```python
# Dashboard receives live updates via Server-Sent Events
@app.get("/api/dashboard/events")
async def dashboard_events():
    """Stream all dashboard events."""
    async def event_generator():
        async for event in event_queue.subscribe():
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# Events emitted:
# - workflow.started
# - workflow.step_complete
# - workflow.approval_requested
# - workflow.completed
# - alert.new
# - inventory.update
# - supplier.delay_detected
```

---

## Phase 2: Supplier Delay Response Workflow

### Problem Statement

**Traditional Response to Supplier Delays:**
1. Buyer discovers delay (often late)
2. Buyer calls supplier, gets apology but no solution
3. Buyer manually searches for backup supplier
4. Premium pricing paid due to urgency
5. No penalties enforced on original supplier

**AI Agent Response:**
1. Agent detects delay via logistics tracking API
2. Immediately assesses stockout risk
3. Queries pre-approved backup suppliers
4. Secures bridge order at pre-negotiated emergency rate
5. Automatically applies late-delivery penalty to original invoice

### Business Value

| Metric | Traditional | With AI Agent | Value |
|--------|-------------|---------------|-------|
| Time-to-Recovery | 4-8 hours | 5-15 minutes | 📉 95% faster |
| Premium Paid | 30-50% markup | 15% (pre-negotiated) | 💰 50% savings on emergency costs |
| Penalty Recovery | Rarely enforced | Automatic | 💵 100% compliance |
| Buyer Time | 2-4 hours per incident | 5 min approval | 🧠 90% time saved |

### Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPPLIER DELAY RESPONSE WORKFLOW                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. EVENT TRIGGER: Shipment Delay Detected                          │   │
│  │                                                                      │   │
│  │  Sources:                                                            │   │
│  │  • Webhook from logistics provider (ShipStation, Project44)         │   │
│  │  • Polling of carrier tracking APIs                                  │   │
│  │  • Supplier notification email parser                                │   │
│  │                                                                      │   │
│  │  Trigger Conditions:                                                 │   │
│  │  • ETA change > 24 hours                                            │   │
│  │  • Explicit delay notification received                              │   │
│  │  • Carrier exception code detected                                   │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  2. IMPACT ASSESSMENT AGENT                                         │   │
│  │                                                                      │   │
│  │  Queries:                                                            │   │
│  │  • Current inventory levels for affected SKUs                        │   │
│  │  • Open sales orders / committed demand                              │   │
│  │  • Safety stock thresholds                                           │   │
│  │  • Historical consumption rate                                       │   │
│  │                                                                      │   │
│  │  Calculates:                                                         │   │
│  │  • Days of Stock (DOS) = Current Inv / Daily Demand                 │   │
│  │  • Stockout Date = Today + DOS                                      │   │
│  │  • Risk Level = GREEN (>14 days) / YELLOW (7-14) / RED (<7)         │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│           ┌───────────────────┼───────────────────┐                        │
│           │ GREEN             │ YELLOW            │ RED                    │
│           │ (No action)       │ (Prepare)         │ (Urgent)               │
│           ▼                   ▼                   ▼                        │
│  ┌────────────────┐  ┌────────────────────┐  ┌────────────────────────┐   │
│  │ LOG & MONITOR  │  │ BACKUP SOURCING    │  │ EMERGENCY EXECUTION    │   │
│  │                │  │ AGENT              │  │ AGENT                  │   │
│  │ • Log incident │  │                    │  │                        │   │
│  │ • Update ETA   │  │ • Query backups    │  │ • Auto-select backup   │   │
│  │ • Notify user  │  │ • Get quotes       │  │ • Create bridge PO     │   │
│  │ • Watch status │  │ • Present options  │  │ • Request expedited    │   │
│  │                │  │ • Await decision   │  │   approval             │   │
│  └────────────────┘  └─────────┬──────────┘  └───────────┬────────────┘   │
│                                │                         │                  │
│                                └────────────┬────────────┘                  │
│                                             ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  3. BACKUP SUPPLIER SELECTION                                        │   │
│  │                                                                      │   │
│  │  Criteria:                                                           │   │
│  │  • Pre-approved backup supplier exists                               │   │
│  │  • Emergency rate agreement in place                                 │   │
│  │  • Lead time meets urgency requirement                               │   │
│  │  • Sufficient capacity available                                     │   │
│  │                                                                      │   │
│  │  Output: Ranked list of backup options with pricing                  │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  4. HUMAN APPROVAL (Dashboard Modal)                                 │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ 🚨 URGENT: Supplier Delay Detected                          │    │   │
│  │  │                                                              │    │   │
│  │  │ Original Order: PO-2024-0142 (Dairy Fresh Inc)              │    │   │
│  │  │ Delay: 4 days (New ETA: Jan 15 → Jan 19)                    │    │   │
│  │  │ Impact: CRITICAL - Stockout in 3 days                       │    │   │
│  │  │                                                              │    │   │
│  │  │ RECOMMENDED ACTION:                                          │    │   │
│  │  │ Bridge order from AgroFresh (backup supplier)                │    │   │
│  │  │ • Quantity: 200 units Butter                                 │    │   │
│  │  │ • Price: $4.83/unit (15% emergency premium)                  │    │   │
│  │  │ • Delivery: 2 days                                           │    │   │
│  │  │ • Total: $966.00                                             │    │   │
│  │  │                                                              │    │   │
│  │  │ [✅ APPROVE BRIDGE ORDER]  [❌ REJECT]  [⏸️ WAIT]            │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  5. ORDER EXECUTION AGENT                                            │   │
│  │                                                                      │   │
│  │  If Approved:                                                        │   │
│  │  • Submit bridge order to backup supplier                            │   │
│  │  • Update inventory expectations                                     │   │
│  │  • Notify warehouse of incoming shipment                             │   │
│  │  • Adjust original order (partial cancel if needed)                  │   │
│  │                                                                      │   │
│  │  Always:                                                             │   │
│  │  • Apply late-delivery penalty to original supplier invoice          │   │
│  │  • Update supplier reliability score                                 │   │
│  │  • Log incident for performance tracking                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  6. POST-INCIDENT REPORTING                                          │   │
│  │                                                                      │   │
│  │  • Generate incident report                                          │   │
│  │  • Calculate total cost of disruption                                │   │
│  │  • Update supplier scorecard                                         │   │
│  │  • Recommend contract renegotiation if pattern detected             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema Extensions

```sql
-- Backup supplier registry with pre-negotiated emergency rates
CREATE TABLE backup_suppliers (
    id SERIAL PRIMARY KEY,
    primary_supplier_id INTEGER REFERENCES suppliers(id),
    backup_supplier_id INTEGER REFERENCES suppliers(id),
    asin VARCHAR(20),
    emergency_rate_multiplier DECIMAL(3,2) DEFAULT 1.15, -- 15% premium
    max_emergency_quantity INTEGER,
    lead_time_days INTEGER,
    min_order_value DECIMAL(10,2),
    contract_valid_until DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Shipment tracking
CREATE TABLE shipment_tracking (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(20) REFERENCES purchase_orders(po_number),
    carrier VARCHAR(50),
    tracking_number VARCHAR(100),
    original_eta DATE,
    current_eta DATE,
    status VARCHAR(30), -- 'on_time', 'delayed', 'exception', 'delivered'
    last_location VARCHAR(200),
    last_checked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Supplier incidents for performance tracking
CREATE TABLE supplier_incidents (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER REFERENCES suppliers(id),
    incident_type VARCHAR(50), -- 'late_delivery', 'quality_issue', 'short_ship', 'wrong_item'
    po_number VARCHAR(20) REFERENCES purchase_orders(po_number),
    original_eta DATE,
    actual_eta DATE,
    delay_days INTEGER,
    impact_level VARCHAR(10), -- 'GREEN', 'YELLOW', 'RED'
    penalty_applied DECIMAL(10,2) DEFAULT 0,
    backup_order_placed BOOLEAN DEFAULT FALSE,
    backup_po_number VARCHAR(20),
    backup_cost DECIMAL(10,2),
    resolved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Supplier performance scores (calculated/cached)
CREATE TABLE supplier_scores (
    supplier_id INTEGER PRIMARY KEY REFERENCES suppliers(id),
    on_time_delivery_rate DECIMAL(5,2), -- percentage
    quality_score DECIMAL(5,2),
    response_time_avg_hours DECIMAL(5,1),
    total_orders INTEGER,
    total_incidents INTEGER,
    last_incident_date DATE,
    reliability_tier VARCHAR(10), -- 'GOLD', 'SILVER', 'BRONZE', 'PROBATION'
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_shipment_status ON shipment_tracking(status);
CREATE INDEX idx_shipment_eta ON shipment_tracking(current_eta);
CREATE INDEX idx_incidents_supplier ON supplier_incidents(supplier_id);
CREATE INDEX idx_backup_primary ON backup_suppliers(primary_supplier_id);
```

### MCP Tools for Delay Response

```typescript
// mcp-servers/logistics/src/server.ts

// Tool: Track Shipment
server.tool(
  "track_shipment",
  "Get real-time tracking status for a shipment",
  {
    po_number: { type: "string", description: "Purchase order number" },
  },
  async ({ po_number }) => {
    const tracking = await logisticsService.getTracking(po_number);
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          tracking_number: tracking.trackingNumber,
          carrier: tracking.carrier,
          status: tracking.status,
          current_eta: tracking.currentEta,
          original_eta: tracking.originalEta,
          delay_days: tracking.delayDays,
          last_location: tracking.lastLocation,
        }),
      }],
    };
  }
);

// Tool: Calculate Stockout Risk
server.tool(
  "calculate_stockout_risk",
  "Assess impact of a delay on inventory levels",
  {
    asin: { type: "string", description: "Product ASIN" },
    delay_days: { type: "number", description: "Days of delay" },
  },
  async ({ asin, delay_days }) => {
    const inventory = await inventoryService.getCurrentLevel(asin);
    const dailyDemand = await forecastService.getDailyDemand(asin);
    const daysOfStock = inventory / dailyDemand;
    const stockoutDate = new Date();
    stockoutDate.setDate(stockoutDate.getDate() + daysOfStock);
    
    let riskLevel: 'GREEN' | 'YELLOW' | 'RED';
    if (daysOfStock > 14) riskLevel = 'GREEN';
    else if (daysOfStock > 7) riskLevel = 'YELLOW';
    else riskLevel = 'RED';
    
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          current_inventory: inventory,
          daily_demand: dailyDemand,
          days_of_stock: daysOfStock,
          stockout_date: stockoutDate.toISOString().split('T')[0],
          risk_level: riskLevel,
          recommendation: riskLevel === 'RED' 
            ? 'Immediate bridge order required'
            : riskLevel === 'YELLOW'
              ? 'Monitor closely, prepare backup'
              : 'No action needed',
        }),
      }],
    };
  }
);

// Tool: Query Backup Suppliers
server.tool(
  "query_backup_suppliers",
  "Get quotes from pre-approved backup suppliers",
  {
    asin: { type: "string", description: "Product ASIN" },
    quantity: { type: "number", description: "Quantity needed" },
    urgency: { type: "string", enum: ["standard", "expedited", "emergency"] },
  },
  async ({ asin, quantity, urgency }) => {
    const backups = await supplierService.getBackupQuotes(asin, quantity, urgency);
    return {
      content: [{
        type: "text",
        text: JSON.stringify(backups.map(b => ({
          supplier_id: b.supplierId,
          supplier_name: b.supplierName,
          unit_price: b.unitPrice,
          total_price: b.unitPrice * quantity,
          lead_time_days: b.leadTimeDays,
          rate_type: urgency,
          reliability_score: b.reliabilityScore,
        }))),
      }],
    };
  }
);

// Tool: Create Bridge Order
server.tool(
  "create_bridge_order",
  "Create an emergency bridge order to backup supplier",
  {
    supplier_id: { type: "string" },
    items: { type: "array" },
    original_po: { type: "string", description: "Original delayed PO number" },
    rate_type: { type: "string", enum: ["standard", "emergency"] },
  },
  async ({ supplier_id, items, original_po, rate_type }) => {
    const order = await orderService.createBridgeOrder({
      supplierId: supplier_id,
      items,
      originalPoNumber: original_po,
      rateType: rate_type,
    });
    
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          bridge_po_number: order.poNumber,
          status: "pending_approval",
          total: order.totalCost,
          expected_delivery: order.expectedDelivery,
        }),
      }],
    };
  }
);

// Tool: Apply Late Penalty
server.tool(
  "apply_late_penalty",
  "Apply late-delivery penalty to supplier invoice",
  {
    po_number: { type: "string" },
    delay_days: { type: "number" },
    penalty_rate: { type: "number", description: "Penalty rate per day (percentage)" },
  },
  async ({ po_number, delay_days, penalty_rate }) => {
    const result = await invoiceService.applyPenalty(po_number, delay_days, penalty_rate);
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          po_number,
          original_amount: result.originalAmount,
          penalty_amount: result.penaltyAmount,
          adjusted_amount: result.adjustedAmount,
          penalty_note: `Late delivery penalty: ${delay_days} days × ${penalty_rate}%`,
        }),
      }],
    };
  }
);
```

### Webhook Endpoint for Logistics Events

```python
# main.py - Add webhook handler

@app.post("/api/webhooks/logistics")
async def logistics_webhook(event: LogisticsEvent):
    """
    Receive shipment events from logistics providers.
    Triggers the delay response workflow when delays are detected.
    """
    if event.type == "shipment_delayed":
        # Calculate delay
        original_eta = event.original_eta
        new_eta = event.new_eta
        delay_days = (new_eta - original_eta).days
        
        if delay_days >= 1:  # Trigger threshold
            # Start delay response workflow
            workflow_id = await workflow_service.trigger_delay_response(
                po_number=event.po_number,
                delay_days=delay_days,
                reason=event.reason,
            )
            
            # Emit event to dashboard
            await emit_dashboard_event("supplier.delay_detected", {
                "po_number": event.po_number,
                "delay_days": delay_days,
                "workflow_id": workflow_id,
            })
            
            return {"status": "workflow_triggered", "workflow_id": workflow_id}
    
    return {"status": "logged"}
```

---

## OpenTelemetry Integration

### Why OpenTelemetry?

- **Distributed Tracing**: Track requests across agents and services
- **Metrics**: Monitor workflow performance, latency, success rates
- **Correlation**: Link agent actions to business outcomes
- **Debugging**: Pinpoint failures in complex multi-agent workflows

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY ARCHITECTURE                               │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ FastAPI     │  │ Forecast    │  │ Price       │  │ Ordering    │        │
│  │ Backend     │  │ Agent       │  │ Agent       │  │ Agent       │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                    │                                        │
│                                    ▼                                        │
│         ┌─────────────────────────────────────────────────┐                │
│         │           OpenTelemetry Collector               │                │
│         │                                                 │                │
│         │  • Receives traces, metrics, logs               │                │
│         │  • Processes and batches                        │                │
│         │  • Exports to backends                          │                │
│         └──────────────────────┬──────────────────────────┘                │
│                                │                                            │
│              ┌─────────────────┼─────────────────┐                         │
│              ▼                 ▼                 ▼                         │
│  ┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐             │
│  │ Azure Application │ │               │ │                   │             │
│  │ Insights          │ │               │ │                   │             │
│  └───────────────────┘ └───────────────┘ └───────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 1. Install Dependencies

```bash
# Add to pyproject.toml
pip install opentelemetry-api \
            opentelemetry-sdk \
            opentelemetry-exporter-otlp \
            opentelemetry-instrumentation-fastapi \
            opentelemetry-instrumentation-httpx \
            opentelemetry-instrumentation-sqlalchemy
```

#### 2. Telemetry Configuration

```python
# services/telemetry.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import os

def setup_telemetry(app):
    """Initialize OpenTelemetry for the application."""
    
    # Get OTLP endpoint from environment
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    service_name = os.getenv("OTEL_SERVICE_NAME", "supply-chain-agents")
    
    # Setup Tracing
    trace_provider = TracerProvider(
        resource=Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })
    )
    
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)
    
    # Setup Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint),
        export_interval_millis=60000,  # Every 60 seconds
    )
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    
    # Auto-instrument frameworks
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    
    return trace.get_tracer(service_name)

# Create tracer for manual instrumentation
tracer = trace.get_tracer("supply-chain-agents")
meter = metrics.get_meter("supply-chain-agents")

# Custom metrics
workflow_counter = meter.create_counter(
    name="workflow.executions",
    description="Number of workflow executions",
    unit="1",
)

workflow_duration = meter.create_histogram(
    name="workflow.duration",
    description="Workflow execution duration",
    unit="ms",
)

agent_calls = meter.create_counter(
    name="agent.calls",
    description="Number of agent tool calls",
    unit="1",
)
```

#### 3. Agent Instrumentation Decorator

```python
# services/telemetry.py (continued)
import functools
from opentelemetry import trace

def trace_agent_action(agent_name: str):
    """Decorator to trace agent actions with OpenTelemetry."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                name=f"{agent_name}.{func.__name__}",
                attributes={
                    "agent.name": agent_name,
                    "agent.action": func.__name__,
                }
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("agent.success", True)
                    agent_calls.add(1, {"agent": agent_name, "action": func.__name__, "status": "success"})
                    return result
                except Exception as e:
                    span.set_attribute("agent.success", False)
                    span.set_attribute("agent.error", str(e))
                    span.record_exception(e)
                    agent_calls.add(1, {"agent": agent_name, "action": func.__name__, "status": "error"})
                    raise
        return wrapper
    return decorator

# Usage in agents
class PriceMonitoringAgent:
    @trace_agent_action("PriceMonitoringAgent")
    async def get_supplier_prices(self, asin: str):
        # ... implementation
        pass
```

#### 4. Workflow Tracing

```python
# services/workflow_service.py
from services.telemetry import tracer, workflow_counter, workflow_duration
import time

class WorkflowService:
    async def run_optimization_workflow(self, product_filter=None):
        with tracer.start_as_current_span(
            name="workflow.inventory_optimization",
            attributes={
                "workflow.type": "inventory_optimization",
                "workflow.filter": product_filter or "all",
            }
        ) as span:
            start_time = time.time()
            workflow_id = str(uuid.uuid4())
            span.set_attribute("workflow.id", workflow_id)
            
            try:
                # Step 1: Forecast
                with tracer.start_as_current_span("step.forecast"):
                    forecast_result = await self._run_forecast(product_filter)
                
                # Step 2: Price Check
                with tracer.start_as_current_span("step.price_check"):
                    price_result = await self._check_prices(forecast_result)
                
                # Step 3: Generate Orders
                with tracer.start_as_current_span("step.generate_orders"):
                    orders = await self._generate_orders(price_result)
                
                # Record success
                duration_ms = (time.time() - start_time) * 1000
                workflow_counter.add(1, {"workflow": "inventory_optimization", "status": "success"})
                workflow_duration.record(duration_ms, {"workflow": "inventory_optimization"})
                
                return orders
                
            except Exception as e:
                workflow_counter.add(1, {"workflow": "inventory_optimization", "status": "error"})
                span.record_exception(e)
                raise
```

#### 5. Application Integration

```python
# main.py
from services.telemetry import setup_telemetry

app = FastAPI(title="Supply Chain Agents")

# Initialize OpenTelemetry on startup
@app.on_event("startup")
async def startup():
    setup_telemetry(app)
    # ... other startup tasks
```

### Docker Compose for Local Development

```yaml
# docker-compose.observability.yml
version: '3.8'

services:
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Prometheus metrics
    networks:
      - observability

  # Jaeger for trace visualization
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "14268:14268"  # Jaeger collector
    networks:
      - observability

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - observability

  # Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - observability

networks:
  observability:
    driver: bridge

volumes:
  grafana-data:
```

### OpenTelemetry Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  # For local development
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  
  prometheus:
    endpoint: "0.0.0.0:8889"
  
  # For Azure (production)
  azuremonitor:
    connection_string: ${APPLICATIONINSIGHTS_CONNECTION_STRING}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger, azuremonitor]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, azuremonitor]
```

### Azure Deployment with Application Insights

```bicep
// infra/modules/app-insights.bicep
param name string
param location string

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${name}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

output connectionString string = appInsights.properties.ConnectionString
output instrumentationKey string = appInsights.properties.InstrumentationKey
```

---

## Current Implementation Status

### ✅ Phase 1: Core Functionality (Completed)

- [x] Demand Forecasting Model (XGBoost + Statistical)
- [x] Model Service with Confidence Intervals
- [x] Workflow Service (Forecast + Price + Orders)
- [x] Live Dashboard with SSE Streaming
- [x] Setup Script for Easy Installation
- [x] Comprehensive README

### 🔄 Phase 2: Production Readiness (In Progress)

- [ ] **Dashboard Intelligence Hub**
  - [ ] Programmed Workflows Panel
  - [ ] Approval Modal Component
  - [ ] Real-time event streaming
  - [ ] Supplier Performance Dashboard
- [ ] **MCP Ordering Server Implementation**
  - [ ] create_purchase_order tool
  - [ ] submit_order tool
  - [ ] get_order_status tool
- [ ] **Human-in-the-Loop Approval System**
  - [ ] Checkpointing storage
  - [ ] Approval API endpoints
  - [ ] Dashboard approval UI

### 📋 Phase 3: Deployment & Observability (Planned)

- [ ] **OpenTelemetry Integration**
  - [ ] Tracing setup
  - [ ] Metrics collection
  - [ ] Agent instrumentation decorators
  - [ ] Grafana dashboards
- [ ] **Azure Infrastructure (Bicep)**
  - [ ] Container Apps environment
  - [ ] Application Insights
  - [ ] Key Vault for secrets
  - [ ] azd deployment workflow

### 🚀 Phase 4: Supply Chain Resilience (Planned)

- [ ] **Supplier Delay Response Workflow**
  - [ ] Logistics webhook integration
  - [ ] Impact Assessment Agent
  - [ ] Backup Sourcing Agent
  - [ ] Emergency Execution Agent
- [ ] **Database Extensions**
  - [ ] backup_suppliers table
  - [ ] shipment_tracking table
  - [ ] supplier_incidents table
  - [ ] supplier_scores table
- [ ] **New MCP Tools**
  - [ ] track_shipment
  - [ ] calculate_stockout_risk
  - [ ] query_backup_suppliers
  - [ ] create_bridge_order
  - [ ] apply_late_penalty

---

## Implementation Priority Matrix

| Feature | Business Impact | Technical Effort | Priority |
|---------|----------------|------------------|----------|
| Dashboard Approval Modal | High (blocks orders) | Medium | 🔴 P0 |
| OpenTelemetry | Medium (debugging) | Low | 🟡 P1 |
| Azure Deployment | High (production) | Medium | 🟡 P1 |
| Delay Response Workflow | Very High (resilience) | High | 🟢 P2 |
| Supplier Scorecard | Medium (insights) | Low | 🟢 P2 |

