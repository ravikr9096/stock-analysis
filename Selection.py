import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from analyse import get_5min_candle_data

app = FastAPI(title="NSE Top Stocks API")

# Add CORS middleware to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_nse_data():
    base_url = "https://www.nseindia.com"
    # api_url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
    api_url = "https://www.nseindia.com/api/equity-stockIndex?index=SECURITIES%20IN%20F%26O"
    
    # NSE blocks requests without proper headers, specifically User-Agent.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    # A session is required because NSE requires cookies set from the base page
    session = requests.Session()
    
    try:
        # First request to the base URL to obtain necessary cookies
        session.get(base_url, headers=headers, timeout=10)
        
        # Second request to the actual API
        response = session.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return data
            else:
                print("Error: 'data' key not found in the response.")
                return None
        else:
            print(f"Error: Failed to fetch data. Status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        return None

def format_stock_data(stocks):
    return [
        {
            "symbol": stock.get('symbol', 'Unknown'),
            "pChange": stock.get('pChange', 0),
            "lastPrice": stock.get('lastPrice', 0),
        }
        for stock in stocks
    ]

@app.get("/api/stock-candles/{symbol}")
def get_stock_candles(symbol: str):
    df = get_5min_candle_data(symbol)
    candles = []
    if not df.empty:
        df_reset = df.reset_index()
        if 'datetime' in df_reset.columns:
            df_reset['datetime'] = df_reset['datetime'].astype(str)
        candles = df_reset.to_dict(orient='records')
    return {"symbol": symbol, "candles": candles}

@app.get("/api/top-stocks")
def get_top_stocks():
    api_response = get_nse_data()
    if not api_response or 'data' not in api_response:
        raise HTTPException(status_code=500, detail="Failed to fetch data from NSE")
        
    data = api_response['data']
    advance_info = api_response.get('advance', {'advances': 0, 'declines': 0, 'unchanged': 0})

    valid_data = [item for item in data if 'pChange' in item and isinstance(item['pChange'], (int, float))]
    valid_data = [item for item in valid_data if item.get('symbol') != 'SECURITIES IN F&O']
    
    sorted_data_desc = sorted(valid_data, key=lambda x: x['pChange'], reverse=True)
    sorted_data_asc = sorted(valid_data, key=lambda x: x['pChange'])
    
    return {
        "advance_info": advance_info,
        "top_gainers": format_stock_data(sorted_data_desc[:5]),
        "top_losers": format_stock_data(sorted_data_asc[:5])
    }

# Mount the React frontend build directory to serve static files
dist_dir = os.path.join(os.path.dirname(__file__), "stock-dashboard", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
else:
    print(f"Warning: Frontend build directory not found at {dist_dir}. Please run your frontend build command.")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    uvicorn.run("Selection:app", host="0.0.0.0", port=8000, reload=True)
