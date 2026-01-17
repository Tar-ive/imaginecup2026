"""
Price service for CSV integration and price synchronization.
"""
from typing import Optional, Dict
import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import Product


class PriceService:
    """Service for managing price data from external CSV"""

    def __init__(self, db: Session, csv_url: str):
        self.db = db
        self.csv_url = csv_url
        self.df: Optional[pd.DataFrame] = None
        self.last_loaded: Optional[datetime] = None

    def load_csv_data(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Load CSV data with caching.

        Args:
            force_reload: Force reload even if recently loaded

        Returns:
            DataFrame with product data
        """
        # Check if we need to reload (if not loaded or older than 1 hour)
        if force_reload or self.df is None or self.last_loaded is None or \
           datetime.now() - self.last_loaded > timedelta(hours=1):

            print(f"Loading CSV from {self.csv_url}...")
            response = requests.get(self.csv_url)
            response.raise_for_status()

            # Parse CSV
            df = pd.read_csv(StringIO(response.text))

            # Normalize columns
            df.columns = df.columns.str.strip().str.lower()

            # Clean price column
            if 'final_price' in df.columns:
                df['price_cleaned'] = df['final_price'].astype(str).str.replace(r'[^\d.]', '', regex=True)
                df['price_cleaned'] = pd.to_numeric(df['price_cleaned'], errors='coerce').fillna(0.0)
            else:
                df['price_cleaned'] = 0.0

            # Fill missing values
            df['brand'] = df['brand'].fillna('Unknown')
            df['title'] = df['title'].fillna('Untitled')

            self.df = df
            self.last_loaded = datetime.now()

            print(f"✅ Loaded {len(df)} products from CSV")

        return self.df

    def get_csv_price(self, asin: str) -> Optional[float]:
        """
        Get current market price for a product from CSV.

        Args:
            asin: Product ASIN

        Returns:
            Price as float or None if not found
        """
        if self.df is None:
            self.load_csv_data()

        if 'asin' not in self.df.columns:
            return None

        matches = self.df[self.df['asin'] == asin]

        if matches.empty:
            return None

        return float(matches.iloc[0]['price_cleaned'])

    def sync_prices_to_database(self) -> Dict:
        """
        Synchronize prices from CSV to database.

        Updates market_price and price_last_updated for all products.

        Returns:
            Dict with sync statistics
        """
        print("🔄 Syncing prices from CSV to database...")

        # Load fresh CSV data
        self.load_csv_data(force_reload=True)

        if self.df is None or 'asin' not in self.df.columns:
            return {
                'error': 'CSV data not available or missing ASIN column',
                'updated': 0
            }

        # Get all products from database
        products = self.db.query(Product).all()

        updated_count = 0
        price_changes = []

        for product in products:
            # Find matching product in CSV
            matches = self.df[self.df['asin'] == product.asin]

            if not matches.empty:
                new_price = float(matches.iloc[0]['price_cleaned'])

                # Check if price changed
                if product.market_price != new_price:
                    old_price = product.market_price

                    # Update price
                    product.market_price = new_price
                    product.price_last_updated = datetime.utcnow()

                    updated_count += 1

                    if old_price and new_price > 0:
                        variance = ((new_price - old_price) / old_price) * 100
                        price_changes.append({
                            'asin': product.asin,
                            'title': product.title[:50],
                            'old_price': float(old_price),
                            'new_price': new_price,
                            'variance_pct': round(variance, 2)
                        })

        if updated_count > 0:
            self.db.commit()

        print(f"✅ Updated {updated_count} prices")

        return {
            'total_products': len(products),
            'updated': updated_count,
            'price_changes': price_changes[:10],  # Top 10 changes
            'sync_timestamp': datetime.utcnow().isoformat()
        }

    def get_price_comparison(self, asin: str) -> Optional[Dict]:
        """
        Compare database cost vs CSV market price.

        Args:
            asin: Product ASIN

        Returns:
            Dict with price comparison or None if not found
        """
        product = self.db.query(Product).filter(Product.asin == asin).first()

        if not product:
            return None

        csv_price = self.get_csv_price(asin)

        comparison = {
            'asin': product.asin,
            'title': product.title,
            'unit_cost': float(product.unit_cost) if product.unit_cost else None,
            'last_purchase_price': float(product.last_purchase_price) if product.last_purchase_price else None,
            'market_price_db': float(product.market_price) if product.market_price else None,
            'market_price_csv': csv_price,
            'price_last_updated': product.price_last_updated.isoformat() if product.price_last_updated else None
        }

        # Calculate margins and variances
        if product.unit_cost and csv_price and csv_price > 0:
            comparison['margin_pct'] = round(((csv_price - product.unit_cost) / csv_price) * 100, 2)

        if product.market_price and csv_price:
            comparison['price_drift'] = round(csv_price - product.market_price, 2)
            if product.market_price > 0:
                comparison['price_drift_pct'] = round((comparison['price_drift'] / product.market_price) * 100, 2)

        return comparison

    def get_csv_products_df(self) -> pd.DataFrame:
        """Get the full CSV dataframe (for fuzzy matching)"""
        if self.df is None:
            self.load_csv_data()

        return self.df
