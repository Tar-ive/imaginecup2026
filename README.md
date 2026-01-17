# SupplyMind - Azure AI Supply Chain Platform

AI-powered supply chain optimization platform using Azure AI Foundry and multi-agent architecture.

---

## Repository Structure

```
azure-agents/
├── frontend/                   # Next.js 15 frontend application
│   ├── app/                   # Next.js app router
│   ├── components/            # React components
│   └── Dockerfile
│
├── realtime_price_agent/       # FastAPI backend + AI agents
│   ├── agents/                # AI agent implementations
│   │   ├── automated_ordering/
│   │   ├── demand_forecasting/
│   │   ├── negotiation/
│   │   ├── orchestrator/
│   │   └── price_monitoring/
│   ├── database/              # Database models & migrations
│   ├── mcp_servers/           # MCP server implementations
│   ├── services/              # Business logic services
│   ├── schemas/               # Pydantic schemas
│   ├── legacy/                # Legacy code reference
│   ├── notebooks/             # Jupyter notebooks
│   └── main.py                # FastAPI application
│
├── docs/                       # Documentation
│   └── DEPLOYMENT_STANDARDS.md # Deployment guide
│
├── scripts/                    # All deployment & utility scripts
│   ├── deploy-all.sh          # Deploy everything
│   ├── deploy-backend.sh      # Deploy backend only
│   ├── deploy-frontend.sh     # Deploy frontend only
│   └── ...                    # See docs/DEPLOYMENT_STANDARDS.md
│
├── docker-compose.yml          # Local development
├── package.json                # Root package config
└── README.md                   # This file
```

---

## Quick Start

### Prerequisites
- Azure CLI (`az login`)
- Docker (for local development)
- Node.js 20+, Python 3.11+

### Deploy to Azure
```bash
# Deploy both frontend and backend
./scripts/deploy-all.sh
```

### Local Development
```bash
# Start all services
docker-compose up
```

---

## Documentation

- **[Deployment Standards](docs/DEPLOYMENT_STANDARDS.md)** - Complete deployment guide, scripts reference, and troubleshooting

---

## ⚠️ Important: Local-Only Files

The following files/folders are **local only** and should never be committed:

| Path | Purpose |
|------|---------|
| `.env` | Environment secrets |
| `.venv/`, `venv/` | Python virtual environments |
| `azure-ai-travel-agents/` | External reference repository |
| `ucp-python-sdk/` | External SDK reference |
| `node_modules/` | Node dependencies |

These are already in `.gitignore`. **Do not remove them from .gitignore.**

---

## Tech Stack

- **Frontend**: Next.js 15, React 19, TailwindCSS, shadcn/ui
- **Backend**: FastAPI, Python 3.11, SQLAlchemy
- **AI**: Azure OpenAI, Multi-Agent Architecture
- **Database**: Neon PostgreSQL (serverless)
- **Deployment**: Azure Container Apps

---

*Last Updated: 2026-01-17*