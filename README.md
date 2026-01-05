# Supply Chain Agents

An AI-powered **supply chain optimization system** with demand forecasting, realtime price monitoring, and automated order recommendations. Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework), FastAPI, and XGBoost ML models.

![Dashboard](docs/assets/dashboard-preview.png)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📈 **Demand Forecasting** | XGBoost ML model trained on order history with confidence intervals |
| 💰 **Realtime Pricing** | Live price fetching from Amazon API |
| 📦 **Order Recommendations** | Smart reorder suggestions grouped by supplier |
| 📊 **Live Dashboard** | Real-time telemetry with SSE streaming |
| 🤖 **AI Agents** | Orchestrated workflow using Microsoft Agent Framework |
| 🔄 **Human-in-the-Loop** | Optional approval for high-value orders |

## 🚀 Quick Start

### One-Command Setup

```bash
# Clone and setup
git clone <repo-url>
cd realtime_price_agent

# Run the setup script (creates venv, installs deps, checks env)
./scripts/setup.sh

# Start the server
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Open dashboard
open http://localhost:8000
```

### Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -e .
pip install xgboost scikit-learn

# macOS only: Install OpenMP for XGBoost
brew install libomp

# 3. Configure environment
cp .env.sample .env
# Edit .env with your credentials

# 4. Run
uvicorn main:app --reload --port 8000
```

## ⚙️ Environment Variables

Create a `.env` file with:

```env
# Required: Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Required: Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Optional: MCP Server URLs (for agent tools)
MCP_SUPPLIER_URL=http://localhost:3001
MCP_INVENTORY_URL=http://localhost:3002
MCP_FINANCE_URL=http://localhost:3003
MCP_ANALYTICS_URL=http://localhost:3004
MCP_INTEGRATIONS_URL=http://localhost:3005
```

## 📊 Dashboard

Access the workflow dashboard at `http://localhost:8000/`:

- **Telemetry Console** - Real-time logs showing workflow progress
- **Stats Cards** - Products analyzed, reorder count, suppliers, total value
- **Results Table** - Order recommendations grouped by supplier
- **Progress Bar** - Live progress during workflow execution

## 🔌 API Endpoints

### Workflow Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/workflows/optimize-inventory` | Run full optimization workflow |
| `GET` | `/api/workflows/optimize-inventory/stream` | SSE streaming version with telemetry |
| `GET` | `/api/workflows/analyze-product/{asin}` | Analyze single product |

### Forecasting Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/forecast/{asin}` | Get demand forecast for product |
| `GET` | `/api/forecast/model/info` | Get model metadata |

### Inventory & Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/products` | List all products |
| `GET` | `/products/{asin}` | Get product details |
| `GET` | `/inventory/low-stock` | Get products needing reorder |
| `GET` | `/orders` | List purchase orders |
| `POST` | `/prices/sync-from-amazon` | Sync prices from Amazon API |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check with agent status |
| `GET` | `/api/tools` | List available MCP tools |

## 🤖 Demand Forecasting Model

### Training (Google Colab)

1. Upload `notebooks/demand_forecasting_training.py` to Google Colab
2. Set `DATABASE_URL` environment variable (use Colab Secrets)
3. Run all cells
4. Download `demand_forecaster.pkl`
5. Save to `agents/demand_forecasting/models/demand_forecaster.pkl`

### Model Details

- **Algorithm**: Hybrid XGBoost + Statistical fallback
- **Features**: Lag features, rolling means, temporal features
- **Output**: Predicted demand with confidence intervals
- **Products**: 8 ML models, 229 statistical fallback

## 📁 Project Structure

```
realtime_price_agent/
├── main.py                         # FastAPI application
├── scripts/
│   └── setup.sh                    # One-command setup script
├── static/
│   └── index.html                  # Dashboard UI
├── agents/
│   ├── orchestrator/               # Workflow orchestration
│   ├── demand_forecasting/         # Forecasting agent + ML model
│   │   ├── agent.py                # Agent definition
│   │   ├── model_service.py        # Model loading & inference
│   │   └── models/
│   │       └── demand_forecaster.pkl  # Trained model
│   ├── price_monitoring/           # Price analysis agent
│   └── automated_ordering/         # Order generation agent
├── services/
│   ├── workflow_service.py         # Optimization workflow
│   ├── inventory_service.py        # Stock management
│   ├── order_service.py            # Order CRUD
│   └── supplier_service.py         # Supplier management
├── database/
│   ├── config.py                   # PostgreSQL connection
│   └── models.py                   # SQLAlchemy models
├── notebooks/
│   └── demand_forecasting_training.py  # Colab training notebook
└── docs/
    ├── implementation_docs/
    │   └── implementation_plan.md  # Detailed implementation guide
    └── mcp_deploy.md               # MCP server deployment guide
```

## 🐳 Docker Deployment

```bash
# Build
docker build -t supply-chain-agents .

# Run
docker run -p 8000:8000 --env-file .env supply-chain-agents
```

## ☁️ Azure Deployment (azd)

See [Implementation Plan](docs/implementation_docs/implementation_plan.md) for detailed Azure deployment instructions including:

- Azure Container Apps setup
- MCP server deployment
- Managed identity configuration
- Application Insights integration

```bash
# Initialize and deploy
azd init
azd up
```

## 📚 References

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Azure MCP Server](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server)
- [Azure AI Travel Agents (Reference)](https://github.com/Azure-Samples/azure-ai-travel-agents)

## 📄 License

MIT License
