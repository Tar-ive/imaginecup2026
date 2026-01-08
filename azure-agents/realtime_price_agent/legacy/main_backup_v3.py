from fastapi import FastAPI, Query, HTTPException
from contextlib import asynccontextmanager
import pandas as pd
import requests
from io import StringIO

# Global storage
db = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading CSV data...")
    url = "https://raw.githubusercontent.com/luminati-io/eCommerce-dataset-samples/refs/heads/main/amazon-products.csv"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch CSV data. Status: {response.status_code}")
    
    # Load CSV
    try:
        df = pd.read_csv(StringIO(response.text))
        
        # 1. Normalize headers (lowercase + strip spaces)
        df.columns = df.columns.str.strip().str.lower()
        print(f"Columns found: {list(df.columns)}")

        # 2. Fix Price Column
        # The file uses 'final_price', but we want a clean float for math
        if 'final_price' in df.columns:
            # Remove currency symbols and convert to numbers
            df['price_cleaned'] = df['final_price'].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df['price_cleaned'] = pd.to_numeric(df['price_cleaned'], errors='coerce').fillna(0.0)
        else:
            print("Warning: 'final_price' column not found. Setting price to 0.")
            df['price_cleaned'] = 0.0

        # 3. Handle Missing Values
        # Ensure text columns are strings (not NaNs) to avoid search errors
        if 'brand' in df.columns:
            df['brand'] = df['brand'].fillna('Unknown')
        if 'title' in df.columns:
            df['title'] = df['title'].fillna('Untitled')
            
        db["df"] = df
        print(f"Successfully loaded {len(df)} products.")
        
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        db["df"] = pd.DataFrame() # Empty fallback

    yield
    db.clear()

app = FastAPI(lifespan=lifespan)

@app.get("/products")
def list_products(
    query: str = Query(None), 
    brand: str = Query(None), 
    min_price: float = Query(None),
    max_price: float = Query(None),
    limit: int = 5
):
    df = db.get("df")
    
    if df is None or df.empty:
        return []

    results = df.copy()

    # Brand Filter
    if brand and 'brand' in results.columns:
        results = results[results['brand'].str.contains(brand, case=False, na=False)]

    # Price Filter (using our new clean column)
    if min_price is not None:
        results = results[results['price_cleaned'] >= min_price]
    if max_price is not None:
        results = results[results['price_cleaned'] <= max_price]

    # Keyword Search
    if query and 'title' in results.columns:
        mask = results['title'].str.contains(query, case=False, na=False)
        results = results[mask]
        
    # Limit results
    results = results.head(limit)
    
    # Replace NaN/Infinity before returning JSON (FastAPI doesn't like NaN)
    results = results.fillna("")
    
    return results.to_dict(orient="records")

@app.get("/products/{asin}")
def get_product_details(asin: str):
    df = db.get("df")
    if df is None or 'asin' not in df.columns:
        raise HTTPException(status_code=500, detail="Database not ready")
        
    product = df[df['asin'] == asin]
    if product.empty:
        raise HTTPException(status_code=404, detail="Product not found")
        
    return product.iloc[0].fillna("").to_dict()

    