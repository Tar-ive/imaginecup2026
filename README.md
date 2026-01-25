# SupplyMind - Azure AI Supply Chain Platform
AI-powered supply chain optimization platform using Azure AI Foundry and multi-agent architecture.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- PostgreSQL database (or Neon connection string)
- Azure OpenAI credentials

### Installation

```bash
# 1. Clone and enter the repo
git clone https://github.com/Tar-ive/imaginecup2026.git
cd imaginecup2026

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install Python dependencies
uv sync --all-extras

# 4. Copy and configure environment
cp .env.sample .env
# Edit .env with your credentials:
#   DATABASE_URL, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, etc.

# 5. Install frontend dependencies
cd frontend && npm install && cd ..
```

### Running Locally

```bash
# Terminal 1: Backend
cd realtime_price_agent
uv run uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Repository Structure

```
imaginecup2026/
├── frontend/                   # Next.js 15 frontend
├── realtime_price_agent/       # FastAPI backend + AI agents
│   ├── agents/                # AI agent implementations
│   ├── database/              # Database models
│   ├── mcp_servers/           # MCP server implementations
│   ├── services/              # Business logic
│   └── main.py                # FastAPI application
├── scripts/                    # Deployment scripts
├── docs/                       # Documentation
├── pyproject.toml              # Python dependencies (uv)
└── docker-compose.yml          # Local development
```

---

## Dependency Management

This project uses **[uv](https://docs.astral.sh/uv/)** for Python dependency management.

```bash
# Install all dependencies (including ML, AP2, telemetry)
uv sync --all-extras

# Install specific extras
uv sync --extra ml          # XGBoost, scikit-learn
uv sync --extra ap2         # PyJWT, cryptography
uv sync --extra telemetry   # OpenTelemetry

# Add a new dependency
uv add <package-name>

# Run any Python command
uv run python script.py
uv run pytest
```

---

## Deploy to Azure

```bash
./scripts/deploy-all.sh
```

See [docs/DEPLOYMENT_STANDARDS.md](docs/DEPLOYMENT_STANDARDS.md) for details.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, React 19, TailwindCSS, shadcn/ui |
| Backend | FastAPI, Python 3.11, SQLAlchemy |
| AI | Azure OpenAI, Multi-Agent Architecture |
| Database | Neon PostgreSQL (serverless) |
| Package Manager | uv (Python), npm (Node.js) |
| Deployment | Azure Container Apps |

---

## Local-Only Files

These files are in `.gitignore` and should never be committed:

| Path | Purpose |
|------|---------|
| `.env` | Environment secrets |
| `.venv/` | Python virtual environment (created by uv) |
| `uv.lock` | Lock file (optional to commit) |
| `node_modules/` | Node dependencies |

---

*Last Updated: 2026-01-25*