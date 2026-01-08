- [ ]  Flow is after Agent Prompts but needs updating for non Chatbot UI

## SYSTEM ARCHITECTURE

```
┌───────────────────────────────────────────────────────────────────────┐
│                    INVENTORY OPTIMIZATION PLATFORM                     │
└───────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌───────────────┐       ┌───────────────┐     ┌───────────────┐
    │   WEB UI      │       │   WEB API     │     │  OBSERVABILITY│
    │  (Frontend)   │◄─────►│ Flask/FastAPI │────►│  & MONITORING │
    └───────────────┘       └───────────────┘     └───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │   MCP HOST ENVIRONMENT    │
                    │  (Tool Orchestration)     │
                    └───────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌───────────────┐       ┌───────────────┐     ┌───────────────┐
    │  DATA LAYER   │       │ AGENT LAYER   │     │   MCP TOOLS   │
    │               │       │ (Microsoft    │     │               │
    │ • POS Data    │       │  Agent        │     │ • POS Server  │
    │ • Supplier DB │◄─────►│  Framework)   │◄───►│ • Suppliers   │
    │ • Analytics   │       │               │     │ • Analytics   │
    │ • Documents   │       │               │     │ • Doc Intel   │
    │ • Weather     │       │               │     │ • Weather API │
    │ • Finance     │       │               │     │ • Finance     │
    └───────────────┘       └───────────────┘     └───────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌───────────────┐       ┌───────────────┐     ┌───────────────┐
    │ FORECASTING   │       │  REALTIME     │     │   ORDERING    │
    │    AGENT      │       │ PRICE MONITOR │     │    AGENT      │
    │               │       │    AGENT      │     │               │
    │ • Demand      │       │               │     │ • Cart        │
    │   Analysis    │──────►│ • Price       │────►│   Optimization│
    │ • Trend       │       │   Discovery   │     │ • ERP         │
    │   Projection  │       │ • Supplier    │     │   Integration │
    │ • Seasonality │       │   Comparison  │     │ • Order       │
    └───────────────┘       └───────────────┘     │   Execution   │
                                                  └───────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   LLM MODEL LAYER     │
                        │  Azure AI Foundry     │
                        └───────────────────────┘
```

---

## 1. ORCHESTRATOR AGENT

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR AGENT                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Role: Central coordination hub for multi-agent workflow    │
│                                                             │
│  Properties:                                                │
│  • session_id: Unique identifier for each user interaction  │
│  • conversation_state: Maintains context across turns       │
│  • routing_logic: Intent classification engine              │
│  • synthesis_engine: Response aggregation system            │
│                                                             │
│  Methods:                                                   │
│  • parse_user_intent(query) → intent_type                   │
│  • route_to_agent(intent) → agent_handoff                   │
│  • aggregate_results(agent_outputs) → final_response        │
│  • manage_state(session_data) → updated_context             │
│                                                             │
│  MCP Tools Accessed:                                        │
│  • Session management                                       │
│  • Logging & observability (OPTL)                           │
│  • Cross-agent communication                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Input Processing Logic:**

```python
def parse_user_intent(user_query):
    """
    Extract intent from natural language query

    Examples:
    - "Restock for Diwali" → DEMAND_FORECAST
    - "Find cheapest supplier" → PRICE_MONITORING
    - "Order 50 units coffee" → DIRECT_ORDER
    """
    intent_keywords = {
        'DEMAND_FORECAST': ['restock', 'predict', 'forecast', 'rush'],
        'PRICE_MONITORING': ['price', 'supplier', 'cost', 'cheapest'],
        'ORDER_EXECUTION': ['order', 'buy', 'purchase', 'procure']
    }

    # LLM-powered intent classification
    intent = classify_with_llm(user_query, intent_keywords)
    return intent
```

**State Management:**

```json
{
  "session_id": "sess_20260103_abc123",
  "timestamp": "2026-01-03T17:55:00Z",
  "user_query": "Restock for the upcoming Diwali rush week",
  "detected_intent": "DEMAND_FORECAST",
  "context": {
    "location": "Kathmandu",
    "business_type": "retail_coffee_shop",
    "historical_data_range": "2025-01-01 to 2026-01-03"
  },
  "workflow_state": "AGENT_HANDOFF_PENDING"
}
```

---

## 2. DEMAND FORECASTING AGENT

```
┌─────────────────────────────────────────────────────────────┐
│                  DEMAND FORECASTING AGENT                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Responsibility: Establishing "How much do we need?"        │
│                                                             │
│  Properties:                                                │
│  • forecasting_model: Time series + seasonality analysis   │
│  • correlation_engine: Event-demand mapping                │
│  • threshold_config: Safety stock and reorder points       │
│                                                             │
│  Methods:                                                   │
│  • extract_historical_baseline(date_range)                 │
│  • correlate_external_signals(location, date)              │
│  • apply_projection_thresholds(baseline, signals)          │
│  • generate_demand_score() → demand_signal                 │
│                                                             │
│  MCP Tools Used:                                            │
│  • document_intelligence_query() - Extract from PDFs       │
│  • search_events_api() - Festival/weather data            │
│  • analytics_mcp_server() - Historical trends             │
│  • trend_analyzer_tool() - Statistical projections        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tool Execution Pipeline

**Step 1: Historical Data Extraction**

```python
# MCP Tool Call
document_intelligence_query(
    input="Sales records 2025/01",
    source="Azure Document Intelligence",
    document_types=["invoices", "receipts", "sales_logs"]
)

# Output
{
    "monthly_sales": {
        "coffee_beans": {"avg_units": 120, "variance": 15},
        "metal_crafts": {"avg_units": 45, "variance": 8}
    },
    "baseline_demand": 0.65  # Normalized score
}
```

**Step 2: External Signal Correlation**

```python
# MCP Tool Call
search_events_api(
    location="Kathmandu",
    date_range="2026-01-05 to 2026-01-12",
    event_types=["festivals", "weather", "tourism"]
)

# Output
{
    "events": [
        {
            "name": "Diwali Week",
            "impact_score": 0.85,
            "expected_footfall_increase": "40%"
        },
        {
            "weather": "Clear, 20°C",
            "tourism_influx": "High",
            "impact_score": 0.75
        }
    ],
    "aggregated_signal": 0.80
}
```

**Step 3: Projection & Synthesis**

```python
# Internal Logic
def calculate_demand_score(baseline, external_signals, safety_factor=1.2):
    """
    Combine historical baseline with real-time signals

    Formula:
    demand_score = (baseline * 0.4) + (external_signals * 0.6) * safety_factor
    """
    raw_score = (baseline * 0.4) + (external_signals * 0.6)
    final_score = raw_score * safety_factor

    return {
        "demand_score": min(final_score, 1.0),
        "confidence": calculate_confidence(baseline, external_signals),
        "recommendation": categorize_demand(final_score)
    }
```

### Output: Demand Signal Context

```json
{
  "demand_score": 0.85,
  "confidence": 0.78,
  "recommendation": "HIGH_DEMAND",
  "target_items": [
    {
      "sku": "coffee_beans_arabica",
      "current_stock": 30,
      "qty_needed": 50,
      "urgency": "high",
      "reasoning": "Tourist influx + festival season + baseline trend"
    },
    {
      "sku": "metal_crafts_handmade",
      "current_stock": 10,
      "qty_needed": 20,
      "urgency": "medium",
      "reasoning": "Seasonal gift demand spike expected"
    }
  ],
  "forecast_period": "2026-01-05 to 2026-01-12",
  "risk_factors": ["supply_chain_delay", "weather_change"]
}
```

---

## 3. REALTIME PRICE MONITORING AGENT

```
┌─────────────────────────────────────────────────────────────┐
│              REALTIME PRICE MONITORING AGENT                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Responsibility: Finding the "Best place to buy"            │
│                                                             │
│  Properties:                                                │
│  • supplier_catalog: Real-time price database              │
│  • matching_algorithm: Fuzzy SKU matching                  │
│  • optimization_criteria: Price + delivery + quality       │
│                                                             │
│  Methods:                                                   │
│  • get_realtime_quotes(item_list)                          │
│  • fuzzy_match_suppliers(sku, catalogs)                    │
│  • rank_by_criteria(quotes, weights)                       │
│  • generate_supplier_matrix() → comparison_table           │
│                                                             │
│  MCP Tools Used:                                            │
│  • supplier_mcp_server() - Query supplier APIs             │
│  • get_realtime_quotes() - Live price feeds                │
│  • finance_mcp_server() - Currency conversion              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tool Execution Pipeline

**Step 1: Price Discovery**

```python
# MCP Tool Call
get_realtime_quotes({
    "items": [
        {"sku": "coffee_beans_arabica", "qty": 50},
        {"sku": "metal_crafts_handmade", "qty": 20}
    ],
    "suppliers": ["all"],  # Query all registered suppliers
    "delivery_location": "Kathmandu"
})

# Output
{
    "quotes": [
        {
            "item": "coffee_beans_arabica",
            "supplier": "Himalayan Java Trade Co.",
            "unit_price": 40.00,
            "currency": "NPR",
            "bulk_discount": "5% over 40 units",
            "delivery_sla": "24 hours",
            "quality_rating": 4.5,
            "stock_availability": "In Stock (200 units)"
        },
        {
            "item": "coffee_beans_arabica",
            "supplier": "Mountain Coffee Importers",
            "unit_price": 38.50,
            "currency": "NPR",
            "bulk_discount": "3% over 50 units",
            "delivery_sla": "48 hours",
            "quality_rating": 4.2,
            "stock_availability": "Low Stock (60 units)"
        }
    ]
}
```

**Step 2: Fuzzy Matching & Validation**

```python
def fuzzy_match_suppliers(target_sku, supplier_catalogs):
    """
    Handle SKU variations across suppliers

    Example:
    - Target: "coffee_beans_arabica"
    - Supplier A: "arabica_coffee_premium"
    - Supplier B: "coffee_arabica_grade_A"

    Uses Levenshtein distance + semantic embedding similarity
    """
    matches = []
    for catalog in supplier_catalogs:
        for item in catalog['items']:
            similarity = calculate_similarity(target_sku, item['sku'])
            if similarity > 0.75:
                matches.append({
                    'supplier': catalog['name'],
                    'matched_sku': item['sku'],
                    'confidence': similarity,
                    'details': item
                })

    return sorted(matches, key=lambda x: x['confidence'], reverse=True)
```

### Output: Supplier Matrix

```json
{
  "comparison_matrix": [
    {
      "item": "coffee_beans_arabica",
      "qty_requested": 50,
      "options": [
        {
          "rank": 1,
          "supplier": "Himalayan Java Trade Co.",
          "total_cost": 1900.00,
          "unit_price_after_discount": 38.00,
          "delivery_sla": "24h",
          "quality_score": 4.5,
          "overall_score": 0.92,
          "reasoning": "Best balance of price, speed, and quality"
        },
        {
          "rank": 2,
          "supplier": "Mountain Coffee Importers",
          "total_cost": 1850.00,
          "unit_price_after_discount": 37.00,
          "delivery_sla": "48h",
          "quality_score": 4.2,
          "overall_score": 0.85,
          "reasoning": "Lowest price but slower delivery"
        }
      ]
    },
    {
      "item": "metal_crafts_handmade",
      "qty_requested": 20,
      "options": [
        {
          "rank": 1,
          "supplier": "Patan Local Artisans",
          "total_cost": 4200.00,
          "unit_price": 210.00,
          "delivery_sla": "Same day",
          "quality_score": 4.8,
          "overall_score": 0.95,
          "reasoning": "Premium quality, local sourcing, fast delivery"
        }
      ]
    }
  ],
  "metadata": {
    "total_suppliers_queried": 8,
    "timestamp": "2026-01-03T18:00:15Z",
    "exchange_rates_applied": {"USD": 132.5, "INR": 1.6}
  }
}
```

---

## 4. AUTOMATED ORDERING AGENT

```
┌─────────────────────────────────────────────────────────────┐
│                  AUTOMATED ORDERING AGENT                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Responsibility: The "Closer" - Optimize & Execute          │
│                                                             │
│  Properties:                                                │
│  • cart_optimizer: Multi-objective optimization engine     │
│  • erp_connector: Microsoft Dynamics 365 / SAP integration │
│  • approval_workflow: Human-in-the-loop for large orders   │
│                                                             │
│  Methods:                                                   │
│  • simulate_cart_permutations(supplier_matrix, demand)     │
│  • calculate_total_cost_of_ownership(cart)                 │
│  • verify_delivery_constraints(suppliers, target_date)     │
│  • execute_erp_order(finalized_cart)                       │
│                                                             │
│  MCP Tools Used:                                            │
│  • simulate_cart_permutations() - Optimization logic       │
│  • execute_erp_order() - ERP API integration               │
│  • pos_mcp_server() - Update inventory records             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Optimization Logic

**Step 1: Cart Permutation Simulation**

```python
# MCP Tool Call
simulate_cart_permutations({
    "supplier_matrix": [...],  # From Price Monitoring Agent
    "demand_signal": {...},    # From Forecasting Agent
    "constraints": {
        "max_budget": 10000.00,
        "delivery_deadline": "2026-01-05",
        "min_quality_score": 4.0
    },
    "optimization_objectives": {
        "cost": 0.5,           # 50% weight
        "delivery_speed": 0.3,  # 30% weight
        "quality": 0.2         # 20% weight
    }
})

# Internal Processing
def optimize_cart(permutations, objectives):
    """
    Multi-objective optimization using weighted scoring

    For each permutation:
    1. Calculate total cost with discounts
    2. Verify all items meet delivery deadline
    3. Compute weighted score based on objectives
    4. Rank permutations
    """
    scored_permutations = []

    for perm in permutations:
        cost_score = normalize(perm['total_cost'], min_cost, max_cost)
        speed_score = calculate_delivery_score(perm['delivery_dates'])
        quality_score = average([item['quality'] for item in perm['items']])

        overall_score = (
            cost_score * objectives['cost'] +
            speed_score * objectives['delivery_speed'] +
            quality_score * objectives['quality']
        )

        scored_permutations.append({
            'permutation': perm,
            'score': overall_score,
            'breakdown': {
                'cost': cost_score,
                'speed': speed_score,
                'quality': quality_score
            }
        })

    return sorted(scored_permutations, key=lambda x: x['score'], reverse=True)
```

**Step 2: ERP Integration & Order Execution**

```python
# MCP Tool Call
execute_erp_order({
    "order_type": "PURCHASE_ORDER",
    "erp_system": "Microsoft Dynamics 365",
    "line_items": [
        {
            "sku": "coffee_beans_arabica",
            "supplier_id": "SUP_001",
            "qty": 50,
            "unit_price": 38.00,
            "total": 1900.00
        },
        {
            "sku": "metal_crafts_handmade",
            "supplier_id": "SUP_045",
            "qty": 20,
            "unit_price": 210.00,
            "total": 4200.00
        }
    ],
    "payment_terms": "Net 30",
    "delivery_address": "Thamel, Kathmandu",
    "expected_delivery": "2026-01-05"
})

# Response
{
    "status": "ORDER_CREATED",
    "order_id": "PO-998877",
    "erp_confirmation_number": "DYN365-2026-00123",
    "total_spend": 6100.00,
    "savings_achieved": 145.00,
    "discount_breakdown": {
        "bulk_discount": 95.00,
        "early_payment_discount": 50.00
    },
    "expected_delivery_date": "2026-01-05",
    "tracking_links": [
        "https://tracking.supplier1.com/...",
        "https://tracking.supplier2.com/..."
    ]
}
```

### Output: Order Manifest

```json
{
  "order_manifest": {
    "order_id": "PO-998877",
    "status": "PROCESSED",
    "created_at": "2026-01-03T18:05:30Z",
    "financial_summary": {
      "subtotal": 6245.00,
      "discounts_applied": 145.00,
      "final_total": 6100.00,
      "currency": "NPR",
      "savings_percentage": "2.3%"
    },
    "delivery_schedule": [
      {
        "supplier": "Himalayan Java Trade Co.",
        "items": ["coffee_beans_arabica"],
        "eta": "2026-01-04T16:00:00Z",
        "tracking": "HJT-KTM-20260104-001"
      },
      {
        "supplier": "Patan Local Artisans",
        "items": ["metal_crafts_handmade"],
        "eta": "2026-01-03T20:00:00Z",
        "tracking": "PLA-SAME-DAY-789"
      }
    ],
    "approval_status": "AUTO_APPROVED",
    "approval_reason": "Within budget threshold ($10,000)",
    "next_actions": [
      "Monitor delivery tracking",
      "Update inventory system upon receipt",
      "Verify quality on arrival"
    ]
  },
  "workflow_metadata": {
    "total_processing_time": "5.2 seconds",
    "agents_invoked": ["Orchestrator", "Forecasting", "PriceMonitoring", "Ordering"],
    "mcp_calls_made": 12,
    "llm_tokens_consumed": 3420
  }
}
```

---

## AGENT IMPLEMENTATION PROMPTS

This section contains the complete LLM prompts and instructions for each specialized agent in the system. These prompts define the agent’s behavior, decision-making logic, and response patterns.

### Real-Time Price Monitoring Agent ⭐

**Name:** `PriceMonitoringAgent`

**Description:** Monitors supplier pricing changes and analyzes impact on product/service profitability in real-time

**System Prompt:**

```
You are a real-time price monitoring agent for a supply chain management system.
Your role is to detect supplier price changes and immediately assess their impact on profitability.

Key responsibilities:
- Process and extract pricing data from vendor invoices, quotes, and catalogs using OCR
- Cross-reference new prices against existing cost structures (BOMs, cost cards, pricing sheets)
- Calculate the precise impact on individual product/service margins
- Compare current supplier prices against alternative suppliers in real-time
- Generate actionable alerts when price changes threaten profitability

When a price change is detected:
1. Quantify the exact impact: "Raw material X increased 15% ($3.20 → $3.68/unit)"
2. Identify affected products/services: "Impacts: Product A, Product B, Service Package C"
3. Calculate new margins: "Product A margin dropped from 18% to 2%"
4. Provide specific recommendations with numbers:
   - "Raise price by $1.50 to restore 18% margin"
   - "Switch to Supplier B (saves $0.48/unit, maintains margin)"
   - "Reformulate/redesign to use 20% less of this material"
   - "Renegotiate contract terms or volume discounts"

Always prioritize urgent alerts (margins below 5%) and provide clear, immediately actionable solutions.
Be precise with numbers, transparent about tradeoffs, and proactive in suggesting alternatives.
Consider industry context (retail, manufacturing, healthcare, hospitality, etc.) when calculating impact.

You have access to these tools: 
- supplier_mcp_server() - Query supplier APIs for current pricing
- get_realtime_quotes() - Live price feeds from multiple suppliers
- finance_mcp_server() - Currency conversion and financial calculations
```

**MCP Tools Available:**
- `supplier_mcp_server()` - Query supplier APIs for current pricing

• 

     `instructions = "Use the AI supplier search tool for current supplier related information."`

- `get_realtime_quotes()` - Live price feeds from multiple suppliers
- `finance_mcp_server()` - Currency conversion and financial calculations

---

### Demand Forecasting Agent

**Name:** `DemandForecastingAgent`

**Description:** Predicts future inventory demand using sales history, external data, and pattern recognition

**System Prompt:**

```
You are a demand forecasting agent for a supply chain management system.
Your role is to predict what inventory will be needed and when, preventing both waste and stockouts.

Key responsibilities:
- Analyze historical sales/consumption data to identify patterns
- Integrate external factors: weather, economic indicators, local events, holidays, industry trends, seasonality
- Generate precise quantity forecasts with confidence intervals
- Explain the reasoning behind predictions for transparency and trust
- Identify anomalies and unusual demand patterns
- Adjust forecasts dynamically as new data arrives

When generating forecasts:
1. Provide specific quantities: "Next week: 470 units Product A, 230 units Product B, 600 units Product C"
2. Show percentage changes: "+20% due to seasonal demand, -15% due to market slowdown"
3. Explain your reasoning: "Increased forecast because: (1) Holiday period starts Monday +12%, (2) Promotional campaign launching +8%"
4. Flag uncertainty: "Medium confidence (limited historical data for this scenario)"
5. Highlight edge cases: "Industry conference on Saturday may increase demand 40%"

Adapt to different business contexts:
- Retail: SKU-level demand by location and channel
- Manufacturing: Raw material needs based on production schedules
- Healthcare: Medical supply consumption by department
- Hospitality: Amenity and service demand by occupancy rates

Use clear time horizons (next 3 days, next week, next month) and always explain variance from normal patterns. Always specify dates when you do so. 
Be conservative to avoid waste but proactive enough to prevent stockouts.
Present forecasts in order of confidence level and business impact.

You have access to these tools : 
- document_intelligence_query() - Extract historical data from documents via Azure Document Intelligence 
- search_events_api() - Query festival/holiday calendars, weather data, local events
- analytics_mcp_server() - Run trend analysis and statistical models
- trend_analyzer_tool() - Time series forecasting with seasonality
- pos_mcp_server() - Access historical sales data

Your task is to take all of these tools, and perform them in a specified format -> 
1. Define Objectives: Specify why the forecast is needed (e.g., inventory vs. staffing).
2. Data Collection & Cleaning: Use pos_mcp_server to pull sales and document_intelligence_query to digitize legacy records. Standardized cleaning involves removing outliers like "viral spikes" or stock-out periods.
3. Product Segmentation: Divide SKUs into categories (e.g., "Stable Core," "Highly Seasonal," "New Launch").
4. Model Selection: Choose models based on segment (e.g., Holt-Winters for seasonal items using your trend_analyzer_tool or XGBoost/LSTM for promo-driven items via analytics_mcp_server).
5. Baseline Generation: Create a baseline forecast using trend_analyzer_tool to account for seasonality.
6. Collaborative Enrichment: Adjust the baseline based on upcoming events from search_events_api (e.g., an upcoming festival expected to lift sales).
7. Accuracy Measurement: Use standard 2026 metrics: MAPE (Mean Absolute Percentage Error) and WAPE (Weighted Absolute Percentage Error) to evaluate performance.

```

**MCP Tools Available:**
- `document_intelligence_query()` - Extract historical data from documents via Azure Document Intelligence 
- `search_events_api()` - Query festival/holiday calendars, weather data, local events
- `analytics_mcp_server()` - Run trend analysis and statistical models
- `trend_analyzer_tool()` - Time series forecasting with seasonality
- `pos_mcp_server()` - Access historical sales data

Handoff Output should be a JSON schema with consistent data each run. We should try atleast 3 runs to see that the agent handoff has right data schema or not. 

---

### Automated Ordering Agent

**Name:** `AutomatedOrderingAgent`

**Description:** Autonomously generates and executes purchase orders with multi-supplier optimization

**System Prompt:**

```
You are an automated ordering agent for a supply chain management system.
Your role is to create, optimize, and execute purchase orders without human intervention.

Key responsibilities:
- Generate purchase orders based on demand forecasts and inventory levels
- Optimize across multiple suppliers considering price, reliability, delivery time, quality, and payment terms
- Adapt to real-time disruptions (delays, stockouts, price spikes, capacity constraints)
- Execute orders via appropriate channels (email, API, EDI, phone, procurement portals)
- Track order status and escalate issues requiring human attention

When creating orders:
1. Specify exact requirements: "Order 500 units SKU-123 from Supplier A, delivery by Tuesday 8 AM"
2. Show optimization logic: "Selected Supplier A: $3.20/unit vs Supplier B $3.45/unit, 98% on-time rate, Net-30 terms"
3. Build in safety margins: "Ordering 10% buffer due to forecast uncertainty"
4. Respect constraints: "Minimum order quantity 150 units met by bundling SKU-123 + SKU-456"

When handling disruptions:
- Act autonomously: "Supplier A delayed, automatically switched to Supplier B (+$0.15/unit)"
- Explain decisions: "Accepted higher cost to maintain production/service schedule"
- Escalate critical issues: "All suppliers out of stock - HUMAN REVIEW NEEDED"

Context-aware ordering:
- Manufacturing: Order raw materials aligned with production runs
- Retail: Multi-location ordering with distribution center optimization
- Healthcare: Priority ordering for critical supplies with compliance tracking
- Service industries: Coordinate supply delivery with service schedules

Always confirm order placement, track delivery status, and maintain an audit trail.
Optimize for total cost of ownership (price + reliability + quality + lead time), not just unit price.
Be proactive, decisive, and transparent about tradeoffs.

You have access to these tools. 
- simulate_cart_permutations() - Multi-objective optimization engine
- execute_erp_order() - Integrate with Microsoft Dynamics 365 / SAP
- pos_mcp_server() - Update inventory records post-order
- supplier_mcp_server() - Place orders via supplier APIs
- finance_mcp_server() - Process payments and validate budgets

You will order what the historic weekly averages are without asking for human Intervention, and if the demand forecast agent gives you a higher quote confirm with humans and wait for his inputs before continuing. DONOT OVERSTEP THIS RULE. 
```

**MCP Tools Available:**
- `simulate_cart_permutations()` - Multi-objective optimization engine
- `execute_erp_order()` - Integrate with Microsoft Dynamics 365 / SAP
- `pos_mcp_server()` - Update inventory records post-order
- `supplier_mcp_server()` - Place orders via supplier APIs
- `finance_mcp_server()` - Process payments and validate budgets

---

---

## WORKFLOW: STEP-BY-STEP EXECUTION

### START

```
┌─ STEP 1: User Query Ingestion
│  • User sees the need for restock due to Diwali: "Restock for the upcoming Diwali rush week"
│  • Orchestrator receives query via Web API
│  • Session initialized: sess_20260103_abc123
│
│
├─ STEP 2: Agent Handoff to Forecasting Agent
│  │
│  ├─ Sub-step 3.1: Historical Data Extraction
│  │  • MCP Call: document_intelligence_query()
│  │  • Extract sales records from PDFs
│  │  • Baseline demand calculated: 0.65
│  │
│  ├─ Sub-step 3.2: External Signal Correlation
│  │  • MCP Call: search_events_api()
│  │  • Diwali impact score: 0.85
│  │  • Weather/tourism boost: 0.75
│  │
│  └─ Sub-step 3.3: Demand Projection
│     • Apply forecasting algorithm
│     • Generate demand score: 0.85 (HIGH)
│     • Identify target items: coffee_beans (50), metal_crafts (20)
│
├─ STEP 4: Agent Handoff to Price Monitoring Agent
│  │
│  ├─ Sub-step 4.1: Supplier Query
│  │  • MCP Call: get_realtime_quotes()
│  │  • Query 8 suppliers in parallel
│  │  • Collect 15 price quotes
│  │
│  ├─ Sub-step 4.2: Fuzzy Matching
│  │  • Match SKUs across supplier catalogs
│  │  • Validate stock availability
│  │
│  └─ Sub-step 4.3: Ranking & Comparison
│     • Apply multi-criteria scoring
│     • Generate supplier matrix
│     • Best option: Himalayan Java Trade (score: 0.92)
│
├─ STEP 5: Agent Handoff to Ordering Agent
│  │
│  ├─ Sub-step 5.1: Cart Optimization
│  │  • MCP Call: simulate_cart_permutations()
│  │  • Test 24 supplier combinations
│  │  • Optimize for cost (50%), speed (30%), quality (20%)
│  │  • Selected cart: Total $6100, ETA 2026-01-05
│  │
│  ├─ Sub-step 5.2: Delivery Verification
│  │  • Verify all items meet deadline
│  │  • Check supplier SLAs
│  │  • Confirm stock availability
│  │
│  └─ Sub-step 5.3: ERP Order Execution
│     • MCP Call: execute_erp_order()
│     • Create PO in Dynamics 365
│     • Order ID: PO-998877
│     • Status: PROCESSED
│
├─ STEP 6: Result Aggregation (Back to Orchestrator)
│  • Collect outputs from all 3 agents
│  • Synthesize final response
│  • Format for user interface
│
└─ STEP 7: User Response Delivery
   • Stream final summary to UI
   • Display order confirmation
   • Provide tracking information
   • Update inventory dashboard

END
```

---

| **Scenario** | **Intent Type** | **Primary Agent** | **Expected Outcome** |
| --- | --- | --- | --- |
| “Restock for festival week” | DEMAND_FORECAST | Forecasting → Price → Order | Automated restocking order |
| “Find cheapest coffee supplier” | PRICE_MONITORING | Price Monitoring | Supplier comparison table |
| “Order 100 units coffee beans” | DIRECT_ORDER | Ordering | Direct PO creation |
| “Predict next month demand” | ANALYTICS | Forecasting | Demand forecast report |
| “Compare supplier A vs B” | PRICE_MONITORING | Price Monitoring | Side-by-side comparison |

### Parameter Tuning

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIGURABLE PARAMETERS                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Demand Forecasting:                                        │
│  • baseline_weight: 0.4 (40% historical data)              │
│  • external_signal_weight: 0.6 (60% real-time signals)     │
│  • safety_factor: 1.2 (20% buffer stock)                   │
│  • confidence_threshold: 0.70                              │
│                                                             │
│  Price Monitoring:                                          │
│  • fuzzy_match_threshold: 0.75                             │
│  • max_suppliers_to_query: 10                              │
│  • price_validity_window: 24 hours                         │
│                                                             │
│  Ordering Optimization:                                     │
│  • cost_weight: 0.5                                        │
│  • delivery_speed_weight: 0.3                              │
│  • quality_weight: 0.2                                     │
│  • auto_approval_threshold: $10,000                        │
│                                                             │
│  System-wide:                                               │
│  • session_timeout: 30 minutes                             │
│  • max_retries_per_mcp_call: 3                             │
│  • llm_temperature: 0.3 (deterministic)                    │
│  • observability_level: DEBUG                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP SERVER INTEGRATION MAP

### MCP Servers & Their Responsibilities

```
┌────────────────────────────────────────────────────────────┐
│                      MCP ECOSYSTEM                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. POS MCP Server                                         │
│     • Read current inventory levels                        │
│     • Update stock after orders                            │
│     • Query historical sales data                          │
│     Tools: get_inventory(), update_stock(), sales_history()│
│                                                            │
│  2. Supplier MCP Server                                    │
│     • Query supplier catalogs                              │
│     • Get real-time pricing                                │
│     • Check stock availability                             │
│     Tools: get_catalog(), get_quotes(), check_availability()│
│                                                            │
│  3. Analytics MCP Server                                   │
│     • Run trend analysis                                   │
│     • Calculate forecasting models                         │
│     • Generate business insights                           │
│     Tools: trend_analyzer(), forecast_model(), insights()  │
│                                                            │
│  4. OCR/Document Intelligence MCP Server                   │
│     • Extract data from invoices                           │
│     • Parse supplier catalogs (PDFs)                       │
│     • Read unstructured documents                          │
│     Tools: extract_invoice(), parse_catalog(), ocr_scan()  │
│                                                            │
│  5. Weather & Events MCP Server                            │
│     • Fetch weather forecasts                              │
│     • Query festival/holiday calendars                     │
│     • Tourism data APIs                                    │
│     Tools: get_weather(), search_events(), tourism_stats() │
│                                                            │
│  6. Finance MCP Server                                     │
│     • Currency conversion                                  │
│     • Payment processing                                   │
│     • Budget compliance checks                             │
│     Tools: convert_currency(), process_payment(), budget() │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Agent-to-MCP Mapping

| **Agent** | **MCP Servers Used** | **Primary Tools** |
| --- | --- | --- |
| Orchestrator | All (logging) | session_manager(), log_metrics() |
| Forecasting | Analytics, OCR, Weather | trend_analyzer(), extract_invoice(), search_events() |
| Price Monitoring | Supplier, Finance | get_quotes(), convert_currency() |
| Ordering | POS, Finance | update_stock(), process_payment() |

---

## VISUALIZATIONS & METRICS

### Key Performance Indicators

```
┌─────────────────────────────────────────────────────────────┐
│                     SYSTEM METRICS                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Forecasting Accuracy:                                      │
│  • MAPE (Mean Absolute Percentage Error): < 15%            │
│  • Demand prediction hit rate: > 80%                       │
│  • False positive rate: < 10%                              │
│                                                             │
│  Cost Optimization:                                         │
│  • Average savings per order: 5-10%                        │
│  • Budget adherence: > 95%                                 │
│  • Supplier diversification index: 0.6-0.8                 │
│                                                             │
│  Operational Efficiency:                                    │
│  • End-to-end workflow time: < 10 seconds                  │
│  • MCP call success rate: > 99%                            │
│  • Agent handoff latency: < 500ms                          │
│                                                             │
│  User Experience:                                           │
│  • Query understanding accuracy: > 90%                     │
│  • Response completeness score: > 85%                      │
│  • User satisfaction (CSAT): > 4.2/5.0                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Dashboards That Can Be Created

1. **Demand Forecast Dashboard**
    - Time series plots of predicted vs actual demand
    - Confidence intervals visualization
    - Event correlation heatmap
2. **Supplier Comparison Dashboard**
    - Real-time price tracking charts
    - Quality vs cost scatter plots
    - Delivery SLA compliance tracker
3. **Order Execution Dashboard**
    - Order status pipeline visualization
    - Cost savings over time
    - Budget utilization gauge
4. **System Performance Dashboard**
    - Agent execution timeline
    - MCP call latency histogram
    - Token consumption analytics

---

## TASK ROADMAP

### Task 1: Foundation Setup

```
✓ Set up Azure AI Foundry environment
✓ Configure MCP servers (POS, Supplier, Analytics, OCR, Weather, Finance)
✓ Implement basic Web API (Flask/FastAPI)
✓ Build Orchestrator Agent skeleton
✓ Milestone: Can route simple queries to agents
```

### Task 2: Core Agent Development

```
✓ Implement Demand Forecasting Agent
  - Integrate document_intelligence_query()
  - Build trend_analyzer_tool()
  - Test with sample data

✓ Implement Price Monitoring Agent
  - Connect to Supplier MCP
  - Build fuzzy matching logic
  - Create supplier comparison matrix

✓ Milestone: Can generate demand forecasts and price comparisons
```

### Task 3: Ordering & Integration

```
✓ Implement Automated Ordering Agent
  - Build cart optimization engine
  - Integrate with Dynamics 365/SAP
  - Add approval workflow

✓ Connect all agents via Orchestrator
✓ End-to-end workflow testing
✓ Milestone: Complete order flow working
```

### Task 4: Observability & Refinement

```
✓ Add OTLP monitoring
✓ Implement logging hooks
✓ Build performance dashboards
✓ Optimize MCP call patterns
✓ Milestone: Production-ready system
```

### Task 5: UI & Polish

```
✓ Build Web UI (Next.js/React)
✓ Add real-time status updates
✓ Create user documentation
✓ Load testing & optimization
✓ Milestone: Launch-ready application
```

---

## QUICK START CHECKLIST

```
□ Understand the multi-agent architecture
  └─ Why: Separate concerns for scalability

□ Set up Azure environment
  └─ Azure AI Foundry, App Services, Document Intelligence

□ Install MCP servers
  └─ Use npx commands or custom deployments

□ Build Orchestrator first (simplest)
  └─ Get intent routing working

□ Add one agent at a time
  └─ Forecasting → Price Monitoring → Ordering

□ Test with sample data
  └─ Use mock MCP responses initially

□ Integrate real MCP servers
  └─ Replace mocks with actual API calls

□ Add observability
  └─ OTLP, Application Insights, custom dashboards

□ Build Web UI
  └─ Next.js template from Azure

□ Deploy to production
  └─ App Service, Container Apps, or AKS
```

---

## KEY INSIGHTS FOR SUCCESS

### 1. START WITH MOCKS, THEN GO REAL

```
Don't wait for all MCP servers to be ready
Build with mock data first
Swap in real integrations incrementally
```

### 2. AGENT ISOLATION IS KEY

```
Each agent should be independently testable
Use clear contracts for inter-agent communication
Orchestrator handles ALL coordination
```

### 3. OBSERVABILITY FROM DAY 1

```
Log every MCP call
Track agent execution times
Monitor LLM token usage
Set up alerts for failures
```

### 4. OPTIMIZE FOR USER INTENT

```
The better your intent classification, the smoother the workflow
Invest time in prompt engineering for the Orchestrator
Test with diverse user queries
```

### 5. HANDLE FAILURES GRACEFULLY

```
MCP servers will timeout or fail
Implement retry logic with exponential backoff
Provide fallback responses to users
Never expose raw errors to UI
```

### 6. COST AWARENESS

```
LLM calls are expensive
Cache frequently used queries
Use smaller models for classification tasks
Monitor token consumption
```

---

## FINAL DELIVERABLES

```
┌─────────────────────────────────────────────────────────────┐
│                   PROJECT DELIVERABLES                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SOURCE CODE REPOSITORY                                  │
│     • /src/agents/ (Orchestrator, Forecasting, Price, Order)│
│     • /src/mcp/ (MCP server implementations)               │
│     • /src/api/ (Flask/FastAPI backend)                    │
│     • /src/ui/ (Next.js frontend)                          │
│     • /tests/ (Unit tests, integration tests)              │
│     • /docs/ (Architecture diagrams, API specs)            │
│                                                             │
│  2. DEPLOYMENT PACKAGE                                      │
│     • docker-compose.yml (local development)               │
│     • azure.yaml (Azure deployment config)                 │
│     • infra/ (Bicep templates for Azure resources)         │
│     • .env.sample (Environment variables template)         │
│                                                             │
│  3. DOCUMENTATION                                           │
│     • README.md (Getting started guide)                    │
│     • ARCHITECTURE.md (This document)                      │
│     • API_REFERENCE.md (API endpoints)                     │
│     • MCP_INTEGRATION.md (MCP server guide)                │
│     • DEPLOYMENT.md (Deployment instructions)              │
│                                                             │
│  4. DEMO MATERIALS                                          │
│     • Sample user queries                                   │
│     • Video walkthrough                                     │
│     • Performance benchmarks                                │
│     • Cost analysis report                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## APPENDIX: EXAMPLE QUERIES & RESPONSES

### Example 1: Basic Restocking Query

**User Input:**

```
"Restock for the upcoming Diwali rush week"
```

**System Response:**

```
Based on historical data and upcoming Diwali festivities (Jan 5-12),
I recommend restocking:

1. Coffee Beans (Arabica): 50 units
   - Current stock: 30 units
   - Predicted demand: High (0.85 confidence)
   - Best supplier: Himalayan Java Trade Co.
   - Cost: $1,900 (with 5% bulk discount)
   - Delivery: 24 hours

2. Metal Crafts (Handmade): 20 units
   - Current stock: 10 units
   - Predicted demand: Medium (0.72 confidence)
   - Best supplier: Patan Local Artisans
   - Cost: $4,200
   - Delivery: Same day

Total investment: $6,100
Estimated savings: $145 (2.3%)
Order ID: PO-998877

Shall I proceed with this order?
```

### Example 2: Price Comparison Query

**User Input:**

```
"Compare coffee suppliers for 100 units"
```

**System Response:**

```
Here's a comparison of coffee suppliers for 100 units:

┌──────────────────────┬──────────┬──────────┬──────────┐
│ Supplier             │ Price    │ Delivery │ Quality  │
├──────────────────────┼──────────┼──────────┼──────────┤
│ Himalayan Java       │ $3,700   │ 24h      │ ⭐⭐⭐⭐½  │
│ Mountain Coffee      │ $3,600   │ 48h      │ ⭐⭐⭐⭐   │
│ Local Roasters Co.   │ $3,850   │ Same day │ ⭐⭐⭐⭐⭐  │
└──────────────────────┴──────────┴──────────┴──────────┘

Recommendation: Himalayan Java (Best balance of price, speed, quality)

Would you like to place an order?
```

### Example 3: Demand Forecast Query

**User Input:**

```
"Predict demand for next month"
```

**System Response:**

```
February 2026 Demand Forecast:

📈 Overall Trend: Moderate growth (+12%)

Top Items to Stock:
1. Coffee Beans: 180 units (up from 160)
   Drivers: Post-festival tourism, pleasant weather

2. Tea Varieties: 95 units (stable)
   Drivers: Winter season continuation

3. Local Handicrafts: 65 units (up from 50)
   Drivers: Valentine's Day gifting surge

4. Packaged Snacks: 120 units (down from 140)
   Drivers: Post-holiday diet consciousness

🔍 Risk Factors:
- Potential supply chain delays (Holi festival week)
- Weather uncertainty (monsoon preparedness)

Recommended restocking date: Jan 28, 2026
Estimated budget: $18,500
```

---

## TECHNICAL ARCHITECTURE DETAILS

### Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     TECHNOLOGY STACK                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend:                                                  │
│  • Next.js 14+ (React 18)                                  │
│  • TypeScript                                              │
│  • Tailwind CSS                                            │
│  • Recharts (for visualizations)                           │
│                                                             │
│  Backend:                                                   │
│  • Python 3.11+                                            │
│  • FastAPI (async API framework)                           │
│  • Microsoft Agent Framework                               │
│  • Pydantic (data validation)                              │
│                                                             │
│  MCP Layer:                                                 │
│  • Custom MCP servers (TypeScript/Python)                  │
│  • MCP SDK                                                 │
│  • STDIO/HTTP protocols                                    │
│                                                             │
│  LLM Provider:                                              │
│  • Azure AI Foundry (Claude Sonnet 4.5 / GPT-4)           │
│  • Azure OpenAI Service                                    │
│                                                             │
│  Infrastructure:                                            │
│  • Azure App Service / Container Apps                      │
│  • Azure Cosmos DB (session storage)                       │
│  • Azure Document Intelligence                             │
│  • Azure Application Insights (observability)              │
│  • Azure API Management (optional)                         │
│                                                             │
│  DevOps:                                                    │
│  • GitHub Actions (CI/CD)                                  │
│  • Docker / Docker Compose                                 │
│  • Azure Bicep (IaC)                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌─────────┐       ┌──────────┐       ┌───────────┐
│  User   │──────►│  Web UI  │──────►│  Web API  │
│         │◄──────│ (Next.js)│◄──────│ (FastAPI) │
└─────────┘       └──────────┘       └───────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │  Orchestrator    │
                                  │     Agent        │
                                  └──────────────────┘
                                            │
                  ┌─────────────────────────┼─────────────────────────┐
                  │                         │                         │
                  ▼                         ▼                         ▼
         ┌────────────────┐       ┌────────────────┐       ┌────────────────┐
         │ Forecasting    │       │ Price Monitor  │       │   Ordering     │
         │    Agent       │       │     Agent      │       │     Agent      │
         └────────────────┘       └────────────────┘       └────────────────┘
                  │                         │                         │
                  │                         │                         │
         ┌────────┴────────┐       ┌────────┴────────┐       ┌────────┴────────┐
         │                 │       │                 │       │                 │
         ▼                 ▼       ▼                 ▼       ▼                 ▼
    ┌────────┐      ┌─────────┐ ┌────────┐    ┌────────┐ ┌────────┐    ┌────────┐
    │Analytics│      │  OCR    │ │Supplier│    │Finance │ │  POS   │    │Finance │
    │  MCP   │      │  MCP    │ │  MCP   │    │  MCP   │ │  MCP   │    │  MCP   │
    └────────┘      └─────────┘ └────────┘    └────────┘ └────────┘    └────────┘
         │                 │           │              │         │              │
         └─────────────────┴───────────┴──────────────┴─────────┴──────────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │   LLM Provider   │
                                  │ (Azure Foundry)  │
                                  └──────────────────┘
```

---

## SECURITY & COMPLIANCE

### Security Best Practices

```
┌─────────────────────────────────────────────────────────────┐
│                   SECURITY CHECKLIST                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Authentication & Authorization:                            │
│  ✓ Azure AD / Entra ID integration                         │
│  ✓ API key rotation for MCP servers                        │
│  ✓ Role-based access control (RBAC)                        │
│  ✓ JWT tokens for session management                       │
│                                                             │
│  Data Protection:                                           │
│  ✓ Encrypt PII (supplier contracts, pricing)               │
│  ✓ Use Azure Key Vault for secrets                         │
│  ✓ HTTPS/TLS for all communications                        │
│  ✓ Data residency compliance (GDPR, local laws)            │
│                                                             │
│  Input Validation:                                          │
│  ✓ Sanitize user queries (prevent injection)               │
│  ✓ Validate MCP responses                                  │
│  ✓ Rate limiting on API endpoints                          │
│  ✓ Input length restrictions                               │
│                                                             │
│  Monitoring & Auditing:                                     │
│  ✓ Log all order executions                                │
│  ✓ Track approval workflows                                │
│  ✓ Alert on anomalous spending patterns                    │
│  ✓ Regular security scans (SAST/DAST)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

