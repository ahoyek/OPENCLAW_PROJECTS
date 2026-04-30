#!/usr/bin/env python3
"""
Daily News Headlines Bot
Fetches latest headlines from world news, tech/AI, markets, and crypto sources
and posts them to Discord.
Scheduled: 8 AM and 6 PM Dubai time (Asia/Dubai)
"""

import requests
import os
import re
from datetime import datetime
import json

# Configuration
LOG_FILE = "/Users/ahoyek/.openclaw/workspace/news-bot.log"
DISCORD_CHANNEL_ID = "1484630456103338236"

def log(message):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line + "\n")
    except Exception:
        pass

def fetch_headlines():
    """Fetch headlines from multiple sources."""
    
    headlines = {
        "🌍 World & Politics": [],
        "🤖 Tech & AI": [],
        "📈 Markets": [],
        "₿ Crypto": []
    }
    
    headers = {"User-Agent": "NewsBot/1.0 (Anthony's Daily News)"}
    
    # World News - Reddit r/worldnews
    try:
        log("Fetching world news...")
        response = requests.get("https://www.reddit.com/r/worldnews/top.json?limit=5&time=day", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for post in data["data"]["children"][:5]:
                title = post["data"]["title"]
                if len(title) > 100:
                    title = title[:97] + "..."
                headlines["🌍 World & Politics"].append(title)
    except Exception as e:
        log(f"  ⚠️ Error fetching world news: {e}")

    # French News - Le Monde RSS
    try:
        log("Fetching French news...")
        response = requests.get("https://www.lemonde.fr/rss/une.xml", headers=headers, timeout=15)
        if response.status_code == 200:
            content = response.text
            titles = re.findall(r'<title>([^<]+)</title>', content)
            for title in titles[1:5]:
                if len(title) > 100:
                    title = title[:97] + "..."
                headlines["🌍 World & Politics"].append(f"[FR] {title}")
    except Exception as e:
        log(f"  ⚠️ Error fetching French news: {e}")

    # GCC News - Al Jazeera (Middle East focus) RSS
    try:
        log("Fetching GCC/Middle East news...")
        response = requests.get("https://www.aljazeera.com/xml/rss/all.xml", headers=headers, timeout=15)
        if response.status_code == 200:
            content = response.text
            titles = re.findall(r'<title>([^<]+)</title>', content)
            for title in titles[1:5]:
                if len(title) > 100:
                    title = title[:97] + "..."
                headlines["🌍 World & Politics"].append(f"[GCC] {title}")
    except Exception as e:
        log(f"  ⚠️ Error fetching GCC news: {e}")
    
    # Tech News - Reddit r/technology
    try:
        log("Fetching tech news...")
        response = requests.get("https://www.reddit.com/r/technology/top.json?limit=5&time=day", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for post in data["data"]["children"][:5]:
                title = post["data"]["title"]
                if len(title) > 100:
                    title = title[:97] + "..."
                headlines["🤖 Tech & AI"].append(title)
    except Exception as e:
        log(f"  ⚠️ Error fetching tech news: {e}")
    
    # AI News - Reddit r/ArtificialIntelligence
    try:
        log("Fetching AI news...")
        response = requests.get("https://www.reddit.com/r/ArtificialIntelligence/top.json?limit=3&time=day", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for post in data["data"]["children"][:3]:
                title = post["data"]["title"]
                if len(title) > 100:
                    title = title[:97] + "..."
                if title not in headlines["🤖 Tech & AI"]:
                    headlines["🤖 Tech & AI"].append(title)
    except Exception as e:
        log(f"  ⚠️ Error fetching AI news: {e}")
    
    # Market News - MarketWatch RSS
    try:
        log("Fetching market news...")
        response = requests.get("https://feeds.marketwatch.com/marketwatch/topstory", headers=headers, timeout=15)
        if response.status_code == 200:
            content = response.text
            titles = re.findall(r'<title>([^<]+)</title>', content)
            for title in titles[1:6]:
                if len(title) > 100:
                    title = title[:97] + "..."
                headlines["📈 Markets"].append(title)
    except Exception as e:
        log(f"  ⚠️ Error fetching market news: {e}")
    
    # Crypto News - Reddit r/CryptoCurrency
    try:
        log("Fetching crypto news...")
        response = requests.get("https://www.reddit.com/r/CryptoCurrency/top.json?limit=5&time=day", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for post in data["data"]["children"][:5]:
                title = post["data"]["title"]
                if len(title) > 100:
                    title = title[:97] + "..."
                headlines["₿ Crypto"].append(title)
    except Exception as e:
        log(f"  ⚠️ Error fetching crypto news: {e}")
    
    return headlines

def get_crypto_prices():
    """Get current crypto prices."""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd", timeout=10)
        if response.status_code == 200:
            data = response.json()
            btc = data.get('bitcoin', {}).get('usd', 0)
            eth = data.get('ethereum', {}).get('usd', 0)
            sol = data.get('solana', {}).get('usd', 0)
            return f"🟠 **Bitcoin:** ${btc:,.0f} | 🟣 **Ethereum:** ${eth:,.0f} | 🔵 **Solana:** ${sol:,.2f}"
    except Exception as e:
        log(f"  ⚠️ Error fetching crypto prices: {e}")
    return "⏳ *Crypto prices unavailable right now*"

def build_message():
    """Build the formatted news message."""
    log("🔄 Fetching news headlines...")
    
    headlines = fetch_headlines()
    
    # Build message
    date_str = datetime.now().strftime("%B %d, %Y")
    message = f"## 📰 Daily Headlines — {date_str}\n\n"
    
    for category, items in headlines.items():
        if items:
            message += f"### {category}\n"
            for item in items:
                message += f"• {item}\n"
            message += "\n"
    
    # Add crypto prices
    crypto_prices = get_crypto_prices()
    if crypto_prices:
        message += f"\n**{crypto_prices}**\n"
    
    log("✅ Headlines fetched successfully")
    return message

def post_to_discord(message):
    """Post message to Discord channel."""
    # Method 1: Try via OpenClaw's messaging system
    log(f"Posting to Discord channel {DISCORD_CHANNEL_ID}...")
    
    # We'll output to stdout for now - will be captured by cron
    # In production, you'd use Discord webhook or API
    print("\n" + "="*60 + "\n")
    print(message)
    print("="*60 + "\n")
    
    # For actual Discord posting, you'd need either:
    # 1. A Discord webhook URL
    # 2. Discord bot token with permissions
    # 3. Use OpenClaw's internal messaging
    
    log("✅ Message prepared for Discord")

if __name__ == "__main__":
    log("="*50)
    log("📰 Daily News Headlines Bot Starting")
    log("="*50)
    
    message = build_message()
    post_to_discord(message)
    
    log("✅ Daily news job completed")
