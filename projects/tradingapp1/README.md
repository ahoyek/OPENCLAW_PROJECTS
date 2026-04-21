# TradingApp1

Professional trading dashboard with real-time market data, interactive charts, and dark-themed UI.

## Features

- **Real-Time Ticker** - Live price updates via Server-Sent Events (SSE)
- **Interactive Charts** - Chart.js integration with multi-timeframe support
- **Dark Theme UI** - Modern, professional dark-mode design
- **Skeleton Loading** - Instant visual feedback with shimmer animations
- **Watchlist Management** - Quick access to favorite tickers

## Tickers

| Symbol | Name |
|--------|------|
| SPX    | S&P 500 Index |
| BTC    | Bitcoin USD |
| USO    | United States Oil Fund |
| TSLA   | Tesla, Inc. |
| NVDA   | NVIDIA Corporation |

## Dependencies

- Python 3.8+
- Flask
- yfinance
- pandas

## Installation

```bash
pip install flask yfinance pandas
```

## Running

```bash
python app.py
```

Visit `http://localhost:5001` to view the dashboard.
