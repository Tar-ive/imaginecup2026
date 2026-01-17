# Negotiation Agent Integration Guide for Dev B

**Created**: 2026-01-16
**For**: NegotiationAgent implementation and UCP integration
**MCP Tools Version**: 1.0
**Author**: Dev A

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MCP Tools Reference](#mcp-tools-reference)
4. [NegotiationAgent Implementation](#negotiationagent-implementation)
5. [UCP Protocol Integration](#ucp-protocol-integration)
6. [A2A Agent Communication](#a2a-agent-communication)
7. [Complete Workflow Example](#complete-workflow-example)
8. [Testing & Debugging](#testing--debugging)
9. [Production Considerations](#production-considerations)

---

## Overview

This guide covers how to integrate the **Negotiation & AP2 Payment MCP tools** into the NegotiationAgent using:

- **MCP (Model Context Protocol)**: Agent-to-tool communication
- **UCP (Universal Commerce Protocol)**: End-to-end commerce lifecycle
- **A2A (Agent-to-Agent)**: Inter-agent communication via Magentic
- **AP2 (Agent Payments)**: Secure payment mandate execution

### What's Already Built

Dev A has implemented:
- ✅ 6 Negotiation MCP tools (supplier_data MCP server)
- ✅ 3 AP2 Payment MCP tools (finance_data MCP server)
- ✅ Database models and migrations
- ✅ Negotiation service with intelligent supplier simulation
- ✅ AP2 service with RS256 JWT signing
- ✅ Automated test suite

### What You Need to Build

- 🔨 NegotiationAgent class (Magentic-based)
- 🔨 UCP protocol integration
- 🔨 A2A communication patterns
- 🔨 Agent orchestration logic
- 🔨 Frontend integration endpoints

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│                  /api/negotiate endpoint                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              NegotiationAgent (Magentic)                     │
│  - Orchestrates workflow                                     │
│  - Calls MCP tools                                           │
│  - A2A communication with other agents                       │
└──────┬──────────────────────────┬───────────────────────────┘
       │                          │
       │ MCP HTTP POST            │ MCP HTTP POST
       ▼                          ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Supplier MCP Server │  │  Finance MCP Server  │
│  (port 3001)         │  │  (port 3003)         │
│                      │  │                      │
│  6 Negotiation Tools │  │  3 AP2 Payment Tools │
└──────┬───────────────┘  └──────┬───────────────┘
       │                          │
       ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Azure SQL Database                        │
│  - negotiation_sessions, negotiation_rounds                  │
│  - payment_mandates, suppliers, purchase_orders              │
└─────────────────────────────────────────────────────────────┘
```

### Protocol Stack

| Layer | Protocol | Purpose | Implementation |
|-------|----------|---------|----------------|
| **Agent-to-Tool** | MCP | Agent calls tools via HTTP | `requests.post()` to MCP servers |
| **Agent-to-Agent** | A2A | Inter-agent communication | Magentic framework handles routing |
| **Agent-to-Payment** | AP2 | Payment mandate execution | MCP tools in finance_data server |
| **Commerce Lifecycle** | UCP | End-to-end workflow orchestration | NegotiationAgent implements UCP patterns |

---

## MCP Tools Reference

### Supplier Data MCP Server (port 3001)

Base URL: `http://localhost:3001/mcp`

#### 1. create_negotiation_session

**Purpose**: Initialize a new negotiation session with target pricing

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "create_negotiation_session",
    "arguments": {
      "items": [
        {
          "sku": "B00ABC123",
          "quantity": 500,
          "description": "Premium Butter 1lb blocks"
        }
      ],
      "target_price": 4.50,
      "target_discount_percent": 10,
      "max_rounds": 3
    }
  }
}
```

**Output**:
```json
{
  "session_id": "NEG-1737072000-ABC123",
  "status": "open",
  "items": [...],
  "target_price": 4.50,
  "max_rounds": 3,
  "current_round": 0,
  "created_at": "2026-01-16T10:30:00Z"
}
```

#### 2. request_supplier_quote

**Purpose**: Request quote from a specific supplier (simulated instant response)

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "request_supplier_quote",
    "arguments": {
      "session_id": "NEG-1737072000-ABC123",
      "supplier_id": "SUP-001",
      "urgency": "high"
    }
  }
}
```

**Output**:
```json
{
  "round_id": "RND-123",
  "session_id": "NEG-1737072000-ABC123",
  "supplier_id": "SUP-001",
  "supplier_name": "Premium Dairy Co.",
  "round_number": 1,
  "offered_price": 5.20,
  "total_value": 2600.00,
  "status": "pending",
  "simulated": true,
  "created_at": "2026-01-16T10:31:00Z"
}
```

#### 3. compare_negotiation_offers

**Purpose**: Compare all offers and rank suppliers

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "compare_negotiation_offers",
    "arguments": {
      "session_id": "NEG-1737072000-ABC123",
      "criteria": "total_cost"
    }
  }
}
```

**Output**:
```json
{
  "session_id": "NEG-1737072000-ABC123",
  "offers_count": 3,
  "best_offer": {
    "supplier_id": "SUP-002",
    "supplier_name": "Budget Supplies Inc.",
    "offered_price": 4.80,
    "total_value": 2400.00
  },
  "ranked_suppliers": [
    {"supplier_id": "SUP-002", "offered_price": 4.80, ...},
    {"supplier_id": "SUP-001", "offered_price": 5.20, ...},
    {"supplier_id": "SUP-003", "offered_price": 5.50, ...}
  ]
}
```

#### 4. submit_counter_offer

**Purpose**: Submit counter-offer to supplier with justification

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "submit_counter_offer",
    "arguments": {
      "session_id": "NEG-1737072000-ABC123",
      "supplier_id": "SUP-002",
      "counter_price": 4.50,
      "justification": "Target budget constraint. Competitor quoted 10% less."
    }
  }
}
```

**Output**:
```json
{
  "round_id": "RND-124",
  "session_id": "NEG-1737072000-ABC123",
  "supplier_id": "SUP-002",
  "round_number": 2,
  "our_counter_price": 4.50,
  "their_response_price": 4.65,
  "discount_requested_percent": 6.25,
  "status": "countered",
  "total_value": 2325.00,
  "simulated": true,
  "created_at": "2026-01-16T10:32:00Z"
}
```

#### 5. accept_supplier_offer

**Purpose**: Accept supplier's offer and close negotiation

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "accept_supplier_offer",
    "arguments": {
      "session_id": "NEG-1737072000-ABC123",
      "supplier_id": "SUP-002",
      "notes": "Best offer after negotiation. Meets budget requirements."
    }
  }
}
```

**Output**:
```json
{
  "session_id": "NEG-1737072000-ABC123",
  "winning_supplier_id": "SUP-002",
  "winning_supplier_name": "Budget Supplies Inc.",
  "final_price": 4.65,
  "total_value": 2325.00,
  "rounds_completed": 2,
  "status": "completed",
  "completed_at": "2026-01-16T10:33:00Z"
}
```

#### 6. get_negotiation_status

**Purpose**: Get complete negotiation history

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_negotiation_status",
    "arguments": {
      "session_id": "NEG-1737072000-ABC123"
    }
  }
}
```

**Output**:
```json
{
  "session_id": "NEG-1737072000-ABC123",
  "status": "completed",
  "current_round": 2,
  "max_rounds": 3,
  "target_price": 4.50,
  "winning_supplier_id": "SUP-002",
  "final_price": 4.65,
  "rounds": [
    {
      "round_number": 1,
      "supplier_id": "SUP-002",
      "offer_type": "initial",
      "offered_price": 4.80,
      "status": "pending"
    },
    {
      "round_number": 2,
      "supplier_id": "SUP-002",
      "offer_type": "counter",
      "offered_price": 4.65,
      "counter_price": 4.50,
      "status": "accepted"
    }
  ]
}
```

---

### Finance Data MCP Server (port 3003)

Base URL: `http://localhost:3003/mcp`

#### 7. create_payment_mandate

**Purpose**: Create signed AP2 payment mandate (JWT with RS256)

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "create_payment_mandate",
    "arguments": {
      "session_id": "NEG-1737072000-ABC123",
      "supplier_id": "SUP-002",
      "amount": 2325.00,
      "currency": "USD",
      "order_details": {
        "items": [...],
        "total": 2325.00,
        "negotiation_session": "NEG-1737072000-ABC123"
      },
      "user_consent": true
    }
  }
}
```

**Output**:
```json
{
  "mandate_id": "MAN-1737072180-XYZ789",
  "session_id": "NEG-1737072000-ABC123",
  "supplier_id": "SUP-002",
  "amount": 2325.00,
  "currency": "USD",
  "mandate_type": "checkout",
  "status": "created",
  "signed_mandate": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "signature_algorithm": "RS256",
  "expires_at": "2026-01-17T10:33:00Z",
  "created_at": "2026-01-16T10:33:00Z"
}
```

#### 8. verify_payment_mandate

**Purpose**: Verify JWT signature and mandate validity

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "verify_payment_mandate",
    "arguments": {
      "mandate_id": "MAN-1737072180-XYZ789"
    }
  }
}
```

**Output**:
```json
{
  "mandate_id": "MAN-1737072180-XYZ789",
  "valid": true,
  "status": "created",
  "amount": 2325.00,
  "currency": "USD",
  "supplier_id": "SUP-002",
  "expires_at": "2026-01-17T10:33:00Z",
  "decoded_payload": {
    "iss": "SupplyMind",
    "sub": "SUP-002",
    "aud": "ap2-payment-gateway",
    "mandate_type": "checkout",
    "amount": 2325.00,
    "currency": "USD",
    "exp": 1737158000
  }
}
```

#### 9. execute_payment_with_mandate

**Purpose**: Execute payment using verified mandate

**Input**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "execute_payment_with_mandate",
    "arguments": {
      "mandate_id": "MAN-1737072180-XYZ789",
      "po_number": "PO-2026-001"
    }
  }
}
```

**Output**:
```json
{
  "mandate_id": "MAN-1737072180-XYZ789",
  "status": "executed",
  "amount": 2325.00,
  "currency": "USD",
  "supplier_id": "SUP-002",
  "po_number": "PO-2026-001",
  "executed_at": "2026-01-16T10:34:00Z",
  "message": "Payment executed successfully"
}
```

---

## NegotiationAgent Implementation

### Agent Class Structure

```python
# negotiation_agent.py

from magentic import Agent, tool, UserMessage, AssistantMessage
from typing import List, Dict, Any, Optional
import requests
import json

# MCP server URLs
SUPPLIER_MCP_URL = "http://localhost:3001/mcp"
FINANCE_MCP_URL = "http://localhost:3003/mcp"

class NegotiationAgent(Agent):
    """
    Agent responsible for supplier negotiation and payment execution.

    Implements UCP (Universal Commerce Protocol) patterns for:
    - Multi-round negotiation
    - Supplier comparison
    - AP2 payment mandate creation
    - Order fulfillment

    Uses A2A protocol to communicate with:
    - InventoryAgent: Check stock levels
    - BudgetAgent: Verify budget approval
    - OrderAgent: Create purchase orders
    """

    def __init__(self):
        super().__init__(
            model="gpt-4",
            name="NegotiationAgent",
            description="Handles supplier negotiation and payment execution"
        )
        self.current_session_id = None
        self.negotiation_history = []

    # =====================================================================
    # MCP Tool Wrappers
    # =====================================================================

    def call_mcp_tool(
        self,
        base_url: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool via HTTP POST.

        Args:
            base_url: MCP server URL (SUPPLIER_MCP_URL or FINANCE_MCP_URL)
            tool_name: Name of the tool to call
            arguments: Tool arguments as dict

        Returns:
            Parsed JSON response from tool

        Raises:
            Exception: If tool call fails
        """
        try:
            response = requests.post(base_url, json={
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }, timeout=10)

            response.raise_for_status()
            result = response.json()

            if result.get("isError"):
                error_msg = result["content"][0]["text"]
                raise Exception(f"Tool error: {error_msg}")

            return json.loads(result["content"][0]["text"])

        except Exception as e:
            raise Exception(f"Failed to call {tool_name}: {str(e)}")

    # =====================================================================
    # Negotiation Methods
    # =====================================================================

    def create_negotiation(
        self,
        items: List[Dict[str, Any]],
        target_price: Optional[float] = None,
        target_discount_percent: Optional[float] = None,
        max_rounds: int = 3
    ) -> Dict[str, Any]:
        """
        Create a new negotiation session.

        Args:
            items: List of items to negotiate [{"sku": "...", "quantity": 100, "description": "..."}]
            target_price: Target unit price (optional)
            target_discount_percent: Target discount % (optional)
            max_rounds: Maximum negotiation rounds (default: 3)

        Returns:
            Session info with session_id
        """
        result = self.call_mcp_tool(SUPPLIER_MCP_URL, "create_negotiation_session", {
            "items": items,
            "target_price": target_price,
            "target_discount_percent": target_discount_percent,
            "max_rounds": max_rounds
        })

        self.current_session_id = result["session_id"]
        self.negotiation_history.append({
            "action": "create_session",
            "session_id": self.current_session_id,
            "result": result
        })

        return result

    def request_quotes(
        self,
        supplier_ids: List[str],
        urgency: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Request quotes from multiple suppliers.

        Args:
            supplier_ids: List of supplier IDs ["SUP-001", "SUP-002", ...]
            urgency: "low" | "medium" | "high"

        Returns:
            List of quote responses
        """
        if not self.current_session_id:
            raise Exception("No active negotiation session")

        quotes = []
        for supplier_id in supplier_ids:
            quote = self.call_mcp_tool(SUPPLIER_MCP_URL, "request_supplier_quote", {
                "session_id": self.current_session_id,
                "supplier_id": supplier_id,
                "urgency": urgency
            })
            quotes.append(quote)

            self.negotiation_history.append({
                "action": "request_quote",
                "supplier_id": supplier_id,
                "result": quote
            })

        return quotes

    def compare_offers(
        self,
        criteria: str = "total_cost"
    ) -> Dict[str, Any]:
        """
        Compare all received offers and rank suppliers.

        Args:
            criteria: "total_cost" | "unit_price" | "quality_score"

        Returns:
            Comparison with best_offer and ranked_suppliers
        """
        if not self.current_session_id:
            raise Exception("No active negotiation session")

        comparison = self.call_mcp_tool(SUPPLIER_MCP_URL, "compare_negotiation_offers", {
            "session_id": self.current_session_id,
            "criteria": criteria
        })

        self.negotiation_history.append({
            "action": "compare_offers",
            "result": comparison
        })

        return comparison

    def counter_offer(
        self,
        supplier_id: str,
        counter_price: float,
        justification: str
    ) -> Dict[str, Any]:
        """
        Submit counter-offer to a supplier.

        Args:
            supplier_id: Supplier to counter
            counter_price: Our counter-offer price per unit
            justification: Reason for counter-offer

        Returns:
            Supplier's response to counter-offer
        """
        if not self.current_session_id:
            raise Exception("No active negotiation session")

        result = self.call_mcp_tool(SUPPLIER_MCP_URL, "submit_counter_offer", {
            "session_id": self.current_session_id,
            "supplier_id": supplier_id,
            "counter_price": counter_price,
            "justification": justification
        })

        self.negotiation_history.append({
            "action": "counter_offer",
            "supplier_id": supplier_id,
            "result": result
        })

        return result

    def accept_offer(
        self,
        supplier_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Accept a supplier's offer and close negotiation.

        Args:
            supplier_id: Supplier to accept
            notes: Optional acceptance notes

        Returns:
            Final negotiation result
        """
        if not self.current_session_id:
            raise Exception("No active negotiation session")

        result = self.call_mcp_tool(SUPPLIER_MCP_URL, "accept_supplier_offer", {
            "session_id": self.current_session_id,
            "supplier_id": supplier_id,
            "notes": notes
        })

        self.negotiation_history.append({
            "action": "accept_offer",
            "supplier_id": supplier_id,
            "result": result
        })

        return result

    # =====================================================================
    # AP2 Payment Methods
    # =====================================================================

    def create_payment_mandate(
        self,
        supplier_id: str,
        amount: float,
        currency: str,
        order_details: Dict[str, Any],
        user_consent: bool = False
    ) -> Dict[str, Any]:
        """
        Create AP2 payment mandate with cryptographic signature.

        Args:
            supplier_id: Supplier to pay
            amount: Payment amount
            currency: Currency code (e.g., "USD")
            order_details: Order information
            user_consent: User has consented to payment

        Returns:
            Mandate with signed JWT
        """
        if not self.current_session_id:
            raise Exception("No active negotiation session")

        result = self.call_mcp_tool(FINANCE_MCP_URL, "create_payment_mandate", {
            "session_id": self.current_session_id,
            "supplier_id": supplier_id,
            "amount": amount,
            "currency": currency,
            "order_details": order_details,
            "user_consent": user_consent
        })

        self.negotiation_history.append({
            "action": "create_mandate",
            "result": result
        })

        return result

    def verify_payment_mandate(
        self,
        mandate_id: str
    ) -> Dict[str, Any]:
        """
        Verify payment mandate signature and validity.

        Args:
            mandate_id: Mandate to verify

        Returns:
            Verification result with decoded payload
        """
        result = self.call_mcp_tool(FINANCE_MCP_URL, "verify_payment_mandate", {
            "mandate_id": mandate_id
        })

        return result

    def execute_payment(
        self,
        mandate_id: str,
        po_number: str
    ) -> Dict[str, Any]:
        """
        Execute payment using verified mandate.

        Args:
            mandate_id: Mandate to execute
            po_number: Purchase order number

        Returns:
            Payment execution result
        """
        result = self.call_mcp_tool(FINANCE_MCP_URL, "execute_payment_with_mandate", {
            "mandate_id": mandate_id,
            "po_number": po_number
        })

        self.negotiation_history.append({
            "action": "execute_payment",
            "result": result
        })

        return result

    # =====================================================================
    # High-Level Workflow Methods
    # =====================================================================

    def negotiate_and_purchase(
        self,
        items: List[Dict[str, Any]],
        target_price: Optional[float] = None,
        max_rounds: int = 3,
        supplier_ids: Optional[List[str]] = None,
        auto_accept_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute complete negotiation and purchase workflow.

        This implements the UCP (Universal Commerce Protocol) pattern:
        1. Create negotiation session
        2. Request quotes from suppliers
        3. Compare offers
        4. Counter-offer if needed
        5. Accept best offer
        6. Create payment mandate
        7. Execute payment

        Args:
            items: Items to purchase
            target_price: Target unit price
            max_rounds: Max negotiation rounds
            supplier_ids: List of suppliers to contact (if None, uses all active)
            auto_accept_threshold: Auto-accept if price <= this value

        Returns:
            Complete workflow result
        """
        workflow_result = {
            "status": "in_progress",
            "steps": []
        }

        try:
            # Step 1: Create session
            session = self.create_negotiation(
                items=items,
                target_price=target_price,
                max_rounds=max_rounds
            )
            workflow_result["steps"].append({
                "step": "create_session",
                "status": "success",
                "data": session
            })

            # Step 2: Request quotes
            if not supplier_ids:
                # TODO: Call InventoryAgent to get suppliers for these items
                supplier_ids = ["SUP-001", "SUP-002", "SUP-003"]

            quotes = self.request_quotes(supplier_ids=supplier_ids, urgency="high")
            workflow_result["steps"].append({
                "step": "request_quotes",
                "status": "success",
                "data": {"quotes_count": len(quotes)}
            })

            # Step 3: Compare offers
            comparison = self.compare_offers(criteria="total_cost")
            best_offer = comparison["best_offer"]
            workflow_result["steps"].append({
                "step": "compare_offers",
                "status": "success",
                "data": best_offer
            })

            # Step 4: Decide whether to counter-offer
            should_counter = False
            if target_price and best_offer["offered_price"] > target_price:
                should_counter = True

            if auto_accept_threshold and best_offer["offered_price"] <= auto_accept_threshold:
                should_counter = False

            final_supplier = best_offer["supplier_id"]
            final_price = best_offer["offered_price"]
            final_total = best_offer["total_value"]

            if should_counter:
                # Step 4a: Counter-offer
                counter_result = self.counter_offer(
                    supplier_id=final_supplier,
                    counter_price=target_price,
                    justification=f"Target budget constraint. Seeking {target_price}/unit."
                )
                workflow_result["steps"].append({
                    "step": "counter_offer",
                    "status": "success",
                    "data": counter_result
                })

                # Update final price based on counter-offer response
                final_price = counter_result["their_response_price"]
                final_total = counter_result["total_value"]

            # Step 5: Accept offer
            acceptance = self.accept_offer(
                supplier_id=final_supplier,
                notes="Best offer. Proceeding with payment."
            )
            workflow_result["steps"].append({
                "step": "accept_offer",
                "status": "success",
                "data": acceptance
            })

            # Step 6: Create payment mandate (requires user consent)
            # NOTE: In production, you should wait for user approval here
            mandate = self.create_payment_mandate(
                supplier_id=final_supplier,
                amount=final_total,
                currency="USD",
                order_details={
                    "items": items,
                    "total": final_total,
                    "negotiation_session": self.current_session_id,
                    "supplier": final_supplier
                },
                user_consent=True  # In production: get this from user
            )
            workflow_result["steps"].append({
                "step": "create_mandate",
                "status": "success",
                "data": {
                    "mandate_id": mandate["mandate_id"],
                    "amount": mandate["amount"]
                }
            })

            # Step 7: Verify mandate
            verification = self.verify_payment_mandate(mandate["mandate_id"])
            if not verification["valid"]:
                raise Exception("Payment mandate verification failed")

            workflow_result["steps"].append({
                "step": "verify_mandate",
                "status": "success",
                "data": verification
            })

            # Step 8: Execute payment
            # TODO: Generate PO number via OrderAgent
            po_number = f"PO-{int(time.time())}"

            payment = self.execute_payment(
                mandate_id=mandate["mandate_id"],
                po_number=po_number
            )
            workflow_result["steps"].append({
                "step": "execute_payment",
                "status": "success",
                "data": payment
            })

            # Success!
            workflow_result["status"] = "completed"
            workflow_result["summary"] = {
                "session_id": self.current_session_id,
                "supplier_id": final_supplier,
                "final_price": final_price,
                "total_amount": final_total,
                "mandate_id": mandate["mandate_id"],
                "po_number": po_number
            }

            return workflow_result

        except Exception as e:
            workflow_result["status"] = "failed"
            workflow_result["error"] = str(e)
            return workflow_result
```

---

## UCP Protocol Integration

### UCP Session Lifecycle

```python
# ucp_integration.py

from typing import Dict, Any, Optional
from negotiation_agent import NegotiationAgent

class UCPNegotiationSession:
    """
    UCP (Universal Commerce Protocol) session manager.

    Implements the complete commerce lifecycle:
    1. Discovery: Find suppliers for items
    2. Negotiation: Multi-round price negotiation
    3. Commitment: Create payment mandate
    4. Settlement: Execute payment
    5. Fulfillment: Trigger order processing
    """

    def __init__(self):
        self.agent = NegotiationAgent()
        self.session_state = {
            "phase": "init",  # init → discovery → negotiation → commitment → settlement → fulfilled
            "negotiation_session_id": None,
            "selected_supplier": None,
            "payment_mandate_id": None,
            "purchase_order_id": None
        }

    def execute_commerce_lifecycle(
        self,
        items: List[Dict[str, Any]],
        user_budget: float,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute full UCP commerce lifecycle.

        Args:
            items: Items to purchase
            user_budget: Maximum budget
            user_id: User identifier for consent tracking

        Returns:
            Lifecycle result with all phases
        """
        result = {"phases": []}

        # Phase 1: Discovery
        self.session_state["phase"] = "discovery"
        # TODO: Integrate with InventoryAgent to find suppliers
        suppliers = ["SUP-001", "SUP-002", "SUP-003"]
        result["phases"].append({
            "name": "discovery",
            "status": "completed",
            "suppliers_found": len(suppliers)
        })

        # Phase 2: Negotiation
        self.session_state["phase"] = "negotiation"
        negotiation_result = self.agent.negotiate_and_purchase(
            items=items,
            target_price=user_budget / sum(item["quantity"] for item in items),
            supplier_ids=suppliers,
            max_rounds=3
        )

        if negotiation_result["status"] != "completed":
            return {
                "status": "failed",
                "phase": "negotiation",
                "error": negotiation_result.get("error")
            }

        result["phases"].append({
            "name": "negotiation",
            "status": "completed",
            "summary": negotiation_result["summary"]
        })

        self.session_state["negotiation_session_id"] = negotiation_result["summary"]["session_id"]
        self.session_state["selected_supplier"] = negotiation_result["summary"]["supplier_id"]
        self.session_state["payment_mandate_id"] = negotiation_result["summary"]["mandate_id"]

        # Phase 3: Commitment (mandate created in negotiate_and_purchase)
        self.session_state["phase"] = "commitment"
        result["phases"].append({
            "name": "commitment",
            "status": "completed",
            "mandate_id": self.session_state["payment_mandate_id"]
        })

        # Phase 4: Settlement (payment executed in negotiate_and_purchase)
        self.session_state["phase"] = "settlement"
        result["phases"].append({
            "name": "settlement",
            "status": "completed",
            "po_number": negotiation_result["summary"]["po_number"]
        })

        # Phase 5: Fulfillment
        self.session_state["phase"] = "fulfillment"
        # TODO: Trigger OrderAgent to process PO
        result["phases"].append({
            "name": "fulfillment",
            "status": "pending",
            "po_number": negotiation_result["summary"]["po_number"]
        })

        return {
            "status": "completed",
            "lifecycle_result": result,
            "session_state": self.session_state
        }
```

---

## A2A Agent Communication

### Using Magentic for Agent-to-Agent

```python
# a2a_communication.py

from magentic import Agent, AgentMessage
from negotiation_agent import NegotiationAgent

class SupplyChainOrchestrator(Agent):
    """
    Orchestrator that coordinates multiple agents using A2A protocol.

    Agents involved:
    - NegotiationAgent: Handle supplier negotiation and payment
    - InventoryAgent: Check stock levels and suggest suppliers
    - BudgetAgent: Verify budget approval
    - OrderAgent: Create and track purchase orders
    """

    def __init__(self):
        super().__init__(
            model="gpt-4",
            name="SupplyChainOrchestrator",
            description="Coordinates supply chain operations across agents"
        )

        self.negotiation_agent = NegotiationAgent()
        # TODO: Initialize other agents
        # self.inventory_agent = InventoryAgent()
        # self.budget_agent = BudgetAgent()
        # self.order_agent = OrderAgent()

    async def process_purchase_request(
        self,
        items: List[Dict[str, Any]],
        user_id: str,
        budget: float
    ) -> Dict[str, Any]:
        """
        Process purchase request using A2A coordination.

        Flow:
        1. Ask InventoryAgent: Do we have stock? If not, which suppliers?
        2. Ask BudgetAgent: Is budget approved for this amount?
        3. Call NegotiationAgent: Negotiate with suppliers
        4. Call OrderAgent: Create PO and track fulfillment

        Args:
            items: Items to purchase
            user_id: User making request
            budget: Maximum budget

        Returns:
            Orchestration result
        """
        orchestration_log = []

        # Step 1: Check inventory (A2A call to InventoryAgent)
        # In Magentic, agents can send messages to each other
        inventory_msg = AgentMessage(
            role="user",
            content=f"Check stock for items: {items}"
        )
        # inventory_response = await self.inventory_agent.send(inventory_msg)
        # For now, simulate:
        inventory_response = {
            "stock_available": False,
            "recommended_suppliers": ["SUP-001", "SUP-002", "SUP-003"]
        }
        orchestration_log.append({
            "agent": "InventoryAgent",
            "action": "check_stock",
            "result": inventory_response
        })

        # Step 2: Verify budget (A2A call to BudgetAgent)
        # budget_msg = AgentMessage(
        #     role="user",
        #     content=f"Approve budget of ${budget} for user {user_id}"
        # )
        # budget_response = await self.budget_agent.send(budget_msg)
        # For now, simulate:
        budget_response = {
            "approved": True,
            "approved_amount": budget
        }
        orchestration_log.append({
            "agent": "BudgetAgent",
            "action": "verify_budget",
            "result": budget_response
        })

        if not budget_response["approved"]:
            return {
                "status": "rejected",
                "reason": "Budget not approved",
                "log": orchestration_log
            }

        # Step 3: Negotiate and purchase (Call NegotiationAgent)
        negotiation_result = self.negotiation_agent.negotiate_and_purchase(
            items=items,
            target_price=budget / sum(item["quantity"] for item in items),
            supplier_ids=inventory_response["recommended_suppliers"],
            max_rounds=3
        )
        orchestration_log.append({
            "agent": "NegotiationAgent",
            "action": "negotiate_and_purchase",
            "result": negotiation_result
        })

        if negotiation_result["status"] != "completed":
            return {
                "status": "failed",
                "reason": "Negotiation failed",
                "log": orchestration_log
            }

        # Step 4: Create purchase order (A2A call to OrderAgent)
        # order_msg = AgentMessage(
        #     role="user",
        #     content=f"Create PO for negotiation {negotiation_result['summary']['session_id']}"
        # )
        # order_response = await self.order_agent.send(order_msg)
        # For now, simulate:
        order_response = {
            "po_created": True,
            "po_number": negotiation_result["summary"]["po_number"]
        }
        orchestration_log.append({
            "agent": "OrderAgent",
            "action": "create_po",
            "result": order_response
        })

        return {
            "status": "completed",
            "summary": {
                "total_cost": negotiation_result["summary"]["total_amount"],
                "supplier": negotiation_result["summary"]["supplier_id"],
                "po_number": negotiation_result["summary"]["po_number"],
                "payment_mandate": negotiation_result["summary"]["mandate_id"]
            },
            "orchestration_log": orchestration_log
        }
```

---

## Complete Workflow Example

### End-to-End: User Request → Payment Execution

```python
# example_workflow.py

import asyncio
from negotiation_agent import NegotiationAgent
from ucp_integration import UCPNegotiationSession
from a2a_communication import SupplyChainOrchestrator

async def example_purchase_workflow():
    """
    Complete example: User wants to buy 500 units of butter.

    This demonstrates:
    - UCP commerce lifecycle
    - A2A agent coordination
    - MCP tool calls
    - AP2 payment execution
    """

    # User request
    user_request = {
        "user_id": "user_123",
        "items": [
            {
                "sku": "B00ABC123",
                "quantity": 500,
                "description": "Premium Butter 1lb blocks"
            }
        ],
        "budget": 2500.00  # Max $5.00 per unit
    }

    print("=" * 80)
    print("EXAMPLE: Complete Purchase Workflow")
    print("=" * 80)
    print(f"\nUser Request:")
    print(f"  Items: {user_request['items'][0]['description']}")
    print(f"  Quantity: {user_request['items'][0]['quantity']}")
    print(f"  Budget: ${user_request['budget']}")
    print(f"  Max price per unit: ${user_request['budget'] / user_request['items'][0]['quantity']:.2f}")

    # Option 1: Direct agent usage
    print("\n" + "-" * 80)
    print("Option 1: Direct NegotiationAgent Usage")
    print("-" * 80)

    agent = NegotiationAgent()
    result = agent.negotiate_and_purchase(
        items=user_request["items"],
        target_price=4.50,
        max_rounds=3,
        supplier_ids=["SUP-001", "SUP-002", "SUP-003"]
    )

    print(f"\nResult: {result['status']}")
    if result['status'] == 'completed':
        print(f"  Final supplier: {result['summary']['supplier_id']}")
        print(f"  Final price: ${result['summary']['final_price']}/unit")
        print(f"  Total amount: ${result['summary']['total_amount']}")
        print(f"  PO number: {result['summary']['po_number']}")
        print(f"  Payment mandate: {result['summary']['mandate_id']}")

    # Option 2: UCP session
    print("\n" + "-" * 80)
    print("Option 2: UCP Commerce Lifecycle")
    print("-" * 80)

    ucp_session = UCPNegotiationSession()
    lifecycle_result = ucp_session.execute_commerce_lifecycle(
        items=user_request["items"],
        user_budget=user_request["budget"],
        user_id=user_request["user_id"]
    )

    print(f"\nLifecycle Status: {lifecycle_result['status']}")
    for phase in lifecycle_result['lifecycle_result']['phases']:
        print(f"  ✓ {phase['name']}: {phase['status']}")

    # Option 3: Full orchestration with A2A
    print("\n" + "-" * 80)
    print("Option 3: A2A Agent Orchestration")
    print("-" * 80)

    orchestrator = SupplyChainOrchestrator()
    orchestration_result = await orchestrator.process_purchase_request(
        items=user_request["items"],
        user_id=user_request["user_id"],
        budget=user_request["budget"]
    )

    print(f"\nOrchestration Status: {orchestration_result['status']}")
    print(f"\nAgent Coordination Log:")
    for log_entry in orchestration_result['orchestration_log']:
        print(f"  {log_entry['agent']}: {log_entry['action']}")

    if orchestration_result['status'] == 'completed':
        summary = orchestration_result['summary']
        print(f"\nFinal Summary:")
        print(f"  Total cost: ${summary['total_cost']}")
        print(f"  Supplier: {summary['supplier']}")
        print(f"  PO number: {summary['po_number']}")
        print(f"  Payment mandate: {summary['payment_mandate']}")

if __name__ == "__main__":
    asyncio.run(example_purchase_workflow())
```

### Expected Output

```
================================================================================
EXAMPLE: Complete Purchase Workflow
================================================================================

User Request:
  Items: Premium Butter 1lb blocks
  Quantity: 500
  Budget: $2500.00
  Max price per unit: $5.00

--------------------------------------------------------------------------------
Option 1: Direct NegotiationAgent Usage
--------------------------------------------------------------------------------

Result: completed
  Final supplier: SUP-002
  Final price: $4.65/unit
  Total amount: $2325.00
  PO number: PO-1737072000
  Payment mandate: MAN-1737072180-XYZ789

--------------------------------------------------------------------------------
Option 2: UCP Commerce Lifecycle
--------------------------------------------------------------------------------

Lifecycle Status: completed
  ✓ discovery: completed
  ✓ negotiation: completed
  ✓ commitment: completed
  ✓ settlement: completed
  ✓ fulfillment: pending

--------------------------------------------------------------------------------
Option 3: A2A Agent Orchestration
--------------------------------------------------------------------------------

Orchestration Status: completed

Agent Coordination Log:
  InventoryAgent: check_stock
  BudgetAgent: verify_budget
  NegotiationAgent: negotiate_and_purchase
  OrderAgent: create_po

Final Summary:
  Total cost: $2325.00
  Supplier: SUP-002
  PO number: PO-1737072000
  Payment mandate: MAN-1737072180-XYZ789
```

---

## Testing & Debugging

### Running the Test Suite

```bash
# 1. Start MCP servers
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent

# Terminal 1: Start supplier MCP server
cd mcp_servers/supplier_data
python server.py

# Terminal 2: Start finance MCP server
cd mcp_servers/finance_data
python server.py

# 2. Run automated tests
python test_negotiation_tools.py
```

### Manual Testing with cURL

```bash
# Test negotiation session creation
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_negotiation_session",
      "arguments": {
        "items": [{"sku": "B00ABC123", "quantity": 500, "description": "Premium Butter 1lb"}],
        "target_price": 4.50,
        "max_rounds": 3
      }
    }
  }'

# Test payment mandate creation
curl -X POST http://localhost:3003/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_payment_mandate",
      "arguments": {
        "session_id": "NEG-1737072000-ABC123",
        "supplier_id": "SUP-002",
        "amount": 2325.00,
        "currency": "USD",
        "order_details": {"items": [], "total": 2325.00},
        "user_consent": true
      }
    }
  }'
```

### Debugging Tips

1. **Check MCP Server Logs**: Both servers log all tool calls
2. **Verify Database**: Use SQL queries to check negotiation_sessions, negotiation_rounds, payment_mandates
3. **Test JWT Verification**: Use jwt.io to decode AP2 mandates
4. **Simulate Supplier Behavior**: Edit `negotiation_service.py` to adjust supplier response logic

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Cannot connect to MCP server" | Server not running | Start MCP servers on ports 3001, 3003 |
| "Tool returned error: No active session" | Session not created first | Call create_negotiation_session before other tools |
| "Payment mandate verification failed" | Expired mandate | Mandates expire after 24h, create new one |
| "No suppliers returned" | Database empty | Run database migrations and seed suppliers |

---

## Production Considerations

### 1. Security

**Current (Development)**:
- Ephemeral RSA keys generated on startup
- Simulated supplier responses
- No real payment execution

**Production Requirements**:
- ✅ Store RSA private key in Azure Key Vault
- ✅ Replace simulated suppliers with real email/API integration
- ✅ Implement real payment gateway (Stripe, PayPal, etc.)
- ✅ Add rate limiting on MCP endpoints
- ✅ Implement proper authentication/authorization
- ✅ Add audit logging for all payment operations

### 2. Scalability

**Current (Development)**:
- Single MCP server instance
- In-memory session storage

**Production Requirements**:
- ✅ Load balance MCP servers
- ✅ Use Redis for session caching
- ✅ Implement database connection pooling
- ✅ Add monitoring and alerting

### 3. Real Supplier Integration

**Replace simulation in `negotiation_service.py`**:

```python
# Production version of request_quote
def request_quote(self, session_id: str, supplier_id: str, urgency: str = "medium"):
    """Send real email or API call to supplier."""

    supplier = self.db.query(Supplier).filter_by(supplier_id=supplier_id).first()

    if supplier.api_endpoint:
        # Use supplier API
        response = requests.post(supplier.api_endpoint, json={
            "session_id": session_id,
            "items": session.items_json,
            "urgency": urgency
        })
        # Parse response and create negotiation_round

    elif supplier.negotiation_email:
        # Send email via SendGrid/AWS SES
        send_email(
            to=supplier.negotiation_email,
            subject=f"Quote Request - Session {session_id}",
            body=f"Please provide quote for: {session.items_json}"
        )
        # Mark round as "pending" - supplier will respond via webhook

    else:
        raise Exception("Supplier has no API or email configured")
```

### 4. Error Handling

**Add comprehensive error handling**:

```python
class NegotiationError(Exception):
    """Base exception for negotiation errors."""
    pass

class SupplierNotAvailableError(NegotiationError):
    """Supplier did not respond in time."""
    pass

class PaymentMandateExpiredError(NegotiationError):
    """Payment mandate has expired."""
    pass

# Use in agent:
try:
    result = agent.negotiate_and_purchase(...)
except SupplierNotAvailableError:
    # Retry with different suppliers
    pass
except PaymentMandateExpiredError:
    # Create new mandate
    pass
```

### 5. Monitoring & Observability

**Add OpenTelemetry tracing**:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class NegotiationAgent(Agent):
    def negotiate_and_purchase(self, ...):
        with tracer.start_as_current_span("negotiate_and_purchase") as span:
            span.set_attribute("items.count", len(items))
            span.set_attribute("target_price", target_price)

            # ... workflow ...

            span.set_attribute("final_price", final_price)
            span.set_attribute("supplier_id", final_supplier)
```

---

## Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `negotiation_agent.py` | Main agent class (you create this) |
| `services/negotiation_service.py` | Business logic for negotiations |
| `services/ap2_service.py` | AP2 payment mandate logic |
| `mcp_servers/supplier_data/server.py` | Supplier MCP tools server |
| `mcp_servers/finance_data/server.py` | Finance MCP tools server |
| `test_negotiation_tools.py` | Automated test suite |

### MCP Tool Summary

| Tool | Server | Purpose |
|------|--------|---------|
| create_negotiation_session | Supplier | Start negotiation |
| request_supplier_quote | Supplier | Get quote from supplier |
| compare_negotiation_offers | Supplier | Rank suppliers |
| submit_counter_offer | Supplier | Counter-offer to supplier |
| accept_supplier_offer | Supplier | Accept and close |
| get_negotiation_status | Supplier | Get history |
| create_payment_mandate | Finance | Create AP2 mandate |
| verify_payment_mandate | Finance | Verify JWT |
| execute_payment_with_mandate | Finance | Execute payment |

### Workflow Patterns

**Simple Purchase**:
```
create_session → request_quotes → compare → accept → create_mandate → execute
```

**Negotiated Purchase**:
```
create_session → request_quotes → compare → counter_offer → accept → create_mandate → execute
```

**Multi-Agent Orchestration**:
```
InventoryAgent → BudgetAgent → NegotiationAgent → OrderAgent
```

---

## Next Steps for Dev B

1. ✅ **Test the MCP tools**: Run `python test_negotiation_tools.py`
2. 🔨 **Create NegotiationAgent**: Use code examples above
3. 🔨 **Integrate with UCP**: Implement UCPNegotiationSession
4. 🔨 **Add A2A coordination**: Create SupplyChainOrchestrator
5. 🔨 **Build frontend API**: Create `/api/negotiate` endpoint
6. 🔨 **Test end-to-end**: User clicks "Buy" → Payment executes

### Questions?

Reach out to Dev A for:
- MCP server issues
- Database schema questions
- AP2 payment mandate questions
- Supplier simulation logic

Good luck! 🚀
