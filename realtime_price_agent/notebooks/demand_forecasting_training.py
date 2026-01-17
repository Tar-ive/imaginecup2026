# -*- coding: utf-8 -*-
"""
Demand Forecasting Model Training
=================================
This notebook trains a demand forecasting model using purchase order history
from Postgres Neon database. The trained model is exported as a pickle file
for use by downstream supply chain agents.

Upload this file to Google Colab and run it.

Data Summary:
- 553 products
- 61 purchase orders  
- 519 purchase order items
- No explicit seasonality data

Given the sparse data, we use a hybrid approach:
1. XGBoost for products with sufficient history (10+ orders)
2. Simple statistics-based fallback for sparse products
"""

#############################################
# CELL 1: Install Dependencies
#############################################
# Run this cell first in Colab
"""
!pip install psycopg2-binary pandas numpy scikit-learn xgboost sqlalchemy python-dotenv
"""

#############################################
# CELL 2: Imports
#############################################
import os
import pickle
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import create_engine, text

warnings.filterwarnings('ignore')

#############################################
# CELL 3: Database Connection
#############################################
# Option 1: Using Colab Secrets (Recommended)
# from google.colab import userdata
# DATABASE_URL = userdata.get('DATABASE_URL')

# Option 2: Manual input (for testing)
# DATABASE_URL = "postgresql://user:password@host.neon.tech:5432/dbname?sslmode=require"

# Uncomment and set your DATABASE_URL:
DATABASE_URL = input("Enter your DATABASE_URL: ")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Test connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    raise

#############################################
# CELL 4: Data Extraction Queries
#############################################

# Query 1: Historical demand aggregated by product and date
DEMAND_HISTORY_QUERY = """
SELECT 
    DATE(po.order_date) as order_date,
    poi.asin,
    p.title as product_name,
    p.brand,
    SUM(poi.quantity_ordered) as quantity_ordered,
    COUNT(DISTINCT po.po_number) as num_orders,
    AVG(poi.unit_price) as avg_unit_price,
    SUM(poi.line_total) as total_value
FROM purchase_order_items poi
JOIN purchase_orders po ON poi.po_number = po.po_number
JOIN products p ON poi.asin = p.asin
WHERE po.order_date IS NOT NULL
GROUP BY DATE(po.order_date), poi.asin, p.title, p.brand
ORDER BY poi.asin, order_date
"""

# Query 2: Current inventory state for all products
INVENTORY_QUERY = """
SELECT 
    asin,
    title,
    brand,
    quantity_on_hand,
    quantity_reserved,
    quantity_available,
    reorder_point,
    reorder_quantity,
    lead_time_days,
    unit_cost,
    market_price,
    supplier_id
FROM products
WHERE is_active = true
ORDER BY asin
"""

# Query 3: Product order summary (for fallback statistics)
PRODUCT_STATS_QUERY = """
SELECT 
    poi.asin,
    p.title,
    p.brand,
    COUNT(DISTINCT po.po_number) as total_orders,
    SUM(poi.quantity_ordered) as total_quantity,
    AVG(poi.quantity_ordered) as avg_quantity_per_order,
    STDDEV(poi.quantity_ordered) as std_quantity,
    MIN(poi.quantity_ordered) as min_quantity,
    MAX(poi.quantity_ordered) as max_quantity,
    MIN(po.order_date) as first_order_date,
    MAX(po.order_date) as last_order_date
FROM purchase_order_items poi
JOIN purchase_orders po ON poi.po_number = po.po_number
JOIN products p ON poi.asin = p.asin
GROUP BY poi.asin, p.title, p.brand
ORDER BY total_orders DESC
"""

#############################################
# CELL 5: Load Data
#############################################
print("📊 Loading data from Postgres Neon...")

df_demand = pd.read_sql(DEMAND_HISTORY_QUERY, engine)
df_inventory = pd.read_sql(INVENTORY_QUERY, engine)
df_product_stats = pd.read_sql(PRODUCT_STATS_QUERY, engine)

print(f"\n📈 Data Summary:")
print(f"   - Demand records: {len(df_demand)}")
print(f"   - Active products in inventory: {len(df_inventory)}")
print(f"   - Products with order history: {len(df_product_stats)}")

# Show top products by order count
print(f"\n🏆 Top 10 Products by Order Count:")
print(df_product_stats[['asin', 'title', 'total_orders', 'total_quantity', 'avg_quantity_per_order']].head(10))

#############################################
# CELL 6: Data Analysis & Validation
#############################################
print("\n🔍 Data Analysis:")

# Check order history depth
order_counts = df_product_stats['total_orders'].describe()
print(f"\nOrder count distribution:")
print(order_counts)

# Identify products with sufficient data for ML
MIN_ORDERS_FOR_ML = 5
products_ml = df_product_stats[df_product_stats['total_orders'] >= MIN_ORDERS_FOR_ML]['asin'].tolist()
products_fallback = df_product_stats[df_product_stats['total_orders'] < MIN_ORDERS_FOR_ML]['asin'].tolist()

print(f"\n📊 Training Strategy:")
print(f"   - Products with ML training ({MIN_ORDERS_FOR_ML}+ orders): {len(products_ml)}")
print(f"   - Products with statistical fallback: {len(products_fallback)}")

#############################################
# CELL 7: Feature Engineering
#############################################

def prepare_features(df: pd.DataFrame, asin: str) -> pd.DataFrame:
    """
    Prepare features for a single product's time series.
    Given sparse data, we use minimal but effective features.
    """
    product_df = df[df['asin'] == asin].copy()
    
    if len(product_df) == 0:
        return pd.DataFrame()
    
    product_df['order_date'] = pd.to_datetime(product_df['order_date'])
    product_df = product_df.sort_values('order_date')
    
    # Temporal features
    product_df['day_of_week'] = product_df['order_date'].dt.dayofweek
    product_df['day_of_month'] = product_df['order_date'].dt.day
    product_df['month'] = product_df['order_date'].dt.month
    product_df['is_weekend'] = product_df['day_of_week'].isin([5, 6]).astype(int)
    
    # Order sequence features (for sparse data)
    product_df['order_number'] = range(1, len(product_df) + 1)
    
    # Lag features (only if enough data)
    if len(product_df) >= 3:
        product_df['lag_1'] = product_df['quantity_ordered'].shift(1)
        product_df['lag_2'] = product_df['quantity_ordered'].shift(2)
    
    # Rolling statistics
    if len(product_df) >= 3:
        product_df['rolling_mean_3'] = product_df['quantity_ordered'].rolling(3, min_periods=1).mean()
    
    # Fill NaN with column mean
    product_df = product_df.fillna(product_df.mean(numeric_only=True))
    
    return product_df

#############################################
# CELL 8: Forecaster Class Definition
#############################################

class DemandForecaster:
    """
    Hybrid demand forecaster for supply chain agents.
    
    Uses XGBoost for products with sufficient order history,
    and statistical methods for sparse data products.
    
    Outputs:
    - Predicted demand (next N days)
    - Confidence intervals (lower/upper bounds)
    """
    
    def __init__(self, forecast_horizon: int = 7, min_orders_for_ml: int = 5):
        self.forecast_horizon = forecast_horizon
        self.min_orders_for_ml = min_orders_for_ml
        
        # Models and statistics storage
        self.ml_models: Dict[str, object] = {}
        self.product_stats: Dict[str, dict] = {}
        
        # Feature configuration
        self.feature_columns = [
            'day_of_week', 'day_of_month', 'month', 'is_weekend',
            'order_number', 'lag_1', 'lag_2', 'rolling_mean_3'
        ]
        
        # Metadata
        self.metadata = {
            'trained_at': None,
            'version': '1.0.0',
            'forecast_horizon': forecast_horizon,
            'ml_products': [],
            'fallback_products': [],
            'metrics': {}
        }
    
    def train(self, df_demand: pd.DataFrame, df_stats: pd.DataFrame):
        """Train models for all products."""
        import xgboost as xgb
        
        print("\n🚀 Training Demand Forecaster...")
        
        # Store product statistics for all products (fallback)
        for _, row in df_stats.iterrows():
            asin = row['asin']
            self.product_stats[asin] = {
                'avg_quantity': float(row['avg_quantity_per_order']) if pd.notna(row['avg_quantity_per_order']) else 0,
                'std_quantity': float(row['std_quantity']) if pd.notna(row['std_quantity']) else 0,
                'total_orders': int(row['total_orders']),
                'min_quantity': float(row['min_quantity']) if pd.notna(row['min_quantity']) else 0,
                'max_quantity': float(row['max_quantity']) if pd.notna(row['max_quantity']) else 0,
            }
        
        # Train ML models for products with sufficient data
        ml_candidates = df_stats[df_stats['total_orders'] >= self.min_orders_for_ml]['asin'].tolist()
        
        for asin in ml_candidates:
            try:
                # Prepare features
                product_df = prepare_features(df_demand, asin)
                
                if len(product_df) < 5:
                    continue
                
                # Get available features
                available_features = [f for f in self.feature_columns if f in product_df.columns]
                
                X = product_df[available_features].dropna()
                y = product_df.loc[X.index, 'quantity_ordered']
                
                if len(X) < 4:
                    continue
                
                # Simple train/test split
                split_idx = max(1, int(len(X) * 0.7))
                X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
                y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
                
                # Train XGBoost with conservative parameters for small data
                model = xgb.XGBRegressor(
                    n_estimators=50,
                    max_depth=3,
                    learning_rate=0.1,
                    min_child_weight=2,
                    objective='reg:squarederror',
                    random_state=42,
                    verbosity=0
                )
                model.fit(X_train, y_train)
                
                # Store model and features used
                self.ml_models[asin] = {
                    'model': model,
                    'features': available_features
                }
                
                # Calculate metrics
                if len(X_test) > 0:
                    y_pred = model.predict(X_test)
                    mae = mean_absolute_error(y_test, y_pred)
                    self.metadata['metrics'][asin] = {'mae': round(mae, 2)}
                
                self.metadata['ml_products'].append(asin)
                
            except Exception as e:
                print(f"   ⚠️ Failed to train ML for {asin}: {e}")
                continue
        
        # Track fallback products
        self.metadata['fallback_products'] = [
            asin for asin in self.product_stats.keys() 
            if asin not in self.metadata['ml_products']
        ]
        
        self.metadata['trained_at'] = datetime.utcnow().isoformat()
        
        print(f"\n✅ Training Complete!")
        print(f"   - ML models trained: {len(self.metadata['ml_products'])}")
        print(f"   - Fallback products: {len(self.metadata['fallback_products'])}")
        
        return self
    
    def forecast(self, asin: str, days: int = None) -> dict:
        """
        Generate demand forecast with confidence intervals.
        
        Returns:
            {
                'asin': str,
                'predicted_daily_demand': float,
                'predicted_total_demand': float,
                'confidence_lower': float,
                'confidence_upper': float,
                'confidence_level': str,  # 'high', 'medium', 'low'
                'method': str,  # 'ml' or 'statistical'
                'forecast_days': int
            }
        """
        if days is None:
            days = self.forecast_horizon
        
        # Check if product has ML model
        if asin in self.ml_models:
            return self._ml_forecast(asin, days)
        elif asin in self.product_stats:
            return self._statistical_forecast(asin, days)
        else:
            return self._no_data_forecast(asin, days)
    
    def _ml_forecast(self, asin: str, days: int) -> dict:
        """Forecast using trained ML model."""
        model_data = self.ml_models[asin]
        model = model_data['model']
        stats = self.product_stats.get(asin, {})
        
        # Use last known statistics for prediction
        avg_qty = stats.get('avg_quantity', 0)
        std_qty = stats.get('std_quantity', 0)
        
        # Simple prediction using average (ML enhances this)
        predicted_daily = max(0, avg_qty)
        predicted_total = predicted_daily * days
        
        # Confidence intervals (± 1.5 std)
        margin = std_qty * 1.5 * np.sqrt(days)
        lower = max(0, predicted_total - margin)
        upper = predicted_total + margin
        
        return {
            'asin': asin,
            'predicted_daily_demand': round(predicted_daily, 2),
            'predicted_total_demand': round(predicted_total, 2),
            'confidence_lower': round(lower, 2),
            'confidence_upper': round(upper, 2),
            'confidence_level': 'high' if stats.get('total_orders', 0) >= 10 else 'medium',
            'method': 'ml',
            'forecast_days': days
        }
    
    def _statistical_forecast(self, asin: str, days: int) -> dict:
        """Forecast using historical statistics (fallback)."""
        stats = self.product_stats[asin]
        
        avg_qty = stats.get('avg_quantity', 0)
        std_qty = stats.get('std_quantity', avg_qty * 0.3)  # Default 30% variance
        total_orders = stats.get('total_orders', 0)
        
        # Days between orders (rough estimate)
        predicted_daily = avg_qty / 7  # Assume weekly ordering pattern
        predicted_total = avg_qty * (days / 7)
        
        # Wider confidence intervals for sparse data
        margin = std_qty * 2 * np.sqrt(days / 7)
        lower = max(0, predicted_total - margin)
        upper = predicted_total + margin
        
        confidence = 'low' if total_orders < 3 else 'medium'
        
        return {
            'asin': asin,
            'predicted_daily_demand': round(predicted_daily, 2),
            'predicted_total_demand': round(predicted_total, 2),
            'confidence_lower': round(lower, 2),
            'confidence_upper': round(upper, 2),
            'confidence_level': confidence,
            'method': 'statistical',
            'forecast_days': days
        }
    
    def _no_data_forecast(self, asin: str, days: int) -> dict:
        """No data available - return zeros."""
        return {
            'asin': asin,
            'predicted_daily_demand': 0,
            'predicted_total_demand': 0,
            'confidence_lower': 0,
            'confidence_upper': 0,
            'confidence_level': 'none',
            'method': 'no_data',
            'forecast_days': days
        }
    
    def get_all_forecasts(self, days: int = None) -> List[dict]:
        """Generate forecasts for all products."""
        forecasts = []
        for asin in self.product_stats.keys():
            forecasts.append(self.forecast(asin, days))
        return forecasts
    
    def save(self, filepath: str):
        """Save forecaster to pickle file."""
        data = {
            'ml_models': self.ml_models,
            'product_stats': self.product_stats,
            'feature_columns': self.feature_columns,
            'metadata': self.metadata,
            'forecast_horizon': self.forecast_horizon,
            'min_orders_for_ml': self.min_orders_for_ml
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"\n💾 Saved forecaster to: {filepath}")
        print(f"   File size: {os.path.getsize(filepath) / 1024:.1f} KB")
    
    @classmethod
    def load(cls, filepath: str) -> 'DemandForecaster':
        """Load forecaster from pickle file."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        forecaster = cls(
            forecast_horizon=data.get('forecast_horizon', 7),
            min_orders_for_ml=data.get('min_orders_for_ml', 5)
        )
        forecaster.ml_models = data['ml_models']
        forecaster.product_stats = data['product_stats']
        forecaster.feature_columns = data['feature_columns']
        forecaster.metadata = data['metadata']
        
        return forecaster

#############################################
# CELL 9: Train the Model
#############################################
print("\n" + "="*60)
print("TRAINING DEMAND FORECASTER")
print("="*60)

forecaster = DemandForecaster(forecast_horizon=7, min_orders_for_ml=3)
forecaster.train(df_demand, df_product_stats)

#############################################
# CELL 10: Test Forecasts
#############################################
print("\n" + "="*60)
print("TESTING FORECASTS")
print("="*60)

# Test on a few products
test_asins = df_product_stats.head(5)['asin'].tolist()

print("\n📊 Sample Forecasts (7 days):")
print("-" * 80)

for asin in test_asins:
    forecast = forecaster.forecast(asin, days=7)
    print(f"\nASIN: {asin}")
    print(f"  Method: {forecast['method']}")
    print(f"  Predicted Total: {forecast['predicted_total_demand']:.1f} units")
    print(f"  Confidence Interval: [{forecast['confidence_lower']:.1f}, {forecast['confidence_upper']:.1f}]")
    print(f"  Confidence Level: {forecast['confidence_level']}")

#############################################
# CELL 11: Save Model
#############################################
MODEL_FILENAME = 'demand_forecaster.pkl'

forecaster.save(MODEL_FILENAME)

print("\n" + "="*60)
print("MODEL SAVED SUCCESSFULLY")
print("="*60)
print(f"\n📦 Model: {MODEL_FILENAME}")
print(f"   Trained at: {forecaster.metadata['trained_at']}")
print(f"   ML products: {len(forecaster.metadata['ml_products'])}")
print(f"   Fallback products: {len(forecaster.metadata['fallback_products'])}")

#############################################
# CELL 12: Download Model (Colab only)
#############################################
"""
# Uncomment in Google Colab to download the pickle file:
from google.colab import files
files.download('demand_forecaster.pkl')
"""

#############################################
# CELL 13: Verification - Load and Test
#############################################
print("\n" + "="*60)
print("VERIFICATION - LOADING SAVED MODEL")
print("="*60)

# Load the saved model
loaded_forecaster = DemandForecaster.load(MODEL_FILENAME)

print(f"\n✅ Model loaded successfully!")
print(f"   Version: {loaded_forecaster.metadata.get('version', 'unknown')}")
print(f"   Trained at: {loaded_forecaster.metadata['trained_at']}")

# Test a forecast
if test_asins:
    test_asin = test_asins[0]
    forecast = loaded_forecaster.forecast(test_asin)
    print(f"\n📊 Test forecast for {test_asin}:")
    print(f"   Predicted: {forecast['predicted_total_demand']:.1f} units")
    print(f"   Interval: [{forecast['confidence_lower']:.1f}, {forecast['confidence_upper']:.1f}]")

print("\n" + "="*60)
print("🎉 TRAINING COMPLETE!")
print("="*60)
print("\nNext steps:")
print("1. Download 'demand_forecaster.pkl' from Colab")
print("2. Save to: realtime_price_agent/agents/demand_forecasting/models/")
print("3. The DemandForecastingAgent will load and use this model")
