from flask import Flask, render_template, jsonify, Response
import yfinance as yf
import pandas as pd
from functools import lru_cache
import time

app = Flask(__name__)

# TradingApp1 Tickers - requested tickers with full names
STOCKS = {
    'SPX':  ('^GSPC',  'S&P 500 Index'),
    'BTC':  ('BTC-USD', 'Bitcoin USD'),
    'USO':  ('USO',    'United States Oil Fund'),
    'TSLA': ('TSLA',   'Tesla, Inc.'),
    'NVDA': ('NVDA',   'NVIDIA Corporation'),
}

CACHE_TIMEOUT = 30
last_update_time = 0
cached_data = None

@lru_cache(maxsize=128)
def get_stock_data_cached(ticker):
    """Cached stock data fetch"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        
        # Price and currency
        price = getattr(info, 'last_price', None)
        if not price:
            price = info.get('lastPrice') if hasattr(info, 'get') else 0
        
        currency = getattr(info, 'currency', 'USD')
        
        # OHLC data
        hist = stock.history(period="1d")
        if len(hist) > 0:
            open_price = round(float(hist['Open'].iloc[-1]), 2)
            high = round(float(hist['High'].iloc[-1]), 2)
            low = round(float(hist['Low'].iloc[-1]), 2)
            prev_close = round(float(hist['Close'].iloc[-1]), 2)
        else:
            open_price = high = low = prev_close = 0
        
        return {
            'price': round(float(price), 2) if price else 0,
            'currency': currency,
            'open': open_price,
            'high': high,
            'low': low,
            'prev_close': prev_close
        }
    except Exception as e:
        return {'error': str(e), 'price': 0}


@app.route('/')
def index():
    """Main trading dashboard"""
    return render_template('index.html')


@app.route('/api/stocks')
def get_stocks():
    """API endpoint for stock data with caching"""
    global last_update_time, cached_data
    
    current_time = time.time()
    
    if cached_data and (current_time - last_update_time) < CACHE_TIMEOUT:
        return jsonify(cached_data)
    
    # Fetch fresh data
    stock_data = []
    for ticker, (yf_ticker, full_name) in STOCKS.items():
        data = get_stock_data_cached(yf_ticker)
        
        # Calculate change
        prev_close = data.get('prev_close', 0) or 0
        current_price = data.get('price', 0)
        change = round(current_price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0
        
        stock_data.append({
            'ticker': ticker,
            'name': full_name,
            'price': data.get('price', 0),
            'currency': data.get('currency', 'USD'),
            'prev_close': prev_close,
            'change': change,
            'change_pct': change_pct,
            'ohlc': {
                'open': data.get('open', 0),
                'high': data.get('high', 0),
                'low': data.get('low', 0),
                'close': prev_close
            }
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
            
            for ticker, (yf_ticker, full_name) in STOCKS.items():
                data = get_stock_data_cached(yf_ticker)
                
                prev_close = data.get('prev_close', 0) or 0
                current_price = data.get('price', 0)
                change = round(current_price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2) if prev_close else 0
                
                stock_data.append({
                    'ticker': ticker,
                    'name': full_name,
                    'price': data.get('price', 0),
                    'change': change,
                    'change_pct': change_pct
                })
            
            yield f"data: {jsonify(stock_data).get_data(as_text=True)}\n\n"
            time.sleep(5)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/history')
def get_history():
    """Get 30-day price history for charts"""
    ticker = request.args.get('symbol', 'SPX')
    
    if ticker not in STOCKS:
        return jsonify({'error': 'Invalid ticker'}), 400
    
    yf_ticker = STOCKS[ticker][0]
    stock = yf.Ticker(yf_ticker)
    hist = stock.history(period="30d")
    
    if len(hist) == 0:
        return jsonify({'error': 'No history data'}), 404
    
    prices = [{
        'date': str(idx.date()),
        'close': round(float(row['Close']), 2)
    } for idx, row in hist.iterrows()]
    
    return jsonify({
        'ticker': ticker,
        'prices': prices
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
