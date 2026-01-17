# SupplyMind - Quick Reference Card

## Deployment Commands

### Full Deployment (Backend + Frontend)
```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents
./deploy-all.sh
```

### Backend Only
```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents
./deploy-backend.sh
```

### Frontend Only (Backend already deployed)
```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents
./deploy-frontend.sh --backend-url https://backend-url
# OR let it auto-detect from .backend-url.sh
./deploy-frontend.sh
```

### Deploy with Options
```bash
# Skip backend (use existing)
./deploy-all.sh --skip-backend

# Skip frontend
./deploy-all.sh --skip-frontend

# Frontend only mode
./deploy-all.sh --frontend-only
```

## Azure CLI Commands

### View Logs
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

# Last 100 lines
az containerapp logs show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --tail 100
```

### Check Status
```bash
# Backend status
az containerapp show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query "properties.{status:runningStatus,url:configuration.ingress.fqdn}" \
  -o table

# Frontend status
az containerapp show \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --query "properties.{status:runningStatus,url:configuration.ingress.fqdn}" \
  -o table

# List all container apps
az containerapp list \
  --resource-group ImagineCup \
  --query "[].{name:name,status:properties.runningStatus,url:properties.configuration.ingress.fqdn}" \
  -o table
```

### Scale Applications
```bash
# Scale backend
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

### Restart Applications
```bash
# Restart backend
az containerapp revision restart \
  --name supplymind-backend \
  --resource-group ImagineCup

# Restart frontend
az containerapp revision restart \
  --name supplymind-frontend \
  --resource-group ImagineCup
```

### View Environment Variables
```bash
# Backend env vars
az containerapp show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query "properties.template.containers[0].env" \
  -o table

# Frontend env vars
az containerapp show \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --query "properties.template.containers[0].env" \
  -o table
```

### List Container Images
```bash
# List all images in ACR
az acr repository list \
  --name imaginecupreg999 \
  -o table

# List tags for backend image
az acr repository show-tags \
  --name imaginecupreg999 \
  --repository supply-chain-api \
  -o table

# List tags for frontend image
az acr repository show-tags \
  --name imaginecupreg999 \
  --repository supplymind-frontend \
  -o table
```

## Health Check URLs

Replace `{domain}` with actual FQDN from deployment output.

### Backend
```bash
# Health check
curl https://{backend-domain}/api/health

# API documentation
open https://{backend-domain}/docs

# List products
curl https://{backend-domain}/products?limit=5

# List suppliers
curl https://{backend-domain}/suppliers?limit=5

# Workflow status
curl https://{backend-domain}/api/workflows/pending-approvals
```

### Frontend
```bash
# Homepage
open https://{frontend-domain}

# Health check (if implemented)
curl https://{frontend-domain}/api/health

# Test backend connectivity
curl https://{frontend-domain}/api/proxy/api/health
```

## Troubleshooting Commands

### Check if containers are running
```bash
az containerapp replica list \
  --name supplymind-backend \
  --resource-group ImagineCup \
  -o table
```

### View recent revisions
```bash
az containerapp revision list \
  --name supplymind-backend \
  --resource-group ImagineCup \
  -o table
```

### Rollback to previous revision
```bash
# List revisions first
az containerapp revision list \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query "[].{name:name,active:properties.active,created:properties.createdTime}" \
  -o table

# Activate specific revision
az containerapp revision activate \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --revision {revision-name}
```

### Test database connection
```bash
# From local machine
psql "postgresql://neondb_owner:npg_xv9gsUFdC8yA@ep-super-lab-a8x2j9of-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"

# Or via backend
curl https://{backend-domain}/products?limit=1
```

### Check MCP servers
```bash
# List all tools
curl https://{backend-domain}/api/tools

# Check specific MCP server
curl https://mcp-supplier-data.bluewave-ee01b5af.eastus.azurecontainerapps.io/health
curl https://mcp-inventory-mgmt.bluewave-ee01b5af.eastus.azurecontainerapps.io/health
curl https://mcp-finance-data.bluewave-ee01b5af.eastus.azurecontainerapps.io/health
curl https://mcp-analytics-forecast.bluewave-ee01b5af.eastus.azurecontainerapps.io/health
curl https://mcp-integrations.bluewave-ee01b5af.eastus.azurecontainerapps.io/health
```

## Docker Commands (Local Testing)

### Build locally
```bash
# Backend
cd realtime_price_agent
docker build -t supplymind-backend .

# Frontend (after Dockerfile is ready)
cd frontend
docker build -t supplymind-frontend \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  .
```

### Run locally
```bash
# Backend
docker run -p 8000:8000 --env-file ../.env supplymind-backend

# Frontend
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  supplymind-frontend
```

### Test local setup
```bash
# Terminal 1: Start backend
cd realtime_price_agent
docker run -p 8000:8000 --env-file ../.env supplymind-backend

# Terminal 2: Start frontend
cd frontend
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  supplymind-frontend

# Terminal 3: Test
curl http://localhost:8000/api/health
curl http://localhost:3000
open http://localhost:3000
```

## Monitoring & Metrics

### Get resource usage
```bash
az containerapp show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query "properties.{cpu:template.containers[0].resources.cpu,memory:template.containers[0].resources.memory}" \
  -o table
```

### View metrics in Azure Portal
```bash
# Open backend in portal
az containerapp show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query "id" \
  -o tsv | xargs -I {} open "https://portal.azure.com/#@/resource{}/metrics"
```

## Cost Management

### Estimate current costs
```bash
az consumption usage list \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  | jq '.[] | select(.instanceName | contains("supplymind"))'
```

### Check resource allocation
```bash
az containerapp list \
  --resource-group ImagineCup \
  --query "[].{name:name,cpu:properties.template.containers[0].resources.cpu,memory:properties.template.containers[0].resources.memory}" \
  -o table
```

## Emergency Procedures

### Complete Outage
```bash
# Check if Azure is having issues
az account show

# Restart both apps
az containerapp revision restart --name supplymind-backend --resource-group ImagineCup
az containerapp revision restart --name supplymind-frontend --resource-group ImagineCup

# Check logs for errors
az containerapp logs show --name supplymind-backend --resource-group ImagineCup --tail 100
```

### Database Connection Issues
```bash
# Test from backend
curl https://{backend-domain}/products?limit=1

# Check if database is up (Neon dashboard)
open https://console.neon.tech/

# Verify DATABASE_URL is correct
az containerapp show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --query "properties.template.containers[0].env[?name=='DATABASE_URL'].value" \
  -o tsv
```

### MCP Servers Down
```bash
# Check each MCP server
for server in supplier-data inventory-mgmt finance-data analytics-forecast integrations; do
  echo "Checking mcp-$server..."
  curl -sf https://mcp-$server.bluewave-ee01b5af.eastus.azurecontainerapps.io/health || echo "FAILED"
done
```

## Common File Locations

```
/Users/quamos/Repos/imaginecup2026/
├── .env                                  # Environment variables
├── azure-agents/
│   ├── DEPLOYMENT_PLAN.md               # Full deployment guide
│   ├── QUICK_REFERENCE.md               # This file
│   ├── deploy-all.sh                    # Master deployment script
│   ├── deploy-backend.sh                # Backend deployment
│   ├── deploy-frontend.sh               # Frontend deployment
│   ├── .backend-url.sh                  # Generated backend URL
│   ├── frontend/
│   │   ├── Dockerfile.template          # Frontend Dockerfile
│   │   ├── DEPLOYMENT_CHECKLIST.md      # Frontend prep guide
│   │   └── ...                          # Next.js app
│   └── realtime_price_agent/
│       ├── Dockerfile                   # Backend Dockerfile
│       ├── main.py                      # FastAPI app
│       └── ...                          # Python modules
```

## Support & Documentation

- **Azure Container Apps**: https://learn.microsoft.com/azure/container-apps/
- **Azure CLI**: https://learn.microsoft.com/cli/azure/
- **Next.js Deployment**: https://nextjs.org/docs/deployment
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/

---

**Last Updated**: 2026-01-09

**Tip**: Bookmark this file for quick access to common commands!
