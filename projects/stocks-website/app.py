from flask import Flask, render_template, jsonify, Response
import yfinance as yf
import pandas as pd
from functools import lru_cache
import time
import threading

app = Flask(__name__)

STOCKS = {
    'SPX':  ('^GSPC',  'S&P 500'),
    'NVDA': ('NVDA',   'NVIDIA'),
    'MSFT': ('MSFT',   'Microsoft'),
    'AAPL': ('AAPL',   'Apple'),
    'TSLA': ('TSLA',   'Tesla'),
    'IBIT': ('IBIT',   'iShares Bitcoin Trust'),
}

BTC_TICKER = ('BTC-USD', 'Bitcoin')

CACHE_TIMEOUT = 30  # seconds
last_update_time = 0
cached_data = None

def get_stock_data_cached(ticker):
    """Cached stock data fetch with LRU cache"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        
        # Get OHLC from history (most recent day)
        hist = stock.history(period="1d")
        
        # Try fast_info first, fall back to history
        price = getattr(info, 'last_price', None) or getattr(info, 'lastPrice', None)
        if price is None and len(hist) > 0:
            price = hist.iloc[-1]['Close']
        
        # Get OHLC from history
        if len(hist) > 0:
            row = hist.iloc[-1]
            ohlc = {
                'open': round(row['Open'], 2) if not pd.isna(row['Open']) else 'N/A',
                'high': round(row['High'], 2) if not pd.isna(row['High']) else 'N/A',
                'low': round(row['Low'], 2) if not pd.isna(row['Low']) else 'N/A',
                'close': round(row['Close'], 2) if not pd.isna(row['Close']) else 'N/A',
            }
        else:
            ohlc = {'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A'}
        
        # Get previous day close
        hist2 = stock.history(period="2d")
        prev_close = 'N/A'
        if len(hist2) >= 2:
            prev_close = round(hist2.iloc[0]['Close'], 2)
        
        return {
            'price': round(price, 2) if isinstance(price, (int, float)) else price,
            'prev_close': prev_close,
            'ohlc': ohlc
        }
    except Exception:
        return {'price': 'N/A', 'prev_close': 'N/A', 'ohlc': {'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A'}}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stocks')
def get_stocks():
    """API endpoint for stock data with caching"""
    global last_update_time, cached_data
    
    current_time = time.time()
    
    # Return cached data if within timeout
    if cached_data and (current_time - last_update_time) < CACHE_TIMEOUT:
        return jsonify(cached_data)
    
    # Fetch fresh data
    stock_data = []
    for ticker, (yf_ticker, full_name) in STOCKS.items():
        data = get_stock_data_cached(yf_ticker)
        stock_data.append({
            'ticker': ticker,
            'name': full_name,
            'price': data['price'],
            'prev_close': data['prev_close'],
            'ohlc': data['ohlc']
        })
    
    # Add BTC
    btc_data = get_stock_data_cached(BTC_TICKER[0])
    stock_data.append({
        'ticker': 'BTC',
        'name': BTC_TICKER[1],
        'price': btc_data['price'],
        'prev_close': btc_data['prev_close'],
        'ohlc': btc_data['ohlc']
    })
    
    cached_data = {
        'data': stock_data,
        'timestamp': current_time
    }
    last_update_time = current_time
    
    return jsonify(cached_data)


@app.route('/api/ticker')
def ticker_stream():
    """Server-Sent Events endpoint for real-time price updates"""
    def generate():
        while True:
            stock_data = []
            
            # Get fresh data for each event
            for ticker, (yf_ticker, full_name) in STOCKS.items():
                data = get_stock_data_cached(yf_ticker)
                stock_data.append({
                    'ticker': ticker,
                    'name': full_name,
                    'price': data['price'],
                    'prev_close': data['prev_close'],
                    'ohlc': data['ohlc']
                })
            
            # Add BTC
            btc_data = get_stock_data_cached(BTC_TICKER[0])
            stock_data.append({
                'ticker': 'BTC',
                'name': BTC_TICKER[1],
                'price': btc_data['price'],
                'prev_close': btc_data['prev_close'],
                'ohlc': btc_data['ohlc']
            })
            
            import json
            yield f"data: {json.dumps(stock_data)}\n\n"
            
            import time
            time.sleep(5)  # Update every 5 seconds
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/stats')
def get_stats():
    """Get trading statistics"""
    stats = {}
    
    for ticker, (yf_ticker, _) in STOCKS.items():
        stock = yf.Ticker(yf_ticker)
        
        # Get 52-week high/low
        hist = stock.history(period="52w")
        
        if len(hist) > 0:
            stats[ticker] = {
                'high_52w': round(hist['High'].max(), 2),
                'low_52w': round(hist['Low'].min(), 2),
                'volume': int(hist['Volume'].iloc[-1]) if not pd.isna(hist['Volume'].iloc[-1]) else 0,
                'market_cap': stock.info.get('marketCap', 0) if hasattr(stock, 'info') else 0
            }
    
    # BTC stats
    btc = yf.Ticker('BTC-USD')
    btc_hist = btc.history(period="52w")
    
    if len(btc_hist) > 0:
        stats['BTC'] = {
            'high_52w': round(btc_hist['High'].max(), 2),
            'low_52w': round(btc_hist['Low'].min(), 2),
            'volume': int(btc_hist['Volume'].iloc[-1]) if not pd.isna(btc_hist['Volume'].iloc[-1]) else 0,
            'market_cap': btc.info.get('marketCap', 0) if hasattr(btc, 'info') else 0
        }
    
    return jsonify(stats)


if __name__ == '__main__':
    import sys
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1] == '--port':
        try:
            port = int(sys.argv[2])
        except (ValueError, IndexError):
            port = 5000
    app.run(debug=True, host='0.0.0.0', port=port)
