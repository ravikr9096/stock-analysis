import pandas as pd
from tvDatafeed import TvDatafeed, Interval
import datetime
import time
import threading

# Initialize TvDatafeed globally to avoid reconnecting on every call
tv = None

# Add a lock and a timestamp to manage rate limiting to avoid 429 errors
TV_DATAFEED_LOCK = threading.Lock()
LAST_API_CALL_TIME = 0
MIN_INTERVAL_SECONDS = 0.5  # Allow 2 requests per second to be safe

def get_tv_instance():
    global tv
    if tv is None:
        tv = TvDatafeed()
    return tv

def get_5min_candle_data(symbol: str, exchange: str = "NSE", n_bars: int = None, max_retries: int = 10) -> pd.DataFrame:
    """
    Fetches 5-minute candle data (Open, High, Low, Close, Volume, Color) for a given stock symbol.
    
    Args:
        symbol (str): The stock symbol (e.g., 'GRASIM').
        exchange (str): The exchange where the symbol is listed (e.g., 'NSE', 'BSE', 'NASDAQ').
        n_bars (int, optional): The number of 5-minute candles to fetch. 
                                If None, calculates the candles created today since 9:15 AM.
                      
    Returns:
        pandas.DataFrame: A DataFrame containing Open, High, Low, Close, Volume, and Color data.
                          Returns an empty DataFrame if data fetching fails or symbol is invalid.
    """
    global LAST_API_CALL_TIME
    try:
        filter_today = False
        ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now = datetime.datetime.now(ist)
        
        if n_bars is None:
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            if now < market_open:
                print(f"Warning: Market hasn't opened yet today for {symbol}.")
                return pd.DataFrame()
                
            end_time = min(now, market_close)
            delta_minutes = (end_time - market_open).total_seconds() / 60
            n_bars = int(delta_minutes // 5) + 1
            filter_today = True

        # Get the global TvDatafeed instance
        tv_instance = get_tv_instance()

        # Retry loop: fetch data until it is populated
        data = None
        attempts = 0
        while attempts < max_retries:
            with TV_DATAFEED_LOCK:
                # Throttle requests to avoid hitting rate limits from tvdatafeed
                elapsed = time.monotonic() - LAST_API_CALL_TIME
                if elapsed < MIN_INTERVAL_SECONDS:
                    time.sleep(MIN_INTERVAL_SECONDS - elapsed)

                data = tv_instance.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_5_minute, n_bars=n_bars)
                LAST_API_CALL_TIME = time.monotonic()

            if data is not None and not data.empty:
                break
                
            attempts += 1
            print(f"Attempt {attempts}: No data returned for {symbol}. Retrying in 1 second...")
            time.sleep(1)

        if data is None or data.empty:
            print(f"Warning: Failed to retrieve data for '{symbol}' after {max_retries} attempts.")
            return pd.DataFrame()
            
        # Select only the required columns and rename them to match standard capitalization
        candle_data = data[['open', 'high', 'low', 'close', 'volume']].copy()
        candle_data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Add a column indicating whether the candle is green or red
        candle_data.loc[candle_data['Close'] >= candle_data['Open'], 'Color'] = 'Green'
        candle_data.loc[candle_data['Close'] < candle_data['Open'], 'Color'] = 'Red'
        
        # tvDatafeed returns the datetime as the index, just like yfinance
        
        # Filter to ensure only strictly today's dates are returned (in case of holidays/weekends)
        if filter_today and not candle_data.empty:
            candle_data = candle_data[candle_data.index.date == now.date()]

        return candle_data
        
    except Exception as e:
        print(f"An error occurred while fetching data for {symbol}: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Example usage:
    # Let's fetch data for Grasim Industries on the NSE
    test_symbol = "GRASIM" 
    test_exchange = "NSE"
    
    print(f"Fetching 5-minute candle data for {test_symbol}...")
    
    # Fetching today's bars since market open
    df = get_5min_candle_data(test_symbol, exchange=test_exchange)
    
    if not df.empty:
        print(f"\nData successfully retrieved! Showing the last 5 candles for {test_symbol}:\n")
        print(df)
    else:
        print("Failed to retrieve data.")
