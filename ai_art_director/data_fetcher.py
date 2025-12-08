# ai_art_director/data_fetcher.py
# v24.3.19 - Production Ready (Clearbit Strict & Domain Inference)

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

from . import utils
from . import config

CACHE_FILE = 'symbol_cache.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def resolve_symbol(query):
    cache = load_cache(); query_key = query.upper()
    if query_key in cache:
        print(f"   -> Found '{query_key}' in cache. Skipping live lookup.")
        cached = cache[query_key]
        return cached['nse'], cached['yahoo'], cached['display']
    print(f"   -> '{query_key}' not in cache. Performing live lookup...")
    print("   -> Trying to resolve symbol via local NSE list (with fuzzy search)...")
    nse_file = 'nse_symbols.csv'
    if not os.path.exists(nse_file) or (time.time() - os.path.getmtime(nse_file)) > 7 * 86400:
        update_nse_symbol_list(nse_file)
    match = resolve_symbol_from_nse_local(query, nse_file)
    if match is not None:
        nse_symbol, display_name, yahoo_symbol = match['SYMBOL'], match['NAME OF COMPANY'], f"{match['SYMBOL']}.NS"
        print(f"      - Best fuzzy match found via local NSE list: {nse_symbol}")
        cache[query_key] = {'nse': nse_symbol, 'yahoo': yahoo_symbol, 'display': display_name}; save_cache(cache)
        return nse_symbol, yahoo_symbol, display_name
    try:
        print("   -> Local search failed. Trying Yahoo Finance API as a fallback...")
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote_plus(query)}"
        r = utils.make_request_with_retries(url, timeout=20); data = r.json().get('quotes', [])
        picks = [q for q in data if ".NS" in q.get('symbol', '') and q.get('quoteType') == 'EQUITY'] or [q for q in data if ".NS" in q.get('symbol', '')]
        if picks:
            best = picks[0]; display = best.get("longname") or best.get("shortname") or best["symbol"]
            nse_symbol, yahoo_symbol = best["symbol"].replace(".NS", ""), best["symbol"]
            print(f"      - Symbol found via Yahoo Finance: {nse_symbol}")
            cache[query_key] = {'nse': nse_symbol, 'yahoo': yahoo_symbol, 'display': display}; save_cache(cache)
            return nse_symbol, yahoo_symbol, display
    except Exception as e:
        print(f"      - Yahoo Finance API also failed: {e}.")
    raise ValueError(f"Could not find symbol for '{query}' from any source.")

def update_nse_symbol_list(file_path='nse_symbols.csv'):
    url = 'https://archives.nseindia.com/content/equities/EQUITY_L.csv'
    print("   -> Local NSE symbol list is old or missing. Downloading fresh copy...")
    try:
        response = utils.make_request_with_retries(url)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print("      - NSE symbol list updated successfully.")
        return True
    except Exception as e:
        print(f"      - Could not download NSE symbol list: {e}.")
        return False

def resolve_symbol_from_nse_local(query, file_path='nse_symbols.csv'):
    try:
        df = pd.read_csv(file_path); df.columns = df.columns.str.strip(); query_lower = query.lower()
        best_match, highest_score = None, 0.0
        for _, row in df.iterrows():
            symbol, name = str(row['SYMBOL']).lower(), str(row['NAME OF COMPANY']).lower()
            s_score, n_score = SequenceMatcher(None, query_lower, symbol).ratio(), SequenceMatcher(None, query_lower, name).ratio()
            if query_lower in name: n_score = max(n_score, 0.7)
            score = max(s_score * 1.0, n_score * 0.8)
            if score > highest_score: highest_score, best_match = score, row
        return best_match if highest_score > 0.6 else None
    except Exception as e:
        print(f"      - Error during fuzzy search on local NSE list: {e}")
        return None

def fetch_tickertape_data(nse_symbol):
    print("  -> Fetching consolidated data from TickerTape API..."); bundle = { "shareholding": None, "metrics": {}, "peers": None, "profile": None, "sector": None }
    try:
        encoded_symbol = quote_plus(nse_symbol)
        search_url = f"https://api.tickertape.in/search?text={encoded_symbol}&types=stock"
        search_res = utils.make_request_with_retries(search_url); search_data = search_res.json()
        stock = next((s for s in search_data.get('data', {}).get('stocks', []) if s.get('ticker') == nse_symbol), None)
        if not (stock and stock.get('sid')): return bundle
        sid = stock['sid']
        api_url = f"https://api.tickertape.in/stocks/info/{sid}"
        api_res = utils.make_request_with_retries(api_url); api_data = api_res.json()
        if not api_data.get("success", False): return bundle
        tt_data = api_data.get("data", {})
        if holding_data := tt_data.get("holding", {}).get("data"):
            h_map = {"prom": "Promoter", "mf": "Mutual Funds", "dii": "Other Dom. Inst.", "fii": "Foreign Inst.", "ret": "Retail & Others"}
            sh = {h_map.get(i.get("type")): float(i.get("value")) for i in holding_data if i.get("type") in h_map and i.get("value") is not None}
            bundle["shareholding"] = {k: v for k, v in sh.items() if v > 0}
        if ratios := tt_data.get("ratios", {}):
            if r := ratios.get("mcap"): bundle["metrics"]["Market Cap (Cr)"] = r / 1e7
            if r := ratios.get("pe"): bundle["metrics"]["P/E Ratio"] = r
            if r := ratios.get("pb"): bundle["metrics"]["P/B Ratio"] = r
            if r := ratios.get("dy"): bundle["metrics"]["Dividend Yield (%)"] = r
        if sector_info := tt_data.get("sector"): bundle["sector"] = sector_info.get("sector")
        if peers := tt_data.get("peers"):
            bundle["peers"] = {p.get("info", {}).get("ticker"): p.get("ratios", {}).get("pe") for p in peers[:4] if p.get("ratios", {}).get("pe")}
        if desc := tt_data.get("profile", {}).get("description"): bundle["profile"] = desc[:800]
    except: pass
    return bundle

def fetch_yfinance_supplemental_details(y_symbol):
    details = {}
    try:
        ticker = yf.Ticker(y_symbol); info = ticker.info; execs = info.get('companyOfficers', [])
        if execs:
            ceo = next((p for p in execs if 'CEO' in p.get('title', '')), execs[0] if execs else None)
            if ceo: details['ceo'] = ceo.get('name')
        if roe := info.get('returnOnEquity'): details['returnOnEquity'] = roe
        if high := info.get('fiftyTwoWeekHigh'): details['52-Wk High'] = high
        if low := info.get('fiftyTwoWeekLow'): details['52-Wk Low'] = low
        if mcap := info.get('marketCap'): details['Market Cap (Cr)'] = mcap / 1e7
    except: pass
    return details

def fetch_quarterly_financials(y_symbol):
    try:
        ticker = yf.Ticker(y_symbol); qf = ticker.quarterly_financials
        if not qf.empty:
            latest = qf.iloc[:, 0]
            return {"Quarterly Revenue (Cr)": latest.get('Total Revenue', 0) / 1e7, "Quarterly Profit (Cr)": latest.get('Net Income', 0) / 1e7}
    except: pass
    return {}

def fetch_price_data(y_symbol):
    try:
        ticker = yf.Ticker(y_symbol); df = ticker.history(period="1y", interval="1d")
        if df.empty: raise ValueError
        index_ticker = yf.Ticker("^NSEI"); df_index = index_ticker.history(period="1y", interval="1d")
        return df, df_index
    except: raise

def fetch_yfinance_news(y_symbol):
    try:
        ticker = yf.Ticker(y_symbol); news = ticker.news; items = []; now = utils.now_ist()
        for item in news:
            try:
                published = datetime.fromtimestamp(item['provider_publish_time'], tz=timezone.utc).astimezone(now.tzinfo)
                if (now - published).days <= config.LOOKBACK_NEWS_DAYS: items.append({"title": item['title'].strip(), "link": item['link'], "published": published, "source": "Yahoo Finance"})
            except: continue
        return items
    except: return []

def fetch_google_news(name, symbol, days=7):
    items = []; now = utils.now_ist(); q = f'"{name}" OR {symbol} when:{days}d'
    feed_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"; feed = feedparser.parse(feed_url)
    for e in feed.entries:
        try:
            published = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc).astimezone(now.tzinfo)
            if (now - published).days <= days: items.append({"title": e.title.strip(), "link": e.link, "published": published, "source": "Google News"})
        except: continue
    return items

def fetch_moneycontrol_news(query):
    items = []
    try:
        s_query = query.replace(' Ltd', '').replace(' Limited', '').replace('&', '').replace(' ', '-').lower()
        url = f"https://www.moneycontrol.com/news/tags/{s_query}.html"
        r = utils.make_request_with_retries(url); soup = BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')
        for item in soup.select("#cagetory a")[:10]:
            if (title := item.get('title')) and (link := item.get('href')): items.append({"title": title.strip(), "link": link, "published": utils.now_ist(), "source": "MoneyControl"})
    except: pass
    return items

def fetch_economic_times_news(query):
    items = []
    try:
        s_query = query.lower().replace(' ltd', '').replace(' limited', '').replace('&', '').replace(' ', '-')
        url = f"https://economictimes.indiatimes.com/topic/{s_query}"
        r = utils.make_request_with_retries(url); soup = BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')
        for item in soup.select("div.story_list a")[:10]:
            if (title := item.get_text(strip=True)) and (link := item.get('href')): items.append({"title": title, "link": "https://economictimes.indiatimes.com" + link, "published": utils.now_ist(), "source": "Economic Times"})
    except: pass
    return items

def fetch_trendlyne_announcements(nse_symbol):
    items = []
    try:
        search_url = f"https://api.bseindia.com/Msmgr/GetSecurityCsv?typ=F&text={nse_symbol}"; search_res = utils.make_request_with_retries(search_url)
        lines = search_res.text.strip().split('\n')
        if len(lines) < 2 or len(lines[1].split('|')) < 3: return []
        bse_code = lines[1].split('|')[2].strip()
        url = f"https://trendlyne.com/company/{bse_code}/{nse_symbol.lower()}/corporate-announcements/"
        res = utils.make_request_with_retries(url); soup = BeautifulSoup(res.content, 'html.parser', from_encoding='utf-8')
        if table := soup.find('table', class_='table-striped table-bordered'):
            for row in table.select("tbody tr")[:5]:
                if (cols := row.find_all('td')) and len(cols) > 0:
                    title = re.sub(r'^\s*-\s*', '', cols[0].get_text(strip=True)); items.append({"title": title, "link": url, "published": utils.now_ist(), "source": "Trendlyne Announcements"})
    except: pass
    return items

def score_news_relevance(headline, company_name, source):
    score = 0; headline_lower = headline.lower(); company_name_short = company_name.split()[0].lower()
    if headline_lower.startswith(company_name_short): score += 30
    elif company_name_short in headline_lower: score += 10
    for keyword in config.IMPACT_KEYWORDS:
        if keyword in headline_lower: score += 15
    score += config.SOURCE_BONUS.get(source, 0)
    return score

def compute_price_snapshot(df):
    if len(df) < 2: return {"last_close": df.iloc[-1]["Close"], "d_pct": 0, "d5_pct": 0}
    last, prev = df.iloc[-1], df.iloc[-2]; d_pct = (last["Close"] / prev["Close"] - 1) * 100
    prev5 = df.iloc[-6] if len(df) >= 6 else prev; d5_pct = (last["Close"] / prev5["Close"] - 1) * 100
    return {"last_close": last["Close"], "d_pct": d_pct, "d5_pct": d5_pct}

def fetch_company_logo(y_symbol):
    print(f"   -> Fetching logo for {y_symbol}...")
    try:
        # 1. Get Domain
        ticker = yf.Ticker(y_symbol)
        info = ticker.info
        website = info.get('website', '')
        
        if not website:
            clean_name = y_symbol.replace('.NS','').replace('.BO','').lower()
            domain = f"{clean_name}.com"
        else:
            if "//" in website: domain = website.split('//')[-1].split('/')[0]
            else: domain = website.split('/')[0]
            if domain.startswith("www."): domain = domain[4:]
            
        print(f"      - Target Domain: {domain}")
        
        # 2. Try Clearbit (Primary)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
        }
        url_clearbit = f"https://logo.clearbit.com/{domain}"
        
        response = utils.make_request_with_retries(url_clearbit, headers=headers, timeout=5)
        if response and response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
             img = Image.open(BytesIO(response.content)).convert("RGBA")
             print("      - ✅ Logo fetched (Clearbit)")
             return img
             
        # 3. Try Google High-Res Favicon (Fallback)
        print("      - ⚠️ Clearbit failed. Trying Google...")
        # Request largest possible size (256 is usually max)
        url_google = f"https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=256"
        
        response = utils.make_request_with_retries(url_google, headers=headers, timeout=10)
        if response and response.status_code == 200:
             img = Image.open(BytesIO(response.content)).convert("RGBA")
             print("      - ✅ Logo fetched (Google)")
             return img

        print(f"      - ❌ Logo not found via any source.")
            
    except Exception as e:
        print(f"      - ⚠️ Logo fetch error: {e}")
        
    return None
