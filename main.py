import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
import random

app = FastAPI(title="Energy Insights API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

# Simple in-app dataset to power search (no persistence required for market data lookups)
OIL_BENCHMARKS = [
    {
        "id": "brent",
        "name": "Brent Crude",
        "region": "North Sea",
        "unit": "USD/bbl",
    },
    {
        "id": "wti",
        "name": "WTI Crude",
        "region": "United States",
        "unit": "USD/bbl",
    },
    {
        "id": "opec",
        "name": "OPEC Basket",
        "region": "OPEC Members",
        "unit": "USD/bbl",
    },
    {
        "id": "urals",
        "name": "Urals",
        "region": "Russia",
        "unit": "USD/bbl",
    },
    {
        "id": "dubai",
        "name": "Dubai/Oman",
        "region": "Middle East",
        "unit": "USD/bbl",
    },
]


def synth_price(seed: str) -> dict:
    # Generate a pseudo-realistic price snapshot using a stable seed
    rnd = random.Random(seed)
    base = {
        "brent": 84.2,
        "wti": 80.1,
        "opec": 82.7,
        "urals": 71.9,
        "dubai": 78.3,
    }
    symbol = seed
    base_price = base.get(symbol, 79.0)
    # Add small intraday noise
    noise = rnd.uniform(-1.2, 1.2)
    price = round(base_price + noise, 2)
    change = round(rnd.uniform(-2.0, 2.0), 2)
    percent = round((change / max(price - change, 1e-6)) * 100, 2)
    now = datetime.utcnow()
    updated_at = now - timedelta(minutes=rnd.randint(1, 45))
    return {
        "symbol": symbol.upper(),
        "price": price,
        "change": change,
        "percent_change": percent,
        "currency": "USD",
        "unit": "bbl",
        "updated_at": updated_at.isoformat() + "Z",
    }


@app.get("/api/oil/lookup")
def oil_lookup(q: Optional[str] = Query(None, description="Search term e.g. 'brent'")):
    """
    Lightweight search endpoint for oil benchmarks.
    Returns a list of matching instruments with a synthetic latest price snapshot.
    """
    term = (q or "").strip().lower()
    matches = []
    for item in OIL_BENCHMARKS:
        text = " ".join([item["id"], item["name"], item["region"]]).lower()
        if term == "" or term in text:
            snap = synth_price(item["id"])  # deterministic per id
            matches.append({
                "id": item["id"],
                "name": item["name"],
                "region": item["region"],
                "unit": item["unit"],
                "snapshot": snap,
            })
    return {
        "query": term,
        "count": len(matches),
        "results": matches,
    }


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
