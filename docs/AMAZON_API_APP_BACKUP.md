# Amazon API App - Legacy Deployment Reference

> **Status:** Decommissioned on 2026-01-17 for cost optimization.  
> **Note:** This container was a legacy backend superseded by `supplymind-backend`.

## Container Configuration (Backup)

| Property | Value |
|----------|-------|
| **Image** | `imaginecupreg999.azurecr.io/supply-chain-api:v11` |
| **CPU** | 1.0 |
| **Memory** | 2Gi |
| **Port** | 8000 |
| **FQDN** | `amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io` |

## Environment Variables

```bash
# Use values from .env file or Azure Key Vault
DATABASE_URL=${DATABASE_URL}
AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
PORT=8000
LOG_LEVEL=INFO
```

## Redeploy Command (If Needed)

```bash
# 1. Create container app from existing image
az containerapp create \
  --name amazon-api-app \
  --resource-group ImagineCup \
  --image imaginecupreg999.azurecr.io/supply-chain-api:v11 \
  --target-port 8000 \
  --ingress external \
  --cpu 1.0 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    DATABASE_URL="$DATABASE_URL" \
    AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
    AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5-mini" \
    AZURE_OPENAI_API_VERSION="2024-12-01-preview" \
    PORT="8000" \
    LOG_LEVEL="INFO"
```

## Codebase References

These files contain hardcoded references to this container:

- `realtime_price_agent/main.py` - Lines 372, 417, 453 (price sync endpoints)
- `realtime_price_agent/mcp_servers/integrations/server.py` - Line 53

**Note:** These endpoints are admin utilities, not called by the frontend.
