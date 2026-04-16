from flask import Flask, render_template
import yfinance as yf
import pandas as pd

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

def get_stock_data(ticker):
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
            'price': round(price, 2) if isinstance(price, float) else price,
            'prev_close': prev_close,
            'ohlc': ohlc
        }
    except Exception:
        return {'price': 'N/A', 'prev_close': 'N/A', 'ohlc': {'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A'}}


@app.route('/')
def index():
    stock_data = []
    for ticker, (yf_ticker, full_name) in STOCKS.items():
        data = get_stock_data(yf_ticker)
        stock_data.append({
            'ticker': ticker,
            'name': full_name,
            'price': data['price'],
            'prev_close': data['prev_close'],
            'ohlc': data['ohlc']
        })
    
    # Add BTC
    btc_data = get_stock_data(BTC_TICKER[0])
    stock_data.append({
        'ticker': 'BTC',
        'name': BTC_TICKER[1],
        'price': btc_data['price'],
        'prev_close': btc_data['prev_close'],
        'ohlc': btc_data['ohlc']
    })
    
    return render_template('index.html', stocks=stock_data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
