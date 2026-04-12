from flask import Flask, render_template
import yfinance as yf

app = Flask(__name__)

STOCKS = {
    'SPX': '^GSPC',
    'NVDA': 'NVDA',
    'MSFT': 'MSFT',
    'AAPL': 'AAPL',
    'TSLA': 'TSLA',
    'IBIT': 'IBIT'
}

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        full_name = info.get('longName', ticker)
        price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        return {'name': full_name, 'price': price}
    except Exception:
        return {'name': ticker, 'price': 'N/A'}

@app.route('/')
def index():
    stock_data = []
    for ticker, yf_ticker in STOCKS.items():
        data = get_stock_data(yf_ticker)
        stock_data.append({
            'ticker': ticker,
            'name': data['name'],
            'price': data['price']
        })
    return render_template('index.html', stocks=stock_data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
