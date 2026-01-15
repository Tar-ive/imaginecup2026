# SupplyMind - Azure Deployment

Complete deployment infrastructure for the SupplyMind supply chain optimization platform.

## Quick Start

### First-Time Deployment

```bash
# 1. Ensure you're in the right directory
cd /Users/quamos/Repos/imaginecup2026/azure-agents

# 2. Deploy both frontend and backend
./deploy-all.sh
```

That's it! The script will:
- ✅ Validate prerequisites
- ✅ Deploy backend to Azure Container Apps
- ✅ Deploy frontend with correct backend URL
- ✅ Run health checks
- ✅ Display application URLs

### Update Existing Deployment

```bash
# Deploy only backend (if backend code changed)
./deploy-backend.sh

# Deploy only frontend (if frontend code changed)
./deploy-frontend.sh

# Deploy both
./deploy-all.sh
```

## Architecture

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

**Key Decision: Why Two Containers?**
- ✅ Independent scaling (frontend traffic ≠ backend load)
- ✅ Independent deployment (update one without affecting the other)
- ✅ Cost optimization (right-size each container)
- ✅ Technology isolation (Node.js vs Python)
- ✅ Better debugging (separate logs)

## Project Structure

```
azure-agents/
├── README.md                    # This file
├── DEPLOYMENT_PLAN.md           # Comprehensive deployment guide
├── QUICK_REFERENCE.md           # Common commands reference
│
├── deploy-all.sh                # 🚀 Master deployment script
├── deploy-backend.sh            # Backend deployment
├── deploy-frontend.sh           # Frontend deployment
├── .backend-url.sh              # Auto-generated backend URL
│
├── frontend/
│   ├── Dockerfile.template      # Frontend container definition
│   ├── DEPLOYMENT_CHECKLIST.md  # Frontend preparation guide
│   ├── app/                     # Next.js application
│   ├── components/              # React components
│   └── package.json             # Node dependencies
│
└── realtime_price_agent/
    ├── Dockerfile               # Backend container definition
    ├── main.py                  # FastAPI application
    ├── agents/                  # AI agents
    ├── services/                # Business logic
    ├── database/                # Database models
    └── requirements.txt         # Python dependencies
```

## Prerequisites

### Required Tools

```bash
# Azure CLI (for deployment)
brew install azure-cli  # macOS
# OR
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash  # Linux

# Docker (for local testing only - not required for deployment)
brew install docker  # macOS
```

### Azure Login

```bash
# Login to Azure
az login

# Set subscription (if you have multiple)
az account set --subscription "8648ece4-f125-406e-86ee-ecddc7e70962"

# Verify
az account show
```

### Environment Variables

Ensure `.env` file exists at project root with:

```bash
# Database
DATABASE_URL=postgresql://...

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# MCP Servers (already deployed)
MCP_SUPPLIER_DATA_URL=https://...
MCP_INVENTORY_MGMT_URL=https://...
MCP_FINANCE_DATA_URL=https://...
MCP_ANALYTICS_FORECAST_URL=https://...
MCP_INTEGRATIONS_URL=https://...

# Server Configuration
PORT=8000
LOG_LEVEL=INFO
```

## Deployment Options

### Option 1: Complete Deployment (Recommended)

```bash
./deploy-all.sh
```

Deploys both frontend and backend, with automatic health checks.

### Option 2: Backend Only

```bash
./deploy-backend.sh
```

Use when:
- Only backend code changed
- Frontend is not ready yet
- Testing backend changes

### Option 3: Frontend Only

```bash
# Auto-detect backend URL from previous deployment
./deploy-frontend.sh

# Or specify backend URL explicitly
./deploy-frontend.sh --backend-url https://supplymind-backend.xxx.azurecontainerapps.io
```

Use when:
- Only frontend code changed
- Backend is already running

### Option 4: Partial Updates

```bash
# Deploy backend, skip frontend
./deploy-all.sh --skip-frontend

# Deploy frontend, skip backend (use existing)
./deploy-all.sh --skip-backend
# OR
./deploy-all.sh --frontend-only
```

## Post-Deployment

### Verify Deployment

```bash
# Check both apps are running
az containerapp list \
  --resource-group ImagineCup \
  --query "[].{name:name,status:properties.runningStatus,url:properties.configuration.ingress.fqdn}" \
  -o table

# Test backend
curl https://supplymind-backend.xxx.azurecontainerapps.io/api/health

# Test frontend
open https://supplymind-frontend.xxx.azurecontainerapps.io
```

### Monitor Logs

```bash
# Backend logs (follow mode)
az containerapp logs show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --follow

# Frontend logs (follow mode)
az containerapp logs show \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --follow
```

## Common Tasks

### Update Backend Code

```bash
# Make your changes
vim realtime_price_agent/main.py

# Deploy
./deploy-backend.sh

# Check logs
az containerapp logs show --name supplymind-backend --resource-group ImagineCup --follow
```

### Update Frontend Code

**Note**: Frontend needs Dockerfile first (see frontend/DEPLOYMENT_CHECKLIST.md)

```bash
# Make your changes
vim frontend/app/page.tsx

# Deploy
./deploy-frontend.sh

# Check logs
az containerapp logs show --name supplymind-frontend --resource-group ImagineCup --follow
```

### Rollback Deployment

```bash
# List available versions
az acr repository show-tags \
  --name imaginecupreg999 \
  --repository supply-chain-api \
  -o table

# Deploy specific version
az containerapp update \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v20260108-120000
```

### Scale Applications

```bash
# Scale backend for high load
az containerapp update \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --min-replicas 2 \
  --max-replicas 5

# Scale frontend
az containerapp update \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --min-replicas 1 \
  --max-replicas 3
```

## Troubleshooting

### Deployment Fails

**Problem**: Script exits with error

**Solutions**:
1. Check you're logged in: `az account show`
2. Verify .env file exists and has all required variables
3. Check ACR has space: `az acr show-usage --name imaginecupreg999`
4. Review error message for specific issue

### Frontend Can't Reach Backend

**Problem**: Frontend loads but can't fetch data

**Solutions**:
1. Verify backend URL is correct:
   ```bash
   az containerapp show \
     --name supplymind-frontend \
     --resource-group ImagineCup \
     --query "properties.template.containers[0].env[?name=='NEXT_PUBLIC_API_URL'].value"
   ```
2. Test backend directly: `curl https://backend-url/api/health`
3. Check backend logs for errors
4. Verify CORS is enabled in backend (already configured)

### Container Keeps Restarting

**Problem**: App shows as "Running" but keeps restarting

**Solutions**:
1. Check logs: `az containerapp logs show ...`
2. Verify environment variables are set correctly
3. Check database connectivity
4. Ensure health check endpoint is working

### High Costs

**Problem**: Azure bill is higher than expected

**Solutions**:
1. Check replica counts (reduce if too high)
2. Review resource allocations (CPU/memory)
3. Check auto-scaling settings
4. Consider reserved capacity for production

## Cost Estimation

| Component | Resources | Estimated Cost |
|-----------|-----------|----------------|
| Backend | 1.0 CPU, 2Gi RAM, 1-3 replicas | $50-70/month |
| Frontend | 0.5 CPU, 1Gi RAM, 1-3 replicas | $20-25/month |
| MCP Servers | Already deployed | $0 (existing) |
| Container Registry | 100GB storage | $5/month |
| Database (Neon) | Free tier | $0 |
| **Total** | | **$75-100/month** |

**Note**: Actual costs depend on traffic and auto-scaling. These are estimates for low-moderate traffic.

## Documentation

- **[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)** - Complete deployment strategy and architecture
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Common commands and troubleshooting
- **[frontend/DEPLOYMENT_CHECKLIST.md](frontend/DEPLOYMENT_CHECKLIST.md)** - Frontend preparation guide

## Support

### Azure Resources
- Azure Container Apps: https://learn.microsoft.com/azure/container-apps/
- Azure Container Registry: https://learn.microsoft.com/azure/container-registry/
- Azure CLI: https://learn.microsoft.com/cli/azure/

### Application Resources
- Next.js Deployment: https://nextjs.org/docs/deployment
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/

## Team

- **Frontend**: Next.js 15, React 19, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Python 3.11, SQLAlchemy, Azure OpenAI
- **Database**: Neon PostgreSQL (serverless)
- **Agents**: Custom AI agents for supply chain optimization
- **Deployment**: Azure Container Apps, Azure Container Registry

---

## Quick Commands Summary

```bash
# Deploy everything
./deploy-all.sh

# Deploy backend only
./deploy-backend.sh

# Deploy frontend only
./deploy-frontend.sh

# View backend logs
az containerapp logs show --name supplymind-backend --resource-group ImagineCup --follow

# View frontend logs
az containerapp logs show --name supplymind-frontend --resource-group ImagineCup --follow

# Check status
az containerapp list --resource-group ImagineCup -o table

# Rollback backend
./deploy-backend.sh --tag v20260108-120000

# Get application URLs
az containerapp show --name supplymind-backend --resource-group ImagineCup \
  --query properties.configuration.ingress.fqdn -o tsv
az containerapp show --name supplymind-frontend --resource-group ImagineCup \
  --query properties.configuration.ingress.fqdn -o tsv
```

---

**Status**: Ready for deployment (frontend Dockerfile pending)

**Last Updated**: 2026-01-09

**Version**: 1.0.0
