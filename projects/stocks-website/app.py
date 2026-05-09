from flask import Flask, render_template, jsonify, Response
import yfinance as yf
import pandas as pd
from functools import lru_cache
import time
import threading
import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

NEWS_CACHE = {}
NEWS_CACHE_TIMEOUT = 240  # 4 minutes

def get_stock_data_cached(ticker):
    """Cached stock data fetch - uses fast_info first, history as minimal fallback"""
    try:
        stock = yf.Ticker(ticker)
        
        # Try fast_info first (much faster, no extra HTTP requests needed)
        price = 'N/A'
        prev_close = 'N/A'
        ohlc = {'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A'}
        
        # Get price from fast_info
        try:
            lp = stock.fast_info.get('lastPrice')
            if lp is not None and isinstance(lp, (int, float)):
                price = round(float(lp), 2)
        except Exception:
            pass
        
        # Get previous close from fast_info
        try:
            pc = stock.fast_info.get('previousClose')
            if pc is not None and isinstance(pc, (int, float)):
                prev_close = round(float(pc), 2)
        except Exception:
            pass
        
        # Only fall back to history if fast_info failed
        if price == 'N/A' or prev_close == 'N/A':
            try:
                # Get last 2 days of history in one call (with timeout)
                hist = stock.history(period="2d", timeout=5)
                
                if len(hist) >= 2:
                    # prev_close is from the first row (older)
                    if prev_close == 'N/A':
                        pc = hist.iloc[0]['Close']
                        if not pd.isna(pc):
                            prev_close = round(float(pc), 2)
                    
                    # price is from the last row (newer)
                    if price == 'N/A':
                        lp = hist.iloc[-1]['Close']
                        if not pd.isna(lp):
                            price = round(float(lp), 2)
                
                # Get OHLC from most recent day if available
                if len(hist) > 0:
                    row = hist.iloc[-1]
                    ohlc = {
                        'open': round(float(row['Open']), 2) if not pd.isna(row['Open']) else 'N/A',
                        'high': round(float(row['High']), 2) if not pd.isna(row['High']) else 'N/A',
                        'low': round(float(row['Low']), 2) if not pd.isna(row['Low']) else 'N/A',
                        'close': round(float(row['Close']), 2) if not pd.isna(row['Close']) else 'N/A',
                    }
            except Exception:
                pass  # Keep N/A values if history fails
        
        # Calculate daily change and percent change
        change = 'N/A'
        pct_change = 'N/A'
        if isinstance(price, (int, float)) and prev_close != 'N/A' and float(prev_close) != 0:
            change = round(float(price) - float(prev_close), 2)
            pct_change = round((change / float(prev_close)) * 100, 2)
        
        return {
            'price': price,
            'prev_close': prev_close,
            'change': change,
            'pct_change': pct_change,
            'ohlc': ohlc
        }
    except Exception:
        return {
            'price': 'N/A',
            'prev_close': 'N/A', 
            'change': 'N/A',
            'pct_change': 'N/A',
            'ohlc': {'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A'}
        }


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


@app.route('/')
def index():
    return render_template('index.html')


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
                'market_cap': 'N/A'
            }
    
    # BTC stats
    btc = yf.Ticker('BTC-USD')
    btc_hist = btc.history(period="52w")
    
    if len(btc_hist) > 0:
        stats['BTC'] = {
            'high_52w': round(btc_hist['High'].max(), 2),
            'low_52w': round(btc_hist['Low'].min(), 2),
            'volume': int(btc_hist['Volume'].iloc[-1]) if not pd.isna(btc_hist['Volume'].iloc[-1]) else 0,
            'market_cap': 'N/A'
        }
    
    return jsonify(stats)


def generate():
    """Generate stock data stream for SSE"""
    while True:
        try:
            # Fetch all stock data
            data = fetch_stock_data()
            yield f"data: {json.dumps({'data': data})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        time.sleep(CACHE_TIMEOUT)


def fetch_rss_news(ticker, feed_url):
    """Fetch news from RSS feed for a ticker"""
    try:
        import feedparser
        
        # Replace placeholder in URL with ticker
        url = feed_url.replace('{ticker}', ticker)
        
        # Parse RSS feed
        feed = feedparser.parse(url)
        
        news_items = []
        for entry in feed.entries[:5]:
            # Clean up the title
            title = entry.get('title', 'No title')
            
            # Get link
            link = entry.get('link', '')
            
            # Get published date (format nicely)
            published = entry.get('published', '')
            
            news_items.append({
                'title': title,
                'url': link,
                'time': published
            })
        
        return news_items if news_items else [{'title': 'No recent news available', 'url': '', 'time': ''}]
    
    except Exception as e:
        return [{'title': 'News loading error', 'url': '', 'time': ''}]


def fetch_yahoo_finance_news(ticker):
    """Fetch news from Yahoo Finance using their RSS feed"""
    try:
        import feedparser
        
        # Yahoo Finance RSS feed for ticker news
        rss_url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        
        feed = feedparser.parse(rss_url)
        
        news_items = []
        for entry in feed.entries[:5]:
            title = entry.get('title', 'No title')
            link = entry.get('link', '')
            published = entry.get('published', '')
            
            news_items.append({
                'title': title,
                'url': link,
                'time': published
            })
        
        return news_items if news_items else [{'title': 'No recent news available', 'url': '', 'time': ''}]
    
    except Exception as e:
        return [{'title': 'News loading error', 'url': '', 'time': ''}]


def fetch_news(ticker):
    """Fetch news for a ticker - try RSS first, then fallback"""
    global NEWS_CACHE
    
    current_time = time.time()
    if ticker in NEWS_CACHE and (current_time - NEWS_CACHE[ticker]['timestamp']) < NEWS_CACHE_TIMEOUT:
        return NEWS_CACHE[ticker]['news']
    
    try:
        # Try Yahoo Finance RSS feed
        news_items = fetch_yahoo_finance_news(ticker)
        
        if not news_items or (len(news_items) == 1 and 'error' in news_items[0].get('title', '').lower()):
            # Fallback to simple response if RSS fails
            news_items = [
                {'title': f'Recent {ticker} stock news', 'url': f'https://finance.yahoo.com/quote/{ticker}/news', 'time': ''},
                {'title': f'{ticker} market updates', 'url': f'https://finance.yahoo.com/quote/{ticker}', 'time': ''},
            ]
        
        # Cache the result
        NEWS_CACHE[ticker] = {'news': news_items, 'timestamp': current_time}
        return news_items
        
    except Exception as e:
        # Return cached news if available, otherwise default message
        return [{'title': 'News loading error', 'url': '', 'time': ''}]


@app.route('/api/news/<ticker>')
def get_news(ticker):
    """API endpoint for news data for a specific ticker"""
    news = fetch_news(ticker)
    return jsonify({'ticker': ticker, 'news': news})


@app.route('/api/news/headlines')
def get_headlines():
    """API endpoint for global headlines from news-headlines.py sources"""
    try:
        import sys
        import os
        # Add parent directory to path for news-headlines.py import
        sys.path.insert(0, os.path.dirname(__file__))
        import news_headlines
        
        headlines = news_headlines.fetch_headlines()
        news_items = []
        for category, items in headlines.items():
            for item in items:
                news_items.append({
                    'title': item,
                    'category': category,
                    'url': ''
                })
        
        return jsonify({'headlines': news_items, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'error': str(e), 'headlines': []})


if __name__ == '__main__':
    import sys
    port = 5001
    if len(sys.argv) > 1 and sys.argv[1] == '--port':
        try:
            port = int(sys.argv[2])
        except (ValueError, IndexError):
            port = 5001
    app.run(debug=True, host='0.0.0.0', port=port)
