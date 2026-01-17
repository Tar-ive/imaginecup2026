# Testing the Negotiation & AP2 Payment MCP Tools

**Created**: 2026-01-16
**Status**: Ready for testing

---

## Quick Start

### 1. Start the MCP Servers

The MCP servers need to be restarted to pick up the new negotiation and AP2 payment tools.

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent

# Run the startup script
./start_mcp_servers.sh
```

This will:
- ✅ Kill any existing MCP server processes
- ✅ Start Supplier MCP Server on port 3001
- ✅ Start Finance MCP Server on port 3003
- ✅ Create log files in `logs/` directory
- ✅ Verify servers are running

### 2. Run the Automated Tests

Once the servers are running, execute the test suite:

```bash
# Install test dependencies
pip install requests colorama

# Run the tests
python test_negotiation_tools.py
```

### Expected Test Output

```
================================================================================
MCP TOOLS AUTOMATED TEST SUITE
================================================================================
Testing Negotiation & AP2 Payment Tools
Timestamp: 2026-01-16T10:30:00

================================================================================
[TEST 1] List Available Tools
================================================================================
✓ Found: create_negotiation_session
✓ Found: request_supplier_quote
✓ Found: submit_counter_offer
✓ Found: accept_supplier_offer
✓ Found: get_negotiation_status
✓ Found: compare_negotiation_offers
  Total tools in Supplier MCP: 13

✓ Found: create_payment_mandate
✓ Found: verify_payment_mandate
✓ Found: execute_payment_with_mandate
  Total tools in Finance MCP: 9

[TEST 2] Create Negotiation Session
✓ Session created: NEG-1737072000-ABC123
  Target price: $4.50/unit
  Max rounds: 3
  Status: open

[TEST 3] Request Quotes from Suppliers
✓ SUP-001: $5.20/unit (Total: $2600.00)
  (Simulated supplier response - instant)
✓ SUP-002: $4.80/unit (Total: $2400.00)
  (Simulated supplier response - instant)
✓ SUP-003: $5.50/unit (Total: $2750.00)
  (Simulated supplier response - instant)

[TEST 4] Compare Negotiation Offers
✓ Compared 3 offers
  Best offer: Budget Supplies Inc. at $4.80/unit

  Ranked suppliers:
    1. Budget Supplies Inc.: $4.80/unit
    2. Premium Dairy Co.: $5.20/unit
    3. Quality Foods Ltd.: $5.50/unit

[TEST 5] Get Negotiation Status
✓ Retrieved status for session NEG-1737072000-ABC123
  Current round: 1/3
  Rounds completed: 3
  Session status: open

[TEST 6] Submit Counter-Offer
✓ Counter-offer submitted to SUP-002
  Our counter: $4.50/unit
  Their response: $4.65/unit
  Discount requested: 6.25%
  Status: countered

[TEST 7] Accept Supplier Offer
✓ Offer accepted from SUP-002
  Final price: $4.65/unit
  Total value: $2325.00
  Rounds completed: 2
  Session status: completed

[TEST 8] Create AP2 Payment Mandate
✓ Mandate created: MAN-1737072180-XYZ789
  Amount: $2325.00 USD
  Supplier: SUP-002
  Status: created
  Expires: 2026-01-17T10:33:00Z
  Signature algorithm: RS256 (JWT)
  Signed mandate (JWT): eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

[TEST 9] Verify AP2 Payment Mandate
✓ Mandate verified: True
  Status: created
  Amount: $2325.00 USD
  Issuer: SupplyMind
  Subject (Supplier): SUP-002
  Audience: ap2-payment-gateway
  Expires: 2026-01-17T10:33:00Z

[TEST 10] Execute Payment with Mandate
✓ Payment executed: executed
  Amount: $2325.00 USD
  Supplier: SUP-002
  PO Number: PO-TEST-1737072234
  Executed at: 2026-01-16T10:34:00Z
  Message: Payment executed successfully

================================================================================
TEST SUMMARY
================================================================================

Tests Run: 10
Tests Passed: 10
Tests Failed: 0

🎉 ALL TESTS PASSED!
All MCP tools are working correctly with real-world data.
```

---

## What Gets Tested

### Negotiation Workflow (Tests 1-7)

1. **Tool Discovery**: Verifies all 9 tools are available
2. **Session Creation**: Creates negotiation for 500 units of Premium Butter
3. **Quote Requests**: Requests quotes from 3 suppliers (simulated instant response)
4. **Offer Comparison**: Ranks suppliers by total cost
5. **Status Retrieval**: Gets complete negotiation history
6. **Counter-Offer**: Negotiates from $4.80 → $4.65 per unit
7. **Acceptance**: Closes negotiation with winning supplier

### AP2 Payment Workflow (Tests 8-10)

8. **Mandate Creation**: Creates signed JWT payment mandate (RS256)
9. **Mandate Verification**: Verifies cryptographic signature and expiry
10. **Payment Execution**: Executes payment with verified mandate

---

## Real-World Data Scenario

The test uses realistic SupplyMind startup data:

**Product**: Premium Butter 1lb blocks
**Quantity**: 500 units
**Target Price**: $4.50/unit
**Budget**: $2,250.00

**Simulated Suppliers**:
- SUP-001 (Premium Dairy Co.): Quotes $5.20/unit
- SUP-002 (Budget Supplies Inc.): Quotes $4.80/unit ← Best offer
- SUP-003 (Quality Foods Ltd.): Quotes $5.50/unit

**Negotiation Result**:
- Counter-offered $4.50 to SUP-002
- Supplier responded with $4.65 (met halfway)
- Final total: $2,325.00 (saved $75 from initial quote)

**Payment**:
- Created AP2 mandate for $2,325.00
- Signed with RS256 JWT
- Verified signature
- Executed payment successfully

---

## Manual Testing

### Test Individual Tools with cURL

```bash
# 1. Create negotiation session
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
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
        "max_rounds": 3
      }
    }
  }' | jq .

# 2. Request quote from supplier
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "request_supplier_quote",
      "arguments": {
        "session_id": "NEG-1737072000-ABC123",
        "supplier_id": "SUP-001",
        "urgency": "high"
      }
    }
  }' | jq .

# 3. Create payment mandate
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
        "order_details": {
          "items": [],
          "total": 2325.00
        },
        "user_consent": true
      }
    }
  }' | jq .
```

---

## Troubleshooting

### Problem: "Cannot connect to MCP server"

**Solution**:
```bash
# Check if servers are running
lsof -i :3001  # Supplier MCP
lsof -i :3003  # Finance MCP

# If not running, start them
./start_mcp_servers.sh

# Check logs
tail -f logs/supplier_mcp.log
tail -f logs/finance_mcp.log
```

### Problem: "Tool not found"

**Cause**: Old server code still running

**Solution**:
```bash
# Kill old servers
kill $(lsof -ti:3001)
kill $(lsof -ti:3003)

# Restart with new code
./start_mcp_servers.sh
```

### Problem: "Database connection error"

**Cause**: Azure SQL credentials not configured

**Solution**:
```bash
# Check .env file
cat .env | grep DB_

# Required variables:
DB_SERVER=your-server.database.windows.net
DB_DATABASE=SupplyMind
DB_USERNAME=your-username
DB_PASSWORD=your-password
```

### Problem: "No suppliers found in database"

**Cause**: Database not seeded with test data

**Solution**:
```bash
# Run migrations
cd database/migrations
# Execute 001_add_negotiation_tables.sql in Azure SQL

# Seed test suppliers
# TODO: Create seed script for SUP-001, SUP-002, SUP-003
```

---

## Next Steps After Testing

Once all tests pass:

1. ✅ **Share results with team**: Screenshot of test output
2. ✅ **Hand off to Dev B**: Share `NEGOTIATION_AGENT_INTEGRATION_GUIDE.md`
3. ✅ **Production prep**: Review security considerations in integration guide
4. ✅ **Frontend integration**: Create `/api/negotiate` endpoint
5. ✅ **Real supplier integration**: Replace simulation in `negotiation_service.py`

---

## Key Files

| File | Purpose |
|------|---------|
| `test_negotiation_tools.py` | Automated test suite |
| `start_mcp_servers.sh` | Server startup script |
| `NEGOTIATION_AGENT_INTEGRATION_GUIDE.md` | Dev B integration guide |
| `logs/supplier_mcp.log` | Supplier MCP server logs |
| `logs/finance_mcp.log` | Finance MCP server logs |
| `services/negotiation_service.py` | Negotiation business logic |
| `services/ap2_service.py` | AP2 payment logic |

---

## Success Criteria

All tests should pass with:
- ✅ 10/10 tests passing
- ✅ Negotiation session created
- ✅ 3 supplier quotes received (simulated)
- ✅ Best offer identified and accepted
- ✅ Payment mandate created and signed (RS256 JWT)
- ✅ Mandate verified successfully
- ✅ Payment executed

**When all tests pass, the MCP tools are ready for NegotiationAgent integration!** 🚀
