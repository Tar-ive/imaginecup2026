# Supply Chain API - Azure Deployment Guide

## Overview

This guide provides **three deployment methods** to deploy your Supply Chain API to Azure Container Apps.

## Current Deployment Status

- **Legacy API**: `amazon-api-app` running v10 (old API)
- **New API**: Ready to deploy from `main.py` (full supply chain API with agents, workflows, forecasting)

## Method 1: Cloud Build Deployment (RECOMMENDED ✨)

**Why recommended:** Builds image directly in Azure - no local Docker needed, solves ImagePullBackOff issues.

### Prerequisites
```bash
# 1. Login to Azure
az login

# 2. Verify .env file exists with required variables
cat .env | grep -E "DATABASE_URL|AZURE_OPENAI"
```

### Deploy with One Command

```bash
./deploy-to-azure.sh
```

That's it! The script will:
1. ✅ Build image in Azure (ACR Build)
2. ✅ Push to registry automatically
3. ✅ Update container app with new image
4. ✅ Configure environment variables
5. ✅ Show you the live URL

### What This Does

```
┌─────────────────────────────────────────────────────────┐
│  Your Computer                                          │
│  ├── Source code                                        │
│  └── .env file                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ az acr build (source code)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Azure Container Registry (imaginecupreg999)            │
│  ├── Builds Dockerfile in cloud                         │
│  ├── Creates: supply-chain-api:v11                      │
│  └── Pushes automatically                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ az containerapp update
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Container App (amazon-api-app)                         │
│  ├── Pulls: supply-chain-api:v11                        │
│  ├── Exposes: Port 8000                                 │
│  └── URL: https://amazon-api-app.purplepebble-*.....io  │
└─────────────────────────────────────────────────────────┘
```

---

## Method 2: Manual Cloud Build (Step-by-Step)

If you prefer to run commands manually:

### Step 1: Build in Azure

```bash
# Build image directly in Azure Container Registry
az acr build \
  --registry imaginecupreg999 \
  --image supply-chain-api:v11 \
  --image supply-chain-api:latest \
  --file Dockerfile \
  --platform linux/amd64 \
  .
```

**What happens:** Azure builds your Dockerfile in the cloud and pushes to registry.

### Step 2: Update Container App

```bash
# Load your .env file
source .env

# Update the container app
az containerapp update \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v11 \
  --set-env-vars \
    "DATABASE_URL=$DATABASE_URL" \
    "AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
    "AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY" \
    "AZURE_OPENAI_DEPLOYMENT_NAME=$AZURE_OPENAI_DEPLOYMENT_NAME" \
    "AZURE_OPENAI_API_VERSION=$AZURE_OPENAI_API_VERSION" \
    "PORT=8000" \
    "LOG_LEVEL=INFO"
```

### Step 3: Test Deployment

```bash
# Get your app URL
APP_URL=$(az containerapp show \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

# Test health endpoint
curl https://$APP_URL/api/health

# Open in browser
echo "Dashboard: https://$APP_URL"
echo "API Docs: https://$APP_URL/docs"
```

---

## Method 3: Local Docker Build + Push (Traditional)

If you prefer building locally:

### Prerequisites

```bash
# Ensure Docker is running
docker --version

# Login to ACR
az acr login --name imaginecupreg999
```

### Build and Push

```bash
# Build locally
docker build -t imaginecupreg999.azurecr.io/supply-chain-api:v11 \
  --platform linux/amd64 \
  -f Dockerfile .

# Push to registry
docker push imaginecupreg999.azurecr.io/supply-chain-api:v11

# Update container app (same as Method 2, Step 2)
az containerapp update \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v11 \
  --set-env-vars "DATABASE_URL=$DATABASE_URL" ...
```

---

## Blue-Green Deployment (Zero Downtime)

If you need zero downtime:

### Create New Revision

```bash
# Create new revision with 0% traffic
az containerapp revision copy \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v11
```

### Test New Revision

```bash
# Get revision URL
az containerapp revision list \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --query "[0].name" -o tsv

# Test the new revision independently
curl https://amazon-api-app--<revision>.purplepebble-*.azurecontainerapps.io/api/health
```

### Gradual Traffic Shift

```bash
# Send 10% traffic to new revision
az containerapp ingress traffic set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision-weight <old-revision>=90 <new-revision>=10

# If tests pass, send 100%
az containerapp ingress traffic set \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --revision-weight <new-revision>=100
```

---

## Troubleshooting

### ImagePullBackOff Error

**Cause:** Container can't pull image from registry.

**Solution 1:** Use ACR Build (Method 1) - builds in cloud, avoids this issue entirely.

**Solution 2:** Check ACR authentication:
```bash
# Verify ACR access
az acr login --name imaginecupreg999

# Check if container app has ACR pull permission
az containerapp show \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --query "properties.configuration.registries"
```

### Health Check Failing

**Symptoms:** Container restarts continuously.

**Debug steps:**
```bash
# 1. Check logs
az containerapp logs show \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --tail 50

# 2. Check if /api/health endpoint works
curl https://<your-app>.azurecontainerapps.io/api/health

# 3. Check environment variables
az containerapp show \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --query "properties.template.containers[0].env"
```

**Common fixes:**
- DATABASE_URL incorrect → Check connection string
- Missing AZURE_OPENAI_API_KEY → Add secret
- Wrong health probe path → Update `container-app-config.yaml`

### Database Connection Issues

```bash
# Test database connection locally first
python -c "
import os
from sqlalchemy import create_engine
engine = create_engine('$DATABASE_URL')
with engine.connect() as conn:
    print('✓ Database connected!')
"
```

### Port Mismatch

**Error:** Container exposed on wrong port.

**Fix:** Ensure Dockerfile exposes 8000 and container-app-config.yaml uses 8000:
```bash
az containerapp show \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --query "properties.configuration.ingress.targetPort"
```

---

## Post-Deployment Verification

### 1. Health Check
```bash
curl https://<your-app-url>/api/health
```

Expected response:
```json
{
  "status": "OK",
  "service": "supply-chain-agents",
  "version": "1.0.0",
  "agents": [
    "OrchestratorAgent",
    "PriceMonitoringAgent",
    "DemandForecastingAgent",
    "AutomatedOrderingAgent"
  ]
}
```

### 2. Test Inventory Endpoints
```bash
# List products
curl https://<your-app-url>/products?limit=5

# Get single product
curl https://<your-app-url>/products/B08N5WRWNW
```

### 3. Test Workflow Endpoint
```bash
# Run optimization workflow
curl -X POST "https://<your-app-url>/api/workflows/optimize-inventory?forecast_days=7"
```

### 4. Access Dashboard
Open in browser: `https://<your-app-url>/`

---

## Environment Variables Reference

Required in `.env` file:

```env
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://cog-xxx.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Optional
PORT=8000
LOG_LEVEL=INFO
```

---

## Comparison: Build Methods

| Method | Speed | Complexity | ImagePullBackOff Risk |
|--------|-------|------------|----------------------|
| **ACR Build (Cloud)** | ⚡ Fastest | ✅ Simplest | ❌ None |
| **Local Build + Push** | 🐌 Slowest | ⚠️ Medium | ⚠️ Possible |
| **CI/CD Pipeline** | ⚡ Fast | ⚙️ Complex | ❌ None |

---

## Quick Reference Commands

```bash
# View container apps
az containerapp list -g ImagineCup --query "[].{Name:name, Status:properties.runningStatus}" -o table

# View logs
az containerapp logs show --name amazon-api-app -g ImagineCup --tail 100

# View revisions
az containerapp revision list --name amazon-api-app -g ImagineCup -o table

# Restart app
az containerapp revision restart --name amazon-api-app -g ImagineCup

# Delete old revisions
az containerapp revision deactivate --name amazon-api-app -g ImagineCup --revision <old-revision>
```

---

## Need Help?

1. **Check logs first:** `az containerapp logs show --name amazon-api-app -g ImagineCup --tail 100`
2. **Verify .env file:** Ensure all required variables are set
3. **Test locally:** Run `uvicorn main:app --reload` to verify code works
4. **Review Dockerfile:** Ensure it builds successfully locally

---

## Next Steps After Deployment

1. ✅ Verify all endpoints work
2. ✅ Test the dashboard
3. ✅ Run a test workflow: `/api/workflows/optimize-inventory`
4. ✅ Set up Application Insights for monitoring
5. ✅ Configure custom domain (optional)
6. ✅ Deploy MCP servers (optional, for advanced agent features)

For MCP server deployment, see [docs/mcp_deploy.md](docs/mcp_deploy.md).
