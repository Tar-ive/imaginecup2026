# Azure Cost Optimization Summary

**Date:** January 17, 2026  
**Initial Monthly Cost:** ~$71.50  
**Final Monthly Cost:** ~$15  
**Total Savings:** ~$56/month (78%)

---

## Deletions Completed

### Phase 1C: Legacy Container Apps

| Resource | Resource Group | Type | Monthly Cost | Status |
|----------|---------------|------|--------------|--------|
| `amazon-api-app` | ImagineCup | Container App | $8.67 | ✅ Deleted |
| `supply-chain-api-new` | ImagineCup | Container App | $35.80 | ✅ Deleted |

**Backup created:** [AMAZON_API_APP_BACKUP.md](./AMAZON_API_APP_BACKUP.md)

### Phase 2: ML Workspace

| Resource | Resource Group | Type | Monthly Cost | Status |
|----------|---------------|------|--------------|--------|
| `ImagineCup` | ImagineCup | ML Workspace | $1.39 | ✅ Deleted |

### Phase 3: Right-Sizing

| Resource | Change | Monthly Savings | Status |
|----------|--------|-----------------|--------|
| `supplymind-backend` | 1.0 CPU/2Gi → 0.5 CPU/1Gi | ~$10 | ✅ Applied |

---

## Current Active Resources (ImagineCup)

| Resource | CPU | Memory | Min Replicas | Est. Cost |
|----------|-----|--------|--------------|-----------|
| `supplymind-backend` | 0.5 | 1Gi | 1 | ~$10/mo |
| `supplymind-frontend` | 0.5 | 1Gi | 1 | ~$3/mo |
| `mcp-supplier-data` | 0.5 | 1Gi | 0 | ~$0.02/mo |
| `mcp-inventory-mgmt` | 0.5 | 1Gi | 0 | ~$0.02/mo |
| `mcp-finance-data` | 0.5 | 1Gi | 0 | ~$0.02/mo |
| `mcp-analytics-forecast` | 0.5 | 1Gi | 0 | ~$0.02/mo |
| `mcp-integrations` | 0.5 | 1Gi | 0 | ~$0.02/mo |
| `imaginecupreg999` | - | - | - | ~$2/mo |

---

## Potentially Unused Resource Groups

### rg-team-cosmos (10 resources)

| Resource | Type | Used? |
|----------|------|-------|
| `ca-api-2oy26vbxhdqti` | Container App | ❌ Not used |
| `aoai-2oy26vbxhdqti` | Azure OpenAI | ❌ Not used |
| `cr2oy26vbxhdqti` | Container Registry | ❌ Not used |
| `st2oy26vbxhdqti` | Storage Account | ❌ Not used |
| `log-2oy26vbxhdqti` | Log Analytics | Supporting |
| `appi-2oy26vbxhdqti` | App Insights | Supporting |
| + 4 supporting resources | | |

**Status:** Ready to delete (not used by SupplyMind)

### rg-bhattaraikusum51-8374 (2 resources)

| Resource | Type | Used? |
|----------|------|-------|
| `bhattaraikusum51-8374-resource` | Azure OpenAI | ❌ Not used |

**Status:** Ready to delete (not used by SupplyMind)

---

## ⚠️ Outstanding: Production Azure OpenAI Endpoint

**The production endpoint is NOT in any visible resource group:**

```
AZURE_OPENAI_ENDPOINT=https://cog-4rvgq5cq47ltg.openai.azure.com/
```

### What We Know
- ✅ Endpoint is working (HTTP 200)
- ✅ Used by `supplymind-backend` in production
- ❌ Not found in `Azure subscription 1`
- ❌ Not in ImagineCup, rg-team-cosmos, or rg-bhattaraikusum51-8374

### Possible Locations
1. Different Azure subscription/account
2. Azure AI Foundry managed resource (https://ai.azure.com)
3. Shared team resource

### Action Required
- [ ] Log into Azure Portal and search "cog-4rv" in All Resources
- [ ] Check Azure AI Foundry at https://ai.azure.com
- [ ] Document the actual resource group location

---

## Environment Variables Reference

The following endpoints are used in production (`.env`):

```bash
# PRODUCTION DATABASE
DATABASE_URL=postgresql://neondb_owner:***@ep-super-lab-a8x2j9of-pooler.eastus2.azure.neon.tech/neondb

# AZURE OPENAI (SOURCE UNKNOWN)
AZURE_OPENAI_ENDPOINT=https://cog-4rvgq5cq47ltg.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini
```
