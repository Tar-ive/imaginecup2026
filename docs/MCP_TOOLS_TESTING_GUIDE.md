# MCP Tools Testing Guide
## Negotiation & AP2 Payment Tools

**Date:** 2026-01-16
**Status:** ✅ Implementation Complete - Ready for Testing

---

## Implementation Summary

### ✅ Completed Components

#### 1. **Database Models** (100%)
- `NegotiationSession` - Tracks negotiation sessions
- `NegotiationRound` - Stores offers and counter-offers
- `PaymentMandate` - AP2 payment mandates with JWT signatures
- **Updated:** `Supplier` model with negotiation fields
- **Updated:** `PurchaseOrder` model with negotiation/mandate links

#### 2. **Service Layer** (100%)
- **`NegotiationService`** - Full negotiation workflow with simulated supplier responses
  - `create_session()` - Initialize negotiation
  - `request_quote()` - Get instant simulated quotes
  - `submit_counter()` - Submit counter-offers with intelligent simulation
  - `accept_offer()` - Accept and close negotiation
  - `get_status()` - Get complete negotiation history
  - `compare_offers()` - Rank suppliers by criteria

- **`AP2Service`** - Payment mandate creation with cryptography
  - `create_mandate()` - Generate signed JWT mandates (RS256)
  - `verify_mandate()` - Verify signature and validity
  - `execute_payment()` - Execute payment with mandate

#### 3. **MCP Server Extensions** (100%)
- **Supplier Data MCP** (`:3001`) - 6 new negotiation tools
- **Finance Data MCP** (`:3003`) - 3 new AP2 payment tools

#### 4. **Dependencies** (100%)
- `PyJWT==2.8.0` - JWT signing and verification
- `cryptography==41.0.7` - RSA key generation and management

---

## Prerequisites

### 1. Install Dependencies

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent

# Install main dependencies
pip install -r requirements.txt

# Install MCP server dependencies
pip install -r mcp_servers/finance_data/requirements.txt
```

### 2. Run Database Migration

Connect to your Azure SQL database and run:

```bash
# Using Azure SQL CLI or SQL Server Management Studio
sqlcmd -S your-server.database.windows.net -d your-database -U your-user -P your-password -i database/migrations/001_add_negotiation_tables.sql
```

**Or manually execute the SQL from:** `database/migrations/001_add_negotiation_tables.sql`

### 3. Verify Database Schema

```sql
-- Check tables exist
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('negotiation_sessions', 'negotiation_rounds', 'payment_mandates')
ORDER BY TABLE_NAME;

-- Should return 3 rows
```

---

## Testing the MCP Tools

### Method 1: Test with cURL (Direct MCP Protocol)

#### Test 1: List Available Tools

**Supplier Data MCP:**
```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/list"
  }' | jq '.tools[] | select(.name | startswith("create_negotiation") or startswith("request_supplier") or startswith("submit_counter") or startswith("accept_supplier") or startswith("get_negotiation") or startswith("compare_negotiation")) | .name'
```

**Expected Output:**
```
create_negotiation_session
request_supplier_quote
submit_counter_offer
accept_supplier_offer
get_negotiation_status
compare_negotiation_offers
```

**Finance Data MCP:**
```bash
curl -X POST http://localhost:3003/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/list"
  }' | jq '.tools[] | select(.name | startswith("create_payment") or startswith("verify_payment") or startswith("execute_payment")) | .name'
```

**Expected Output:**
```
create_payment_mandate
verify_payment_mandate
execute_payment_with_mandate
```

---

#### Test 2: Full Negotiation Workflow

**Step 1: Create Negotiation Session**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_negotiation_session",
      "arguments": {
        "items": [
          {
            "sku": "B00EXAMPLE",
            "quantity": 500,
            "description": "Butter 1lb blocks"
          }
        ],
        "target_price": 4.50,
        "max_rounds": 3
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "session_id": "neg-abc12345",
  "status": "open",
  "items": [...],
  "target_price": 4.5,
  "max_rounds": 3,
  "created_at": "2026-01-16T..."
}
```

**Save the `session_id` for next steps!**

---

**Step 2: Request Quotes from Suppliers**

```bash
# Request quote from Supplier A
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "request_supplier_quote",
      "arguments": {
        "session_id": "neg-abc12345",
        "supplier_id": "SUP-001",
        "urgency": "high"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "round_id": "rnd-xyz789",
  "session_id": "neg-abc12345",
  "supplier_id": "SUP-001",
  "supplier_name": "Supplier A",
  "offered_price": 5.12,
  "total_value": 2560.0,
  "status": "received",
  "simulated": true
}
```

**Note:** Price is simulated (5-15% markup from base cost)

Repeat for other suppliers:
```bash
# Supplier B
curl -X POST http://localhost:3001/mcp ... "supplier_id": "SUP-002" ...

# Supplier C
curl -X POST http://localhost:3001/mcp ... "supplier_id": "SUP-003" ...
```

---

**Step 3: Compare Offers**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "compare_negotiation_offers",
      "arguments": {
        "session_id": "neg-abc12345",
        "criteria": "total_cost"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "session_id": "neg-abc12345",
  "criteria": "total_cost",
  "target_price": 4.5,
  "offers_count": 3,
  "ranked_suppliers": [
    {
      "supplier_id": "SUP-001",
      "supplier_name": "Supplier A",
      "offered_price": 5.12,
      "total_value": 2560.0,
      "round_number": 1
    },
    ...
  ],
  "best_offer": { "supplier_id": "SUP-001", ... }
}
```

---

**Step 4: Submit Counter-Offer**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "submit_counter_offer",
      "arguments": {
        "session_id": "neg-abc12345",
        "supplier_id": "SUP-001",
        "counter_price": 4.50,
        "justification": "Target budget constraint, requesting 12% discount"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response (Simulated Supplier Decision):**
```json
{
  "round_id": "rnd-new123",
  "session_id": "neg-abc12345",
  "supplier_id": "SUP-001",
  "our_counter_price": 4.5,
  "their_response_price": 4.81,
  "total_value": 2405.0,
  "round_number": 2,
  "status": "countered",
  "simulated": true,
  "discount_requested_percent": 12.11
}
```

**Simulation Logic:**
- If discount ≤5%: Accept your counter
- If 5-10%: Meet halfway
- If 10-15%: Smaller concession (5% off)
- If >15%: Minimal movement (3% off)

---

**Step 5: Accept Best Offer**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "accept_supplier_offer",
      "arguments": {
        "session_id": "neg-abc12345",
        "supplier_id": "SUP-001",
        "notes": "Best offer after 2 rounds of negotiation"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "session_id": "neg-abc12345",
  "status": "completed",
  "winning_supplier_id": "SUP-001",
  "final_price": 4.81,
  "total_value": 2405.0,
  "items": [...],
  "target_price": 4.5,
  "rounds_completed": 2,
  "notes": "Best offer after 2 rounds of negotiation",
  "completed_at": "2026-01-16T..."
}
```

---

**Step 6: Get Full Negotiation Status**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "get_negotiation_status",
      "arguments": {
        "session_id": "neg-abc12345"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "session_id": "neg-abc12345",
  "status": "completed",
  "items": [...],
  "target_price": 4.5,
  "max_rounds": 3,
  "current_round": 2,
  "winning_supplier_id": "SUP-001",
  "final_price": 4.81,
  "total_value": 2405.0,
  "created_at": "2026-01-16T...",
  "completed_at": "2026-01-16T...",
  "rounds": [
    {
      "round_id": "rnd-xyz789",
      "supplier_id": "SUP-001",
      "round_number": 1,
      "offer_type": "initial",
      "offered_price": 5.12,
      "total_value": 2560.0,
      "status": "countered",
      ...
    },
    {
      "round_id": "rnd-new123",
      "supplier_id": "SUP-001",
      "round_number": 2,
      "offer_type": "counter",
      "offered_price": 4.81,
      "total_value": 2405.0,
      "counter_price": 4.5,
      "justification": "Target budget constraint...",
      "status": "accepted",
      ...
    }
  ]
}
```

---

#### Test 3: AP2 Payment Mandate Creation

**Step 1: Create Payment Mandate**

```bash
curl -X POST http://localhost:3003/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "create_payment_mandate",
      "arguments": {
        "session_id": "neg-abc12345",
        "supplier_id": "SUP-001",
        "amount": 2405.00,
        "currency": "USD",
        "order_details": {
          "items": [
            {"sku": "B00EXAMPLE", "quantity": 500, "unit_price": 4.81}
          ],
          "total": 2405.00
        },
        "user_consent": true
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "mandate_id": "ap2-xyz1234567",
  "signed_mandate": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InN1cHBseW1pbmQta2V5LTAwMSJ9...",
  "amount": 2405.0,
  "currency": "USD",
  "supplier_id": "SUP-001",
  "expires_at": "2026-01-17T...",
  "status": "created",
  "session_id": "neg-abc12345",
  "po_number": null
}
```

**Save the `mandate_id` and `signed_mandate` for next steps!**

---

**Step 2: Verify Payment Mandate**

```bash
curl -X POST http://localhost:3003/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "verify_payment_mandate",
      "arguments": {
        "mandate_id": "ap2-xyz1234567"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "mandate_id": "ap2-xyz1234567",
  "valid": true,
  "decoded_payload": {
    "iss": "SupplyMind",
    "sub": "SUP-001",
    "aud": "ap2-payment-gateway",
    "iat": 1705419600,
    "exp": 1705506000,
    "mandate_id": "ap2-xyz1234567",
    "mandate_type": "checkout",
    "amount": 2405.0,
    "currency": "USD",
    ...
  },
  "status": "created",
  "amount": 2405.0,
  "currency": "USD",
  "supplier_id": "SUP-001"
}
```

---

**Step 3: Execute Payment**

```bash
curl -X POST http://localhost:3003/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "execute_payment_with_mandate",
      "arguments": {
        "mandate_id": "ap2-xyz1234567",
        "po_number": "PO-2026-001"
      }
    }
  }' | jq '.content[0].text | fromjson'
```

**Expected Response:**
```json
{
  "mandate_id": "ap2-xyz1234567",
  "status": "executed",
  "amount": 2405.0,
  "currency": "USD",
  "supplier_id": "SUP-001",
  "po_number": "PO-2026-001",
  "executed_at": "2026-01-16T...",
  "message": "Payment executed successfully (simulated)"
}
```

---

## Verify in Database

After testing, check the database:

```sql
-- Check negotiation sessions
SELECT * FROM negotiation_sessions
ORDER BY created_at DESC;

-- Check negotiation rounds
SELECT
    nr.session_id,
    nr.round_number,
    nr.supplier_id,
    nr.offered_price,
    nr.counter_price,
    nr.status
FROM negotiation_rounds nr
ORDER BY nr.created_at DESC;

-- Check payment mandates
SELECT
    mandate_id,
    supplier_id,
    amount,
    status,
    created_at,
    expires_at
FROM payment_mandates
ORDER BY created_at DESC;

-- Check complete negotiation flow
SELECT
    ns.session_id,
    ns.status AS session_status,
    ns.target_price,
    ns.final_price,
    COUNT(nr.round_id) AS total_rounds,
    pm.mandate_id,
    pm.status AS mandate_status
FROM negotiation_sessions ns
LEFT JOIN negotiation_rounds nr ON ns.session_id = nr.session_id
LEFT JOIN payment_mandates pm ON ns.session_id = pm.session_id
WHERE ns.session_id = 'neg-abc12345'
GROUP BY ns.session_id, ns.status, ns.target_price, ns.final_price, pm.mandate_id, pm.status;
```

---

## Method 2: Test with Python Script

Create `test_negotiation_tools.py`:

```python
import requests
import json

BASE_URL_SUPPLIER = "http://localhost:3001/mcp"
BASE_URL_FINANCE = "http://localhost:3003/mcp"

def call_tool(base_url, tool_name, arguments):
    """Call MCP tool."""
    response = requests.post(base_url, json={
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    })
    result = response.json()
    if result.get("isError"):
        print(f"❌ Error: {result['content'][0]['text']}")
        return None
    return json.loads(result["content"][0]["text"])

# Test workflow
print("1. Creating negotiation session...")
session = call_tool(BASE_URL_SUPPLIER, "create_negotiation_session", {
    "items": [{"sku": "B00TEST", "quantity": 500, "description": "Test product"}],
    "target_price": 4.50,
    "max_rounds": 3
})
print(f"✅ Session created: {session['session_id']}")

session_id = session['session_id']

print("\n2. Requesting quotes from suppliers...")
quote1 = call_tool(BASE_URL_SUPPLIER, "request_supplier_quote", {
    "session_id": session_id,
    "supplier_id": "SUP-001"
})
print(f"✅ Supplier 1 quoted: ${quote1['offered_price']}")

quote2 = call_tool(BASE_URL_SUPPLIER, "request_supplier_quote", {
    "session_id": session_id,
    "supplier_id": "SUP-002"
})
print(f"✅ Supplier 2 quoted: ${quote2['offered_price']}")

print("\n3. Comparing offers...")
comparison = call_tool(BASE_URL_SUPPLIER, "compare_negotiation_offers", {
    "session_id": session_id,
    "criteria": "total_cost"
})
best = comparison['best_offer']
print(f"✅ Best offer: {best['supplier_name']} at ${best['offered_price']}")

print("\n4. Submitting counter-offer...")
counter = call_tool(BASE_URL_SUPPLIER, "submit_counter_offer", {
    "session_id": session_id,
    "supplier_id": best['supplier_id'],
    "counter_price": 4.50,
    "justification": "Target budget"
})
print(f"✅ Counter submitted, supplier responded: ${counter['their_response_price']}")

print("\n5. Accepting offer...")
accepted = call_tool(BASE_URL_SUPPLIER, "accept_supplier_offer", {
    "session_id": session_id,
    "supplier_id": best['supplier_id'],
    "notes": "Best deal"
})
print(f"✅ Offer accepted: ${accepted['final_price']} (Total: ${accepted['total_value']})")

print("\n6. Creating AP2 payment mandate...")
mandate = call_tool(BASE_URL_FINANCE, "create_payment_mandate", {
    "session_id": session_id,
    "supplier_id": accepted['winning_supplier_id'],
    "amount": accepted['total_value'],
    "currency": "USD",
    "order_details": {"items": accepted['items']},
    "user_consent": True
})
print(f"✅ Mandate created: {mandate['mandate_id']}")

print("\n7. Verifying mandate...")
verified = call_tool(BASE_URL_FINANCE, "verify_payment_mandate", {
    "mandate_id": mandate['mandate_id']
})
print(f"✅ Mandate verified: {verified['valid']}")

print("\n8. Executing payment...")
executed = call_tool(BASE_URL_FINANCE, "execute_payment_with_mandate", {
    "mandate_id": mandate['mandate_id'],
    "po_number": "PO-TEST-001"
})
print(f"✅ Payment executed: {executed['status']}")

print("\n🎉 Full workflow completed successfully!")
```

Run it:
```bash
python test_negotiation_tools.py
```

---

## Troubleshooting

### Issue: "Table not found" error

**Solution:** Run the database migration script first.

### Issue: "Unknown tool" error

**Solution:** Make sure MCP servers are restarted after code changes:
```bash
# Stop servers
pkill -f "uvicorn.*mcp_servers"

# Start supplier_data MCP
cd mcp_servers/supplier_data
python server.py &

# Start finance_data MCP
cd ../finance_data
python server.py &
```

### Issue: "Import error" for services

**Solution:** Verify Python path and dependencies:
```bash
pip install -r requirements.txt
export PYTHONPATH=/Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent:$PYTHONPATH
```

### Issue: JWT signature verification fails

**Solution:** AP2Service generates ephemeral keys. This is expected in development. Keys are valid for the lifetime of the server process.

---

## Next Steps

1. ✅ **Test MCP tools** with cURL or Python script
2. ⏭️ **Create NegotiationAgent** with instructions
3. ⏭️ **Integrate with Orchestrator** (magentic_workflow.py)
4. ⏭️ **Test end-to-end** agent workflow
5. ⏭️ **Deploy to Azure** Container Apps

---

## Summary of What Was Built

### Files Created/Modified

**New Files:**
- `services/negotiation_service.py` - Negotiation business logic
- `services/ap2_service.py` - Payment mandate service
- `database/migrations/001_add_negotiation_tables.sql` - SQL migration

**Modified Files:**
- `database/models.py` - Added 3 new models + relationships
- `requirements.txt` - Added PyJWT, cryptography
- `mcp_servers/supplier_data/server.py` - Added 6 negotiation tools
- `mcp_servers/finance_data/server.py` - Added 3 AP2 tools
- `mcp_servers/finance_data/requirements.txt` - Added PyJWT, cryptography

### Tools Available

**Supplier Data MCP (:3001):**
1. `create_negotiation_session` - Start negotiation
2. `request_supplier_quote` - Get quotes (simulated)
3. `submit_counter_offer` - Counter-offer with simulation
4. `accept_supplier_offer` - Accept and close
5. `get_negotiation_status` - View all rounds
6. `compare_negotiation_offers` - Rank suppliers

**Finance Data MCP (:3003):**
1. `create_payment_mandate` - Generate signed JWT
2. `verify_payment_mandate` - Verify signature
3. `execute_payment_with_mandate` - Execute payment

---

**Ready to test!** 🚀
