from flask import Flask, render_template
import yfinance as yf

app = Flask(__name__)

STOCKS = {
    'SPX':  ('^GSPC',  'S&P 500'),
    'NVDA': ('NVDA',   'NVIDIA'),
    'MSFT': ('MSFT',   'Microsoft'),
    'AAPL': ('AAPL',   'Apple'),
    'TSLA': ('TSLA',   'Tesla'),
    'IBIT': ('IBIT',   'iShares Bitcoin Trust'),
}

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        price = info.get('last_price') or info.get('lastPrice') or 'N/A'
        
        # Get previous day close using history
        hist = stock.history(period="2d")
        prev_close = 'N/A'
        if len(hist) >= 2:
            prev_close = hist.iloc[0]['Close']
        
        # fast_info doesn't have longName, fall back to ticker symbol
        return {'name': ticker, 'price': round(price, 2) if isinstance(price, float) else price, 'prev_close': round(prev_close, 2) if isinstance(prev_close, float) else prev_close}
    except Exception:
        return {'name': ticker, 'price': 'N/A', 'prev_close': 'N/A'}

@app.route('/')
def index():
    stock_data = []
    for ticker, (yf_ticker, full_name) in STOCKS.items():
        data = get_stock_data(yf_ticker)
        stock_data.append({
            'ticker': ticker,
            'name': full_name,
            'price': data['price'],
            'prev_close': data['prev_close']
        })
    return render_template('index.html', stocks=stock_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
