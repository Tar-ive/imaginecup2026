#!/usr/bin/env python3
"""
Analyze eCommerce API data to generate statistical distributions for realistic order generation.
Fetches products from multiple categories and computes distributions for:
- Price tiers and quantities
- Rating distributions
- Review count patterns
- Category popularity
- Temporal patterns
"""

import pandas as pd
import requests
import numpy as np
from datetime import datetime
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# API configuration
API_BASE = (
    "https://amazon-api-app.purplepebble-8d2a2163.eastus.azurecontainerapps.io/products"
)
CATEGORIES = ["laptop", "headphones", "electronics", "office", "home", "computer"]
RESULTS_PER_CATEGORY = 50  # Limit per category to avoid API overload


def fetch_category_data(
    category: str, limit: int = RESULTS_PER_CATEGORY
) -> pd.DataFrame:
    """Fetch product data for a specific category"""
    url = f"{API_BASE}?query={category}&limit={limit}"
    print(f"📡 Fetching {limit} products for category: {category}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data:
            print(f"  ⚠️  No data returned for {category}")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["query_category"] = category
        print(f"  ✅ Retrieved {len(df)} products")
        return df

    except Exception as e:
        print(f"  ❌ Error fetching {category}: {e}")
        return pd.DataFrame()


def clean_and_prepare_data(products_df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare the raw product data"""
    print("🧹 Cleaning and preparing data...")

    # Ensure price_cleaned exists and is numeric
    if "price_cleaned" not in products_df.columns:
        if "final_price" in products_df.columns:
            products_df["price_cleaned"] = (
                products_df["final_price"]
                .astype(str)
                .str.extract(r"(\d+\.?\d*)")
                .astype(float)
            )
        else:
            products_df["price_cleaned"] = 29.99  # Default price

    # Fill missing prices with median
    median_price = products_df["price_cleaned"].median()
    products_df["price_cleaned"] = products_df["price_cleaned"].fillna(median_price)

    # Ensure rating is numeric
    products_df["rating"] = pd.to_numeric(
        products_df["rating"], errors="coerce"
    ).fillna(4.0)

    # Ensure reviews_count is numeric
    products_df["reviews_count"] = pd.to_numeric(
        products_df["reviews_count"], errors="coerce"
    ).fillna(10)

    # Parse timestamps if available
    if "timestamp" in products_df.columns:
        products_df["timestamp"] = pd.to_datetime(
            products_df["timestamp"], errors="coerce"
        )
        products_df["month"] = products_df["timestamp"].dt.month
        products_df["weekday"] = products_df["timestamp"].dt.weekday

    # Clean categories - take first category if it's a list
    if "categories" in products_df.columns:
        products_df["primary_category"] = products_df["categories"].apply(
            lambda x: x[0] if isinstance(x, list) and x else "Electronics"
        )

    print(
        f"  📊 Prepared {len(products_df)} products with median price ${median_price:.2f}"
    )
    return products_df


def compute_price_distributions(products_df: pd.DataFrame) -> dict:
    """Compute price tier distributions and statistics"""
    print("💰 Analyzing price distributions...")

    prices = products_df["price_cleaned"]
    quartiles = prices.quantile([0.25, 0.5, 0.75])

    # Define price tiers based on quartiles
    price_tiers = {
        "low": {"min": 0, "max": quartiles[0.25], "weight": 0.35},
        "medium": {"min": quartiles[0.25], "max": quartiles[0.5], "weight": 0.45},
        "high": {"min": quartiles[0.5], "max": quartiles[0.75], "weight": 0.15},
        "premium": {"min": quartiles[0.75], "max": prices.max(), "weight": 0.05},
    }

    # Compute order quantity patterns for each tier
    for tier, config in price_tiers.items():
        tier_products = products_df[
            (products_df["price_cleaned"] >= config["min"])
            & (products_df["price_cleaned"] <= config["max"])
        ]

        if len(tier_products) > 0:
            # Estimate quantities based on price (lower price = higher quantity)
            base_quantity = max(1, 10 - (config["max"] / 10))  # Rough heuristic
            config.update(
                {
                    "avg_quantity": base_quantity,
                    "std_quantity": base_quantity * 0.6,
                    "max_quantity": min(50, base_quantity * 3),
                    "sample_size": len(tier_products),
                }
            )

    return price_tiers


def compute_rating_distributions(products_df: pd.DataFrame) -> dict:
    """Compute rating distribution patterns"""
    print("⭐ Analyzing rating distributions...")

    ratings = products_df["rating"]
    rating_counts = ratings.value_counts().sort_index()

    # Create popularity tiers based on ratings
    rating_tiers = {
        "excellent": {
            "min": 4.5,
            "max": 5.0,
            "weight": len(ratings[(ratings >= 4.5) & (ratings <= 5.0)]) / len(ratings),
        },
        "good": {
            "min": 4.0,
            "max": 4.4,
            "weight": len(ratings[(ratings >= 4.0) & (ratings < 4.5)]) / len(ratings),
        },
        "average": {
            "min": 3.5,
            "max": 3.9,
            "weight": len(ratings[(ratings >= 3.5) & (ratings < 4.0)]) / len(ratings),
        },
        "poor": {
            "min": 1.0,
            "max": 3.4,
            "weight": len(ratings[(ratings >= 1.0) & (ratings < 3.5)]) / len(ratings),
        },
    }

    return rating_tiers


def compute_review_distributions(products_df: pd.DataFrame) -> dict:
    """Compute review count distribution patterns (typically log-normal)"""
    print("📝 Analyzing review count distributions...")

    reviews = products_df["reviews_count"]
    log_reviews = np.log1p(reviews)  # Log transform for normal distribution

    # Create popularity tiers based on review counts
    review_percentiles = reviews.quantile([0.5, 0.8, 0.95])

    review_tiers = {
        "niche": {
            "max": review_percentiles[0.5],
            "weight": 0.60,
            "order_multiplier": 1.0,
        },
        "popular": {
            "min": review_percentiles[0.5],
            "max": review_percentiles[0.8],
            "weight": 0.30,
            "order_multiplier": 1.5,
        },
        "trending": {
            "min": review_percentiles[0.8],
            "max": review_percentiles[0.95],
            "weight": 0.09,
            "order_multiplier": 2.5,
        },
        "viral": {
            "min": review_percentiles[0.95],
            "weight": 0.01,
            "order_multiplier": 4.0,
        },
    }

    return review_tiers


def compute_category_distributions(products_df: pd.DataFrame) -> dict:
    """Compute category popularity patterns"""
    print("📂 Analyzing category distributions...")

    category_counts = products_df["query_category"].value_counts()
    category_weights = (category_counts / len(products_df)).to_dict()

    # Add seasonal patterns (simplified)
    category_seasonality = {
        "electronics": {"q1": 1.0, "q2": 1.1, "q3": 0.9, "q4": 1.3},
        "headphones": {"q1": 0.8, "q2": 1.2, "q3": 1.1, "q4": 1.4},
        "office": {"q1": 1.1, "q2": 0.9, "q3": 1.0, "q4": 1.2},
        "home": {"q1": 1.0, "q2": 1.1, "q3": 1.2, "q4": 1.0},
        "computer": {"q1": 0.9, "q2": 1.0, "q3": 1.1, "q4": 1.3},
    }

    return {"weights": category_weights, "seasonality": category_seasonality}


def compute_temporal_patterns(products_df: pd.DataFrame) -> dict:
    """Compute temporal ordering patterns"""
    print("⏰ Analyzing temporal patterns...")

    temporal_patterns = {}

    if "month" in products_df.columns:
        monthly = products_df.groupby("month").size()
        if len(monthly) > 0:
            monthly_normalized = monthly / monthly.mean()
            temporal_patterns["monthly"] = monthly_normalized.to_dict()

    if "weekday" in products_df.columns:
        weekly = products_df.groupby("weekday").size()
        if len(weekly) > 0:
            weekly_normalized = weekly / weekly.mean()
            temporal_patterns["weekly"] = weekly_normalized.to_dict()

    # Default patterns if no timestamp data
    if not temporal_patterns.get("monthly"):
        temporal_patterns["monthly"] = {
            1: 0.9,
            2: 0.8,
            3: 1.0,
            4: 1.1,
            5: 0.9,
            6: 0.7,
            7: 0.6,
            8: 0.7,
            9: 1.0,
            10: 1.2,
            11: 1.4,
            12: 1.3,
        }

    if not temporal_patterns.get("weekly"):
        temporal_patterns["weekly"] = {
            0: 0.8,
            1: 1.0,
            2: 1.1,
            3: 1.2,
            4: 1.1,
            5: 0.6,
            6: 0.4,
        }

    return temporal_patterns


def generate_order_parameters(stats: dict) -> dict:
    """Generate order generation parameters from computed statistics"""
    print("🔧 Generating order parameters...")

    order_params = {
        "price_tiers": stats["price_tiers"],
        "rating_tiers": stats["rating_tiers"],
        "review_tiers": stats["review_tiers"],
        "category_weights": stats["category_weights"]["weights"],
        "seasonality": stats["category_weights"]["seasonality"],
        "temporal_patterns": stats["temporal_patterns"],
        "generated_at": datetime.now().isoformat(),
        "total_products_analyzed": stats.get("total_products", 0),
    }

    return order_params


def save_parameters_to_file(
    params: dict, filename: str = "order_generation_params.json"
):
    """Save the computed parameters to a JSON file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath, "w") as f:
        json.dump(params, f, indent=2, default=str)

    print(f"💾 Saved parameters to {filepath}")


def main():
    print("🎯 Starting eCommerce data analysis for order generation")
    print(
        f"📊 Will analyze {len(CATEGORIES)} categories with {RESULTS_PER_CATEGORY} products each"
    )
    print()

    # Fetch data from all categories
    all_products = []
    for category in CATEGORIES:
        df = fetch_category_data(category)
        if not df.empty:
            all_products.append(df)

    if not all_products:
        print("❌ No data retrieved from API. Cannot proceed with analysis.")
        sys.exit(1)

    # Combine all data
    products_df = pd.concat(all_products, ignore_index=True)
    print(f"\n📈 Total products collected: {len(products_df)}")

    # Clean and prepare data
    products_df = clean_and_prepare_data(products_df)

    # Compute all statistical distributions
    stats = {
        "price_tiers": compute_price_distributions(products_df),
        "rating_tiers": compute_rating_distributions(products_df),
        "review_tiers": compute_review_distributions(products_df),
        "category_weights": compute_category_distributions(products_df),
        "temporal_patterns": compute_temporal_patterns(products_df),
        "total_products": len(products_df),
    }

    # Generate order parameters
    order_params = generate_order_parameters(stats)

    # Save to file
    save_parameters_to_file(order_params)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total products analyzed: {len(products_df)}")
    print(
        f"Price range: ${products_df['price_cleaned'].min():.2f} - ${products_df['price_cleaned'].max():.2f}"
    )
    print(f"Median price: ${products_df['price_cleaned'].median():.2f}")
    print(
        f"Rating range: {products_df['rating'].min():.1f} - {products_df['rating'].max():.1f}"
    )
    print(f"Average rating: {products_df['rating'].mean():.2f}")
    print(
        f"Review count range: {products_df['reviews_count'].min()} - {products_df['reviews_count'].max()}"
    )
    print(f"Median reviews: {products_df['reviews_count'].median():.0f}")

    print("\n✅ Analysis complete! Parameters saved to order_generation_params.json")
    print("Next step: Update 03_generate_orders.py to use these statistical parameters")


if __name__ == "__main__":
    main()
