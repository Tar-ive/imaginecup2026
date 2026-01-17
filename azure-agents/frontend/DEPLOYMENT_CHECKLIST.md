# Frontend Deployment Checklist

Before deploying the frontend to Azure, complete these steps:

## 1. Update Next.js Configuration

Edit `next.config.mjs` to enable standalone output mode:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
}

export default nextConfig
```

**Why?** Standalone mode creates an optimized production build that includes only necessary files, reducing Docker image size from ~1GB to ~150MB.

## 2. Prepare the Dockerfile

Rename the Dockerfile template:

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents/frontend
mv Dockerfile.template Dockerfile
```

The Dockerfile is already configured for:
- Multi-stage build (optimized size)
- Non-root user (security)
- Health checks
- Build-time API URL injection

## 3. Add API Health Endpoint (Optional)

Create a health check endpoint for the frontend:

```bash
# Create the file
mkdir -p app/api/health
touch app/api/health/route.ts
```

Add this content to `app/api/health/route.ts`:

```typescript
export async function GET() {
  return Response.json({
    status: 'ok',
    timestamp: new Date().toISOString()
  })
}
```

This allows Docker health checks and monitoring tools to verify the frontend is running.

## 4. Test Local Docker Build

Before deploying to Azure, test the Docker build locally:

```bash
# Build the image
docker build -t supplymind-frontend \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  .

# Run the container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  supplymind-frontend

# Test in another terminal
curl http://localhost:3000
curl http://localhost:3000/api/health  # if you added health endpoint
```

## 5. Verify Environment Variables

The frontend needs only one environment variable:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-url.azurecontainerapps.io
```

This is automatically set during deployment by `deploy-frontend.sh`.

## 6. Check Dependencies

Ensure all dependencies are in `package.json`:

```bash
# Install and verify
npm install
npm run build

# Check for any build errors
```

Common issues:
- Missing peer dependencies
- TypeScript errors (can be ignored with `ignoreBuildErrors: true`)
- ESLint errors (can be ignored with `ignoreDuringBuilds: true`)

## 7. Optimize for Production

Consider these optimizations:

### Remove Development-Only Code

```typescript
// Remove console.logs in production
if (process.env.NODE_ENV === 'production') {
  console.log = () => {}
  console.warn = () => {}
}
```

### Enable Compression

Already handled by Next.js automatically.

### Configure Caching

Next.js handles this automatically with its built-in caching.

## 8. Ready to Deploy?

Once all the above is complete, you're ready to deploy:

### Option 1: Deploy Frontend Only (Backend Already Running)

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents
./deploy-frontend.sh --backend-url https://your-backend-url
```

### Option 2: Deploy Everything

```bash
cd /Users/quamos/Repos/imaginecup2026/azure-agents
./deploy-all.sh
```

This will:
1. Deploy backend first
2. Capture backend URL
3. Deploy frontend with correct backend URL
4. Run health checks
5. Display both URLs

## Common Issues and Solutions

### Issue: "Module not found" during build

**Solution**: Run `npm install` again and check package.json

### Issue: Build fails with "output: standalone" error

**Solution**: Ensure you're using Next.js 12+ (you have 15.5.9, so this is fine)

### Issue: Frontend can't reach backend

**Solution**:
1. Check `NEXT_PUBLIC_API_URL` is set correctly
2. Verify backend is running: `curl https://backend-url/api/health`
3. Check proxy routes in `app/api/proxy/[...path]/route.ts`

### Issue: Docker build is slow

**Solution**:
1. First build will be slow (~5-10 minutes)
2. Subsequent builds use cache (~2-3 minutes)
3. Azure ACR build is faster than local builds

### Issue: Container starts but app doesn't work

**Solution**:
1. Check logs: `az containerapp logs show --name supplymind-frontend --resource-group ImagineCup --follow`
2. Verify environment variables are set
3. Check if backend URL is correct

## Deployment Architecture

```
User Browser
    |
    v
Azure Container Apps (Frontend)
    |
    v (via /api/proxy/*)
Azure Container Apps (Backend)
    |
    v
Neon PostgreSQL + MCP Servers
```

## Security Considerations

1. **HTTPS Only**: Container Apps enforce HTTPS automatically
2. **No Secrets in Frontend**: All secrets are in backend only
3. **API Proxy**: Frontend proxies requests to avoid CORS
4. **Non-root User**: Docker container runs as non-root user

## Cost Estimation

- **Frontend Container**: ~$20-25/month
  - 0.5 CPU, 1Gi RAM
  - Auto-scales 1-3 replicas
  - Mostly idle when no traffic

## Rollback Plan

If deployment fails, rollback to previous version:

```bash
# List available images
az acr repository show-tags --name imaginecupreg999 --repository supplymind-frontend

# Deploy specific version
./deploy-frontend.sh --tag v20260109-143000
```

## Monitoring

After deployment, monitor:

1. **Application Insights** (optional, ~$5/month)
2. **Container Logs**: `az containerapp logs show ...`
3. **Metrics**: CPU, Memory, Requests (in Azure Portal)

## Next Steps After Deployment

1. Test all user flows in production
2. Set up custom domain (optional)
3. Configure CDN for static assets (optional)
4. Set up monitoring alerts
5. Document the production URLs

---

**Questions?** Check the main [DEPLOYMENT_PLAN.md](../DEPLOYMENT_PLAN.md) for more details.
