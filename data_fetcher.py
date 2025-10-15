# data_fetcher.py
import os
import time
import json
import re
import yfinance as yf
import pandas as pd
import feedparser
from urllib.parse import quote_plus
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

from utils import make_request_with_retries, now_ist
import config

CACHE_FILE = 'symbol_cache.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def resolve_symbol(query):
    cache = load_cache()
    query_key = query.upper()
    if query_key in cache:
        print(f"   -> Found '{query_key}' in cache. Skipping API calls.")
        cached = cache[query_key]
        return cached['nse'], cached['yahoo'], cached['display']
    print(f"   -> '{query_key}' not in cache. Performing live lookup...")
    try:
        print("   -> Trying to resolve symbol via Yahoo Finance API...")
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote_plus(query)}"
        r = make_request_with_retries(url, timeout=20)
        data = r.json().get('quotes', [])
        picks = [q for q in data if ".NS" in q.get('symbol', '') and q.get('quoteType') == 'EQUITY'] or \
                [q for q in data if ".NS" in q.get('symbol', '')]
        if picks:
            best = picks[0]
            display = best.get("longname") or best.get("shortname") or best["symbol"]
            nse_symbol = best["symbol"].replace(".NS", "")
            yahoo_symbol = best["symbol"]
            print(f"      - Symbol found via Yahoo Finance: {nse_symbol}")
            cache[query_key] = {'nse': nse_symbol, 'yahoo': yahoo_symbol, 'display': display}
            save_cache(cache)
            return nse_symbol, yahoo_symbol, display
    except Exception as e:
        print(f"      - Yahoo Finance API failed: {e}. Trying local NSE fallback.")
    print("   -> Trying to resolve symbol via local NSE list (with fuzzy search)...")
    nse_file = 'nse_symbols.csv'
    if not os.path.exists(nse_file) or (time.time() - os.path.getmtime(nse_file)) > 7 * 86400:
        update_nse_symbol_list(nse_file)
    match = resolve_symbol_from_nse_local(query, nse_file)
    if match is not None:
        nse_symbol = match['SYMBOL']
        display_name = match['NAME OF COMPANY']
        yahoo_symbol = f"{nse_symbol}.NS"
        print(f"      - Best fuzzy match found via local NSE list: {nse_symbol}")
        cache[query_key] = {'nse': nse_symbol, 'yahoo': yahoo_symbol, 'display': display_name}
        save_cache(cache)
        return nse_symbol, yahoo_symbol, display_name
    raise ValueError(f"Could not find symbol for '{query}' from any source.")

def update_nse_symbol_list(file_path='nse_symbols.csv'):
    url = 'https://archives.nseindia.com/content/equities/EQUITY_L.csv'
    print("   -> Checking/updating local NSE symbol list...")
    try:
        response = make_request_with_retries(url)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print("      - NSE symbol list updated successfully.")
        return True
    except Exception as e:
        print(f"      - Could not download NSE symbol list: {e}. Will use existing cache if available.")
        return False

def resolve_symbol_from_nse_local(query, file_path='nse_symbols.csv'):
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        query_lower = query.lower()
        best_match = None
        highest_score = 0.0
        for index, row in df.iterrows():
            symbol = str(row['SYMBOL']).lower()
            company_name = str(row['NAME OF COMPANY']).lower()
            symbol_score = SequenceMatcher(None, query_lower, symbol).ratio()
            name_score = SequenceMatcher(None, query_lower, company_name).ratio()
            if query_lower in company_name:
                name_score = max(name_score, 0.7)
            current_score = max(symbol_score * 1.0, name_score * 0.8)
            if current_score > highest_score:
                highest_score = current_score
                best_match = row
        if highest_score > 0.6:
            return best_match
        else:
            return None
    except Exception as e:
        print(f"      - Error during fuzzy search on local NSE list: {e}")
        return None

def fetch_yfinance_news(y_symbol):
    print("   -> Fetching from Yahoo Finance...")
    try:
        ticker = yf.Ticker(y_symbol)
        news = ticker.news
        items = []
        now = now_ist()
        for item in news:
            try:
                published = datetime.fromtimestamp(item['provider_publish_time'], tz=timezone.utc).astimezone(now.tzinfo)
                if (now - published).days <= config.LOOKBACK_NEWS_DAYS:
                    items.append({"title": item['title'].strip(), "link": item['link'], "published": published, "source": "Yahoo Finance"})
            except:
                continue
        return items
    except Exception as e:
        print(f"      - Could not fetch from Yahoo Finance: {e}")
        return []

def fetch_google_news(name, symbol, days=7):
    print("   -> Fetching from Google News...")
    items = []; now = now_ist(); q = f'"{name}" OR {symbol} when:{days}d'
    feed_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(feed_url)
    for e in feed.entries:
        try:
            published = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc).astimezone(now.tzinfo)
            if (now - published).days <= days:
                items.append({"title": e.title.strip(), "link": e.link, "published": published, "source": "Google News"})
        except: continue
    return items

def fetch_moneycontrol_news(query):
    print("   -> Fetching from MoneyControl...")
    items = []
    try:
        search_query = query.replace(' Ltd', '').replace(' Limited', '').replace('&', '').replace(' ', '-').lower()
        url = f"https://www.moneycontrol.com/news/tags/{search_query}.html"
        r = make_request_with_retries(url)
        soup = BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')
        news_list = soup.select("#cagetory a")
        for item in news_list[:10]:
            title = item.get('title'); link = item.get('href')
            if title and link:
                items.append({"title": title.strip(), "link": link, "published": now_ist(), "source": "MoneyControl"})
    except Exception as e:
        print(f"      - Could not fetch from MoneyControl: {e}")
    return items

def fetch_economic_times_news(query):
    print("   -> Fetching from Economic Times...")
    items = []
    try:
        search_query = query.lower().replace(' ltd', '').replace(' limited', '').replace('&', '').replace(' ', '-')
        url = f"https://economictimes.indiatimes.com/topic/{search_query}"
        r = make_request_with_retries(url)
        soup = BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')
        news_list = soup.select("div.story_list a")
        for item in news_list[:10]:
            title = item.get_text(strip=True)
            link = "https://economictimes.indiatimes.com" + item.get('href')
            if title and link:
                items.append({"title": title, "link": link, "published": now_ist(), "source": "Economic Times"})
    except Exception as e:
        print(f"      - Could not fetch from Economic Times: {e}")
    return items

def fetch_trendlyne_announcements(nse_symbol):
    print("   -> Fetching from Trendlyne (Announcements)...")
    items = []
    try:
        search_url = f"https://api.bseindia.com/Msmgr/GetSecurityCsv?typ=F&text={nse_symbol}"
        search_res = make_request_with_retries(search_url)
        if search_res.text.strip().startswith("<!DOCTYPE html>"):
            print(f"      - BSE API returned an HTML error page while getting code. Skipping.")
            return []
        lines = search_res.text.strip().split('\n')
        if len(lines) < 2 or len(lines[1].split('|')) < 3:
            print(f"      - Could not find valid BSE Security Code for {nse_symbol}. Skipping.")
            return []
        bse_code = lines[1].split('|')[2].strip()
        trendlyne_url = f"https://trendlyne.com/company/{bse_code}/{nse_symbol.lower()}/corporate-announcements/"
        print(f"      - Querying Trendlyne URL: {trendlyne_url}")
        res = make_request_with_retries(trendlyne_url)
        soup = BeautifulSoup(res.content, 'html.parser', from_encoding='utf-8')
        table = soup.find('table', class_='table-striped table-bordered')
        if not table:
            print("      - Could not find announcements table on Trendlyne page. Skipping.")
            return []
        rows = table.select("tbody tr")
        for row in rows[:5]:
            cols = row.find_all('td')
            if len(cols) > 0:
                title = cols[0].get_text(strip=True)
                items.append({"title": title, "link": trendlyne_url, "published": now_ist(), "source": "Trendlyne Announcements"})
        return items
    except Exception as e:
        print(f"      - Could not fetch from Trendlyne Announcements: {e}")
        return []

def score_news_relevance(headline, company_name, source):
    score = 0; headline_lower = headline.lower(); company_name_short = company_name.split()[0].lower()
    if headline_lower.startswith(company_name_short): score += 30
    elif company_name_short in headline_lower: score += 10
    for keyword in config.IMPACT_KEYWORDS:
        if keyword in headline_lower: score += 15
    score += config.SOURCE_BONUS.get(source, 0)
    return score

def fetch_company_profile(y_symbol):
    print("  -> Fetching company business summary...")
    try:
        ticker = yf.Ticker(y_symbol)
        summary = ticker.info.get('longBusinessSummary')
        if summary:
            summary = summary.split('.')[0] + '.'
            if len(summary) > 400:
                summary = summary[:400].rsplit(' ', 1)[0] + '...'
            return summary
        return None
    except Exception as e:
        print(f"      - Could not fetch company profile: {e}")
        return None

def fetch_peer_data(nse_symbol):
    print("  -> Fetching peer comparison data...")
    try:
        api_url = f"https://api.tickertape.in/stocks/peers/{nse_symbol}"
        print(f"      - Querying TickerTape Peers API: {api_url}")
        api_response = make_request_with_retries(api_url)
        api_data = api_response.json()
        if not api_data.get("success", False) or not api_data.get("data"):
            print("      - WARNING: Peer data not found in API response. Skipping peer chart.")
            return None
        peers = api_data["data"][:4]
        peer_metrics = {}
        for peer in peers:
            pe_ratio = peer.get("ratios", {}).get("pe")
            if pe_ratio:
                peer_metrics[peer.get("info", {}).get("ticker")] = pe_ratio
        return peer_metrics
    except Exception as e:
        print(f"      - WARNING: An error occurred fetching peer data from TickerTape: {e}.")
        return None

def fetch_shareholding(nse_symbol):
    print("  -> Fetching shareholding pattern from TickerTape...")
    try:
        print("      - Using TickerTape's direct JSON API for reliability...")
        api_url = f"https://api.tickertape.in/stocks/info/{nse_symbol}"
        print(f"      - Querying TickerTape Info API: {api_url}")
        api_response = make_request_with_retries(api_url)
        api_data = api_response.json()
        if not api_data.get("success", False):
            print("      - WARNING: TickerTape API reported failure. Skipping.")
            return None
        holding_data = api_data.get("data", {}).get("holding", {}).get("data")
        if not holding_data:
            print("      - WARNING: Shareholding data not found in API response. Skipping.")
            return None
        holding_map = {"prom": "Promoter", "mf": "Mutual Funds", "dii": "Other Dom. Inst.", "fii": "Foreign Inst.", "ret": "Retail & Others"}
        shareholding = {}
        for item in holding_data:
            key = holding_map.get(item.get("type"))
            value = item.get("value")
            if key is not None and value is not None:
                shareholding[key] = float(value)
        other_dii_val = shareholding.pop("Other Dom. Inst.", 0)
        shareholding["Other Dom. Inst."] = other_dii_val
        return {k: v for k, v in shareholding.items() if v > 0}
    except Exception as e:
        print(f"      - WARNING: An error occurred fetching from TickerTape API: {e}. Skipping this slide.")
        return None

def fetch_financial_metrics(y_symbol):
    print("  -> Fetching key financial metrics...")
    try:
        ticker = yf.Ticker(y_symbol)
        info = ticker.info
        metrics = {"Market Cap (Cr)": info.get('marketCap', 0) / 1e7, "P/E Ratio": info.get('trailingPE'),
                   "Dividend Yield (%)": info.get('dividendYield', 0) * 100, "52-Wk High": info.get('fiftyTwoWeekHigh'),
                   "52-Wk Low": info.get('fiftyTwoWeekLow'), "Recommendation": info.get('recommendationKey', 'N/A').upper()}
        metrics_clean = {k: v for k, v in metrics.items() if v is not None}
        for key, val in metrics_clean.items():
            if isinstance(val, (int, float)):
                metrics_clean[key] = f"{val:,.2f}"
        return metrics_clean
    except Exception as e:
        print(f"      - Could not fetch financial metrics: {e}")
        return None

def fetch_price_data(y_symbol, index_symbol="^NSEI"):
    print("  -> Fetching price data for stock and index...")
    try:
        ticker = yf.Ticker(y_symbol)
        df = ticker.history(period="1y", interval="1d")
        if df.empty:
            raise ValueError(f"No price data for {y_symbol}")
        index_ticker = yf.Ticker(index_symbol)
        df_index = index_ticker.history(period="1y", interval="1d")
        return df, df_index
    except Exception as e:
        print(f"      - Error fetching price data: {e}")
        raise

def compute_price_snapshot(df):
    if len(df) < 2:
        return {"last_close": df.iloc[-1]["Close"], "d_pct": 0, "d5_pct": 0}
    last, prev = df.iloc[-1], df.iloc[-2]
    d_pct = (last["Close"] / prev["Close"] - 1) * 100
    prev5 = df.iloc[-6] if len(df) >= 6 else prev
    d5_pct = (last["Close"] / prev5["Close"] - 1) * 100
    return {"last_close": last["Close"], "d_pct": d_pct, "d5_pct": d5_pct}

def fetch_company_logo(y_symbol):
    try:
        domain = yf.Ticker(y_symbol).info.get('website', '').split('//')[-1].split('/')[0]
        if domain:
            response = make_request_with_retries(f"https://logo.clearbit.com/{domain}", timeout=10)
            if response and response.status_code == 200:
                return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception:
        pass
    return None
