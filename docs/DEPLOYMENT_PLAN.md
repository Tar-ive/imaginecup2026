# SupplyMind - Azure Deployment Plan

## Architecture Overview

### Current Setup
- **Backend**: FastAPI (Python 3.11) - Port 8000
- **Frontend**: Next.js 15 (Node 20) - Port 3000
- **Database**: Neon PostgreSQL (managed)
- **MCP Servers**: 5 microservices already deployed
- **Resource Group**: ImagineCup
- **Container Registry**: imaginecupreg999

### Deployment Strategy: Two-Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                      │
├──────────────────────────────┬──────────────────────────────┤
│   Frontend Container         │   Backend Container          │
│   (Next.js)                  │   (FastAPI)                  │
│   - Port 3000                │   - Port 8000                │
│   - Proxies to Backend       │   - REST API                 │
│   - Static Assets            │   - Agent Orchestration      │
│   - SSR/SSG                  │   - Database Access          │
└──────────────────────────────┴──────────────────────────────┘
                    │                      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Neon PostgreSQL    │
                    │  (External)         │
                    └─────────────────────┘
```

## Why Two Containers?

### 1. **Independent Scaling**
   - Frontend: High traffic, low CPU (static serving, SSR)
   - Backend: Lower traffic, high CPU (AI agents, database queries)
   - Scale each based on actual needs

### 2. **Resource Optimization**
   - Frontend: 0.5 CPU, 1Gi RAM
   - Backend: 1.0 CPU, 2Gi RAM
   - Cost savings vs single container

### 3. **Independent Deployment**
   - Update frontend without backend restart
   - Update backend without frontend rebuild
   - Faster CI/CD pipelines

### 4. **Better Debugging**
   - Separate logs per service
   - Isolated monitoring
   - Easier troubleshooting

### 5. **Technology Isolation**
   - Node.js runtime for Next.js
   - Python runtime for FastAPI
   - No runtime conflicts

## Container Configuration

### Frontend Container
```yaml
Name: supplymind-frontend
Image: imaginecupreg999.azurecr.io/supplymind-frontend:latest
Port: 3000
Resources:
  CPU: 0.5
  Memory: 1Gi
Replicas: 1-3
Environment:
  - NEXT_PUBLIC_API_URL: https://supplymind-backend.{domain}
  - NODE_ENV: production
```

### Backend Container
```yaml
Name: supplymind-backend
Image: imaginecupreg999.azurecr.io/supply-chain-api:latest
Port: 8000
Resources:
  CPU: 1.0
  Memory: 2Gi
Replicas: 1-3
Environment:
  - DATABASE_URL: <from .env>
  - AZURE_OPENAI_ENDPOINT: <from .env>
  - AZURE_OPENAI_API_KEY: <from .env>
  - AZURE_OPENAI_DEPLOYMENT_NAME: <from .env>
  - AZURE_OPENAI_API_VERSION: <from .env>
  - MCP_SUPPLIER_DATA_URL: <from .env>
  - MCP_INVENTORY_MGMT_URL: <from .env>
  - MCP_FINANCE_DATA_URL: <from .env>
  - MCP_ANALYTICS_FORECAST_URL: <from .env>
  - MCP_INTEGRATIONS_URL: <from .env>
  - PORT: 8000
  - LOG_LEVEL: INFO
```

## Communication Flow

1. **User Request** → Frontend (https://supplymind-frontend.{domain})
2. **Frontend** → API Proxy (`/api/proxy/*`)
3. **API Proxy** → Backend (https://supplymind-backend.{domain})
4. **Backend** → Database / MCP Servers / OpenAI
5. **Response** ← Through chain back to user

### Key Environment Variable
The frontend's `NEXT_PUBLIC_API_URL` must point to the backend's public URL:
```bash
NEXT_PUBLIC_API_URL=https://supplymind-backend.bluewave-ee01b5af.eastus.azurecontainerapps.io
```

## Deployment Scripts

### 1. `deploy-backend.sh`
- Builds backend image in ACR
- Deploys/updates backend container app
- Configures all environment variables
- Sets up health checks

### 2. `deploy-frontend.sh`
- Builds frontend image in ACR (with backend URL)
- Deploys/updates frontend container app
- Configures environment variables
- Sets up ingress

### 3. `deploy-all.sh` (Master Script)
- Validates .env file
- Deploys backend first
- Captures backend URL
- Deploys frontend with backend URL
- Runs health checks
- Displays both URLs

## Deployment Steps (When Ready)

### Prerequisites
```bash
# Install Azure CLI
brew install azure-cli  # macOS
# OR
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash  # Linux

# Login to Azure
az login

# Set subscription
az account set --subscription "8648ece4-f125-406e-86ee-ecddc7e70962"
```

### Step 1: Deploy Backend
```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/realtime_price_agent
./deploy-backend.sh
```

Expected output:
- ✅ Image built in ACR
- ✅ Backend deployed
- 🌐 Backend URL: https://supplymind-backend.{domain}

### Step 2: Deploy Frontend
```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/frontend
./deploy-frontend.sh
```

Expected output:
- ✅ Image built in ACR
- ✅ Frontend deployed
- 🌐 Frontend URL: https://supplymind-frontend.{domain}

### Step 3: Or Deploy Both at Once
```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents
./deploy-all.sh
```

## Health Checks

### Backend Health
```bash
curl https://supplymind-backend.{domain}/api/health
```

Expected response:
```json
{
  "status": "OK",
  "service": "supply-chain-agents",
  "version": "1.0.0",
  "agents": ["OrchestratorAgent", "PriceMonitoringAgent", ...],
  "mcp": {"total_servers": 5, ...}
}
```

### Frontend Health
```bash
curl https://supplymind-frontend.{domain}
```

Expected: HTML page loads successfully

### End-to-End Test
```bash
curl https://supplymind-frontend.{domain}/api/proxy/api/health
```

This tests frontend → backend communication.

## Cost Estimation

### Current (Single Container)
- 1.0 CPU × 2Gi RAM × 730 hours/month
- Estimated: $50-70/month

### Proposed (Two Containers)
- Frontend: 0.5 CPU × 1Gi RAM × 730 hours = ~$20-25/month
- Backend: 1.0 CPU × 2Gi RAM × 730 hours = ~$50-70/month
- **Total: $70-95/month**

**Note**: Slightly higher base cost, but better performance and scalability. Actual cost depends on:
- Traffic patterns
- Auto-scaling configuration
- Data transfer

## Rollback Strategy

### If Issues with New Deployment

#### Option 1: Rollback via Script
```bash
./deploy-backend.sh --tag v10  # Deploy previous version
```

#### Option 2: Manual Rollback
```bash
az containerapp update \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v10
```

#### Option 3: Azure Portal
1. Go to Container Apps → supplymind-backend
2. Click "Revisions"
3. Select previous working revision
4. Click "Activate"

## Monitoring & Logs

### View Backend Logs
```bash
az containerapp logs show \
  --name supplymind-backend \
  --resource-group ImagineCup \
  --follow
```

### View Frontend Logs
```bash
az containerapp logs show \
  --name supplymind-frontend \
  --resource-group ImagineCup \
  --follow
```

### Application Insights (Optional)
- Can be added for advanced monitoring
- Tracks performance, errors, dependencies
- Cost: ~$5-10/month for this scale

## Security Considerations

### 1. **Secrets Management**
- ✅ Secrets in environment variables (Container Apps)
- 🔄 Consider Azure Key Vault for production
- ❌ Never commit .env to git

### 2. **Network Security**
- ✅ HTTPS only (automatic with Container Apps)
- ✅ CORS configured in backend
- 🔄 Consider VNet integration for MCP servers

### 3. **Database Security**
- ✅ SSL/TLS connections (Neon)
- ✅ Connection pooling
- ✅ Read-only credentials for read operations

## Next Steps (Checklist)

- [ ] Frontend development complete
- [ ] Create frontend Dockerfile
- [ ] Test local Docker builds
- [ ] Update .env with any new variables
- [ ] Run deploy-all.sh script
- [ ] Verify both containers are running
- [ ] Test all API endpoints
- [ ] Test frontend UI flows
- [ ] Set up monitoring/alerts
- [ ] Document final URLs
- [ ] Update DNS (if custom domain)

## Troubleshooting

### Frontend can't reach backend
1. Check NEXT_PUBLIC_API_URL is correct
2. Verify backend is running: `az containerapp show --name supplymind-backend ...`
3. Test backend directly: `curl https://supplymind-backend.{domain}/api/health`
4. Check frontend logs for connection errors

### Backend database errors
1. Verify DATABASE_URL is correct
2. Check Neon database is accessible
3. Verify connection pooling settings
4. Check backend logs for specific error

### Build failures
1. Check Dockerfile syntax
2. Verify all dependencies in package.json/requirements.txt
3. Check build logs in ACR: `az acr task logs ...`
4. Ensure sufficient ACR storage

### High costs
1. Check auto-scaling settings (max replicas)
2. Review resource allocations (CPU/RAM)
3. Check data transfer volumes
4. Consider reserved capacity

## Support & Resources

- **Azure Container Apps Docs**: https://learn.microsoft.com/azure/container-apps/
- **Next.js Deployment**: https://nextjs.org/docs/deployment
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Azure CLI Reference**: https://learn.microsoft.com/cli/azure/

---

**Last Updated**: 2026-01-09
**Maintained By**: DevOps Team
