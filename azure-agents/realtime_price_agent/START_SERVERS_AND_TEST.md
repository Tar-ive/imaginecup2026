# Start MCP Servers and Run Tests

**Status**: ✅ Code ready, waiting for Docker to test

---

## ⚠️ Important: Servers Run in Docker

The MCP servers are configured to run in Docker containers, not directly on your local machine. This avoids Python dependency conflicts.

---

## Step 1: Start Docker Desktop

Make sure Docker Desktop is running:

```bash
# Check if Docker is running
docker ps

# If not, start Docker Desktop application
# Then verify it's running
docker --version
```

---

## Step 2: Rebuild and Start MCP Servers

The new negotiation and AP2 tools have been added to the code. Rebuild the Docker images to load them:

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent/mcp_servers

# Rebuild and start all MCP servers
docker-compose up --build -d

# This will start:
# - supplier-data (port 3001) - with 6 new negotiation tools
# - finance-data (port 3003) - with 3 new AP2 payment tools
# - inventory-mgmt (port 3002)
# - analytics-forecast (port 3004)
# - integrations (port 3005)
```

---

## Step 3: Verify Servers Are Running

```bash
# Check container status
docker-compose ps

# Should show all containers as "Up"

# Test supplier MCP server
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}' | jq '.tools[].name' | grep negotiation

# Test finance MCP server
curl -X POST http://localhost:3003/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}' | jq '.tools[].name' | grep mandate
```

Expected output:
```
"create_negotiation_session"
"request_supplier_quote"
"submit_counter_offer"
"accept_supplier_offer"
"get_negotiation_status"
"compare_negotiation_offers"

"create_payment_mandate"
"verify_payment_mandate"
"execute_payment_with_mandate"
```

---

## Step 4: Run Automated Tests

Once servers are running:

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent

# Install test dependencies
pip install requests colorama

# Run the test suite
python test_negotiation_tools.py
```

### Expected Test Output

```
================================================================================
MCP TOOLS AUTOMATED TEST SUITE
================================================================================

[TEST 1] List Available Tools
✓ Found: create_negotiation_session
✓ Found: request_supplier_quote
✓ Found: submit_counter_offer
✓ Found: accept_supplier_offer
✓ Found: get_negotiation_status
✓ Found: compare_negotiation_offers
✓ Found: create_payment_mandate
✓ Found: verify_payment_mandate
✓ Found: execute_payment_with_mandate

[TEST 2] Create Negotiation Session
✓ Session created: NEG-1737072000-ABC123

[TEST 3] Request Quotes from Suppliers
✓ SUP-001: $5.20/unit (Total: $2600.00)
✓ SUP-002: $4.80/unit (Total: $2400.00)
✓ SUP-003: $5.50/unit (Total: $2750.00)

[TEST 4] Compare Negotiation Offers
✓ Compared 3 offers
  Best offer: Budget Supplies Inc. at $4.80/unit

[TEST 5] Get Negotiation Status
✓ Retrieved status

[TEST 6] Submit Counter-Offer
✓ Counter-offer submitted: $4.50 → $4.65/unit

[TEST 7] Accept Supplier Offer
✓ Offer accepted: $4.65/unit, Total: $2325.00

[TEST 8] Create AP2 Payment Mandate
✓ Mandate created with RS256 JWT signature

[TEST 9] Verify AP2 Payment Mandate
✓ Mandate verified: True

[TEST 10] Execute Payment with Mandate
✓ Payment executed successfully

================================================================================
TEST SUMMARY
================================================================================
Tests Run: 10
Tests Passed: 10
Tests Failed: 0

🎉 ALL TESTS PASSED!
```

---

## Step 5: View Server Logs (If Needed)

```bash
# View supplier MCP logs
docker logs mcp-supplier-data

# View finance MCP logs
docker logs mcp-finance-data

# Follow logs in real-time
docker logs -f mcp-supplier-data
```

---

## Troubleshooting

### Problem: Docker not running

**Error**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
# Start Docker Desktop application
# Wait for it to fully start
# Then verify:
docker ps
```

### Problem: Containers won't start

**Error**: Container exits immediately

**Solution**:
```bash
# Check logs
docker logs mcp-supplier-data

# Common issues:
# 1. DATABASE_URL not set - check .env file
# 2. Port already in use - kill process on that port
# 3. Build failed - rebuild with: docker-compose up --build
```

### Problem: Database connection errors

**Solution**:
```bash
# The servers use the .env file in realtime_price_agent/
# Make sure DATABASE_URL is set:
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent
cat .env | grep DATABASE_URL

# It should look like:
# DATABASE_URL=mssql+pyodbc://user:pass@server.database.windows.net/SupplyMind?driver=ODBC+Driver+18+for+SQL+Server
```

### Problem: Tests fail with "Cannot connect to MCP server"

**Solution**:
```bash
# Verify containers are running
docker-compose ps

# Check if ports are accessible
curl http://localhost:3001/mcp
curl http://localhost:3003/mcp

# Restart containers if needed
docker-compose restart
```

---

## Quick Command Reference

```bash
# Start all MCP servers
docker-compose up -d

# Start with rebuild (after code changes)
docker-compose up --build -d

# Stop all servers
docker-compose down

# View logs
docker-compose logs -f

# Restart specific server
docker-compose restart supplier-data

# Check status
docker-compose ps

# Remove all containers and rebuild
docker-compose down
docker-compose up --build -d
```

---

## What Gets Tested

### Real-World Scenario
- **Product**: Premium Butter 1lb blocks
- **Quantity**: 500 units
- **Target Price**: $4.50/unit
- **Budget**: $2,250

### Workflow Tested
1. Create negotiation session
2. Request quotes from 3 suppliers
3. Compare offers (SUP-002 wins at $4.80/unit)
4. Counter-offer to $4.50/unit
5. Supplier responds with $4.65/unit
6. Accept offer
7. Create AP2 payment mandate ($2,325 total)
8. Verify JWT signature
9. Execute payment

### Technologies Validated
- ✅ MCP protocol (agent-to-tool communication)
- ✅ Multi-round negotiation workflow
- ✅ Intelligent supplier simulation
- ✅ AP2 payment mandates with RS256 signatures
- ✅ Database integration (negotiation_sessions, negotiation_rounds, payment_mandates)
- ✅ JWT signing and verification

---

## Success Criteria

Before pushing code, verify:

- [ ] Docker Desktop is running
- [ ] All 5 MCP servers start successfully
- [ ] `docker-compose ps` shows all containers as "Up"
- [ ] Can list tools from supplier-data and finance-data
- [ ] All 10 automated tests pass
- [ ] No errors in server logs
- [ ] Test completes in < 60 seconds

**When all tests pass, the code is ready to push!** 🚀

---

## Files Ready to Push

### Core Implementation
- `database/models.py` - Added NegotiationSession, NegotiationRound, PaymentMandate
- `services/negotiation_service.py` - Negotiation workflow with supplier simulation
- `services/ap2_service.py` - AP2 payment mandates with JWT signing
- `mcp_servers/supplier_data/server.py` - 6 new negotiation tools
- `mcp_servers/finance_data/server.py` - 3 new AP2 payment tools
- `database/migrations/001_add_negotiation_tables.sql` - Database schema

### Testing & Documentation
- `test_negotiation_tools.py` - Automated test suite
- `NEGOTIATION_AGENT_INTEGRATION_GUIDE.md` - Complete guide for Dev B
- `TESTING_README.md` - Testing instructions
- `HANDOFF_TO_DEV_B.md` - Handoff document
- `START_SERVERS_AND_TEST.md` - This file

### Requirements
- `requirements.txt` - Added PyJWT, cryptography
- `mcp_servers/finance_data/requirements.txt` - Updated

---

**Next**: Start Docker, run tests, then push code!
