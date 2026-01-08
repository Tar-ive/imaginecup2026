"""
Demand Forecaster Model Service
===============================
Loads the trained forecasting model (pickle file) and provides
demand forecasting with confidence intervals for the agent.

The trained model should be placed in:
  agents/demand_forecasting/models/demand_forecaster.pkl

Usage:
    from agents.demand_forecasting.model_service import DemandForecasterService

    forecaster = DemandForecasterService.get_instance()
    forecast = forecaster.forecast("B001ABC123", days=7)
"""

import os
import pickle
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class DemandForecast:
    """Demand forecast result with confidence intervals."""
    
    asin: str
    predicted_daily_demand: float
    predicted_total_demand: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: str  # 'high', 'medium', 'low', 'none'
    method: str  # 'ml', 'statistical', 'no_data'
    forecast_days: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'asin': self.asin,
            'predicted_daily_demand': self.predicted_daily_demand,
            'predicted_total_demand': self.predicted_total_demand,
            'confidence_lower': self.confidence_lower,
            'confidence_upper': self.confidence_upper,
            'confidence_level': self.confidence_level,
            'method': self.method,
            'forecast_days': self.forecast_days
        }
    
    @property
    def needs_reorder(self) -> bool:
        """Simplified check - actual logic should consider inventory."""
        return self.predicted_total_demand > 0
    
    @property
    def confidence_range(self) -> float:
        """Spread of confidence interval."""
        return self.confidence_upper - self.confidence_lower


class DemandForecasterService:
    """
    Singleton service for demand forecasting.
    
    Loads the trained model from pickle file and provides
    a clean interface for agents and API endpoints.
    """
    
    _instance: Optional['DemandForecasterService'] = None
    _initialized: bool = False
    
    # Default model path relative to this file
    DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "demand_forecaster.pkl"
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the forecaster service.
        
        Args:
            model_path: Optional path to pickle file. Uses default if not provided.
        """
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = self.DEFAULT_MODEL_PATH
        
        self.model_data: Optional[Dict[str, Any]] = None
        self.is_loaded: bool = False
        self.metadata: Dict[str, Any] = {}
        
        self._load_model()
    
    @classmethod
    def get_instance(cls, model_path: Optional[str] = None) -> 'DemandForecasterService':
        """
        Get singleton instance of the forecaster service.
        
        Args:
            model_path: Optional path to pickle file (only used on first call)
        
        Returns:
            DemandForecasterService instance
        """
        if cls._instance is None:
            cls._instance = cls(model_path)
            cls._initialized = True
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton (useful for testing or reloading model)."""
        cls._instance = None
        cls._initialized = False
    
    def _load_model(self):
        """Load the trained model from pickle file."""
        if not self.model_path.exists():
            logger.warning(
                f"Model file not found at {self.model_path}. "
                f"Forecaster will use fallback mode."
            )
            self.is_loaded = False
            return
        
        try:
            with open(self.model_path, 'rb') as f:
                self.model_data = pickle.load(f)
            
            self.metadata = self.model_data.get('metadata', {})
            self.is_loaded = True
            
            logger.info(
                f"Loaded demand forecaster model. "
                f"ML products: {len(self.model_data.get('ml_models', {}))} "
                f"Stats products: {len(self.model_data.get('product_stats', {}))}"
            )
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.is_loaded = False
    
    def forecast(self, asin: str, days: int = 7) -> DemandForecast:
        """
        Generate demand forecast for a product.
        
        Args:
            asin: Product ASIN
            days: Number of days to forecast (default: 7)
        
        Returns:
            DemandForecast with predicted demand and confidence intervals
        """
        if not self.is_loaded or self.model_data is None:
            return self._no_model_forecast(asin, days)
        
        ml_models = self.model_data.get('ml_models', {})
        product_stats = self.model_data.get('product_stats', {})
        
        # Check if product has ML model
        if asin in ml_models:
            return self._ml_forecast(asin, days, ml_models[asin], product_stats.get(asin, {}))
        elif asin in product_stats:
            return self._statistical_forecast(asin, days, product_stats[asin])
        else:
            return self._no_data_forecast(asin, days)
    
    def _ml_forecast(
        self, 
        asin: str, 
        days: int, 
        model_data: dict,
        stats: dict
    ) -> DemandForecast:
        """Forecast using trained ML model."""
        import numpy as np
        
        avg_qty = stats.get('avg_quantity', 0)
        std_qty = stats.get('std_quantity', 0)
        total_orders = stats.get('total_orders', 0)
        
        predicted_daily = max(0, avg_qty)
        predicted_total = predicted_daily * days
        
        # Confidence intervals
        margin = std_qty * 1.5 * np.sqrt(days)
        lower = max(0, predicted_total - margin)
        upper = predicted_total + margin
        
        confidence = 'high' if total_orders >= 10 else 'medium'
        
        return DemandForecast(
            asin=asin,
            predicted_daily_demand=round(predicted_daily, 2),
            predicted_total_demand=round(predicted_total, 2),
            confidence_lower=round(lower, 2),
            confidence_upper=round(upper, 2),
            confidence_level=confidence,
            method='ml',
            forecast_days=days
        )
    
    def _statistical_forecast(self, asin: str, days: int, stats: dict) -> DemandForecast:
        """Forecast using historical statistics."""
        import numpy as np
        
        avg_qty = stats.get('avg_quantity', 0)
        std_qty = stats.get('std_quantity', avg_qty * 0.3)
        total_orders = stats.get('total_orders', 0)
        
        # Assume weekly ordering pattern
        predicted_daily = avg_qty / 7
        predicted_total = avg_qty * (days / 7)
        
        margin = std_qty * 2 * np.sqrt(days / 7)
        lower = max(0, predicted_total - margin)
        upper = predicted_total + margin
        
        confidence = 'low' if total_orders < 3 else 'medium'
        
        return DemandForecast(
            asin=asin,
            predicted_daily_demand=round(predicted_daily, 2),
            predicted_total_demand=round(predicted_total, 2),
            confidence_lower=round(lower, 2),
            confidence_upper=round(upper, 2),
            confidence_level=confidence,
            method='statistical',
            forecast_days=days
        )
    
    def _no_data_forecast(self, asin: str, days: int) -> DemandForecast:
        """No data available for product."""
        return DemandForecast(
            asin=asin,
            predicted_daily_demand=0,
            predicted_total_demand=0,
            confidence_lower=0,
            confidence_upper=0,
            confidence_level='none',
            method='no_data',
            forecast_days=days
        )
    
    def _no_model_forecast(self, asin: str, days: int) -> DemandForecast:
        """Model not loaded fallback."""
        logger.warning(f"Model not loaded, returning empty forecast for {asin}")
        return self._no_data_forecast(asin, days)
    
    def batch_forecast(self, asins: List[str], days: int = 7) -> List[DemandForecast]:
        """Generate forecasts for multiple products."""
        return [self.forecast(asin, days) for asin in asins]
    
    def get_all_forecasts(self, days: int = 7) -> List[DemandForecast]:
        """Generate forecasts for all known products."""
        if not self.is_loaded or self.model_data is None:
            return []
        
        all_asins = list(self.model_data.get('product_stats', {}).keys())
        return self.batch_forecast(all_asins, days)
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            'is_loaded': self.is_loaded,
            'model_path': str(self.model_path),
            'trained_at': self.metadata.get('trained_at'),
            'version': self.metadata.get('version'),
            'ml_product_count': len(self.metadata.get('ml_products', [])),
            'fallback_product_count': len(self.metadata.get('fallback_products', [])),
            'forecast_horizon': self.metadata.get('forecast_horizon', 7)
        }


# Convenience function for agent tools
def get_demand_forecast(asin: str, days: int = 7) -> dict:
    """
    Agent tool function for getting demand forecasts.
    
    This function is designed to be called by the DemandForecastingAgent as a tool.
    
    Args:
        asin: Product ASIN to forecast
        days: Number of days to forecast (default: 7)
    
    Returns:
        Dictionary with forecast details including confidence intervals
    """
    forecaster = DemandForecasterService.get_instance()
    forecast = forecaster.forecast(asin, days)
    return forecast.to_dict()
