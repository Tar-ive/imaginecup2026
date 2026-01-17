# Demand Forecasting Models

This directory contains ML models for demand forecasting.

## Model Files

The trained model (`demand_forecaster.pkl`) is **not included in git** due to its size.

### Option 1: Train the Model Yourself

1. Open `notebooks/demand_forecasting_training.py` in Google Colab
2. Set your `DATABASE_URL` environment variable (use Colab Secrets)
3. Run all cells to train the model
4. Download the generated `demand_forecaster.pkl`
5. Place it in this directory: `agents/demand_forecasting/models/demand_forecaster.pkl`

### Option 2: Download Pre-trained Model

If a pre-trained model is available:
- Download from your cloud storage (Azure Blob Storage, S3, etc.)
- Or contact the repository maintainer

### Option 3: Deploy Without Model

The API will work without the model file, but forecasting features will return errors. All other endpoints (inventory, suppliers, orders) will function normally.

## Model Details

- **Algorithm**: Hybrid XGBoost + Statistical fallback
- **Format**: Pickle (.pkl)
- **Size**: ~316 KB
- **Training Data**: Historical order/demand data from PostgreSQL database
- **Features**: Lag features, rolling means, temporal features
- **Products Covered**:
  - 8 products with ML models
  - 229 products with statistical fallback

## Security Note

Model files are excluded from version control via `.gitignore` to keep repository size manageable and avoid potential data leakage from embedded training patterns.
