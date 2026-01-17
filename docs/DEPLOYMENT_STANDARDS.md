# SupplyMind - Deployment Standards

This document consolidates all deployment information for the SupplyMind supply chain optimization platform.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  SupplyMind Platform                    │
├──────────────────────┬──────────────────────────────────┤
│   Frontend           │   Backend                        │
│   (Next.js 15)       │   (FastAPI + Python)             │
│   Port: 3000         │   Port: 8000                     │
│   0.5 CPU, 1Gi RAM   │   1.0 CPU, 2Gi RAM               │
└──────────────────────┴──────────────────────────────────┘
            │                       │
            └───────────┬───────────┘
                        │
            ┌───────────▼──────────┐
            │   Neon PostgreSQL    │
            │   + 5 MCP Servers    │
            └──────────────────────┘
```

**Two-Container Architecture Benefits:**
- ✅ Independent scaling (frontend traffic ≠ backend load)
- ✅ Independent deployment (update one without affecting the other)
- ✅ Cost optimization (right-size each container)
- ✅ Technology isolation (Node.js vs Python)
- ✅ Better debugging (separate logs)

---

## Azure Resources

| Resource | Name | Purpose |
|----------|------|---------|
| Resource Group | `ImagineCup` | Container for all resources |
| Container Registry | `imaginecupreg999` | Docker image storage |
| Container App (Backend) | `supplymind-backend` | FastAPI + agents |
| Container App (Frontend) | `supplymind-frontend` | Next.js UI |
| Database | Neon PostgreSQL | Serverless Postgres |

---

## Deployment Scripts

All scripts are located in `/scripts/`:

| Script | Purpose |
|--------|---------|
| `deploy-all.sh` | Deploy both frontend and backend |
| `deploy-backend.sh` | Deploy backend only |
| `deploy-frontend.sh` | Deploy frontend only |
| `deploy-to-azure.sh` | General Azure deployment |
| `deploy-mcp-to-azure.sh` | Deploy MCP servers |
| `start_mcp_servers.sh` | Start local MCP servers |
| `health-check.sh` | Verify deployment health |
| `test-all.sh` | Run all tests |
| `setup.sh` | Initial project setup |
| `create_tables*.sh` | Database table creation |
| `setup_credential.sh` | Azure credential setup |
| `validate_env_vars.sh` | Validate environment variables |

### Quick Deployment

```bash
# Deploy everything
./scripts/deploy-all.sh

# Deploy backend only
./scripts/deploy-backend.sh

# Deploy frontend only
./scripts/deploy-frontend.sh
```

---

## Environment Configuration

Required `.env` variables:

```bash
# Database
DATABASE_URL=postgresql://...

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# MCP Servers
MCP_SUPPLIER_DATA_URL=https://...
MCP_INVENTORY_MGMT_URL=https://...
MCP_FINANCE_DATA_URL=https://...
MCP_ANALYTICS_FORECAST_URL=https://...
MCP_INTEGRATIONS_URL=https://...

# Server
PORT=8000
LOG_LEVEL=INFO
```

---

## Health Checks

### Backend
```bash
curl https://supplymind-backend.<domain>/api/health
```

Expected response:
```json
{
  "status": "OK",
  "service": "supply-chain-agents",
  "version": "1.0.0"
}
```

### Frontend
```bash
curl https://supplymind-frontend.<domain>
```

---

## Monitoring & Logs

```bash
# Backend logs
az containerapp logs show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --follow

# Frontend logs
az containerapp logs show \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --follow
```

---

## Cost Estimation

| Component | Resources | Estimated Cost |
|-----------|-----------|----------------|
| Backend | 1.0 CPU, 2Gi RAM, 1-3 replicas | $50-70/month |
| Frontend | 0.5 CPU, 1Gi RAM, 1-3 replicas | $20-25/month |
| Container Registry | 100GB storage | $5/month |
| Database (Neon) | Free tier | $0 |
| **Total** | | **$75-100/month** |

---

## Rollback Procedures

### Via Script
```bash
./scripts/deploy-backend.sh --tag v20260108-120000
```

### Via Azure CLI
```bash
az containerapp update \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v20260108-120000
```

---

## Troubleshooting

### Frontend Can't Reach Backend
1. Verify `NEXT_PUBLIC_API_URL` is correct
2. Test backend directly: `curl https://backend-url/api/health`
3. Check backend logs for errors

### Container Keeps Restarting
1. Check logs: `az containerapp logs show ...`
2. Verify environment variables
3. Check database connectivity

### Build Failures
1. Check Dockerfile syntax
2. Verify dependencies in package.json/requirements.txt
3. Ensure sufficient ACR storage

---

*Last Updated: 2026-01-17*
