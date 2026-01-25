# Deployment Standards

## 1. Repository Structure
The repository is structured with the implementation root at `/Users/tarive/imaginecup2026`.
- `main.py` (Base application)
- `database/` (Shared database models and config)
- `realtime_price_agent/` (Agent implementations)
- `frontend/` (Next.js application)

## 2. Dependency Management
We use **uv** for dependency management.
- **DO NOT** use `requirements.txt`.
- All dependencies are managed in `pyproject.toml` at the root.
- Docker builds install dependencies using **uv**:
  ```dockerfile
  COPY pyproject.toml ./
  RUN pip install uv
  RUN uv pip install --system --no-cache-dir -e .
  ```

## 3. CI/CD & Docker Build Standards
### Build Context
Docker builds for the backend MUST be run from the **ROOT** of the repository (`.`) to access shared modules like `database/` and the root `pyproject.toml`.

**Correct (GitHub Actions / scripts):**
```yaml
cd realtime_price_agent
az acr build --file Dockerfile . 
```
*Note: The `.` context refers to the repository root if you run it from root, but if changing dir, ensure the relative path to root files is valid OR rely on `COPY . .` copying the current context.*

**WAIT**: The GitHub Action now does:
```yaml
cd realtime_price_agent
az acr build ... --file Dockerfile .
```
This sets the context to `realtime_price_agent` directory.
**correction**: If `pyproject.toml` is at root, and we build from `realtime_price_agent` context, **IT WILL NOT BE FOUND**.

**CRITICAL FIX**:
If `pyproject.toml` is at **ROOT**, then the build context MUST be ROOT.
The GitHub Action I just verified:
```yaml
            az acr build \
              ...
              --file realtime_price_agent/Dockerfile \
              .
```
(I executed this replacement in Step 234).
This sets the context to `.` (ROOT).
So the Dockerfile at `realtime_price_agent/Dockerfile` will see:
`COPY pyproject.toml ./` -> Copies from ROOT context. This works.
`COPY . .` -> Copies ROOT context into `/app`.

**Standard:**
- **Context**: Repository Root (`.`)
- **Dockerfile Path**: `realtime_price_agent/Dockerfile`

### Azure Container Registry
- **Updates**: Use `az acr build` (via `azure/CLI` action).
- **Credentials**: Handled automatically by `azure/login`. Do NOT pass JSON credentials manually to `az acr build` actions.

## 4. MCP Integration
- MCP URLs are dynamic internal services (Container Apps).
- They are fetched at deployment time via `az containerapp show`.
- No manual secrets required for MCP URLs.
