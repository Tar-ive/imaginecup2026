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

```bash
# Initialize azd
azd init

# Provision infrastructure
azd provision

# Deploy
azd up

# Monitor
azd monitor
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `agents/forecasting/__init__.py` | Forecasting package |
| `agents/forecasting/prophet_model.py` | Prophet implementation |
| `agents/workflows/__init__.py` | Workflows package |
| `agents/workflows/inventory_optimization.py` | Main workflow |
| `agents/workflows/checkpoint_storage.py` | Checkpoint persistence |
| `agents/observability/telemetry.py` | OpenTelemetry setup |
| `infra/main.bicep` | Azure infrastructure |
| `azure.yaml` | azd configuration |
