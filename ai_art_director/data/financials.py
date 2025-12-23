# ai_art_director/data/financials.py
# v26.0.0 - Stock 360 Upgrade (Technicals + Deep Fundamentals)

import yfinance as yf
import pandas as pd
import numpy as np
from urllib.parse import quote_plus
from .. import utils

def fetch_tickertape_data(nse_symbol):
    print("  -> Fetching consolidated data from TickerTape API...")
    bundle = { "shareholding": None, "metrics": {}, "peers": None, "profile": None, "sector": None }
    try:
        encoded_symbol = quote_plus(nse_symbol)
        search_url = f"https://api.tickertape.in/search?text={encoded_symbol}&types=stock"
        
        # 1. Search for SID
        search_res = utils.make_request_with_retries(search_url)
        search_data = search_res.json()
        stock = next((s for s in search_data.get('data', {}).get('stocks', []) if s.get('ticker') == nse_symbol), None)
        
        if not (stock and stock.get('sid')): 
            return bundle
            
        sid = stock['sid']
        
        # 2. Fetch Info
        api_url = f"https://api.tickertape.in/stocks/info/{sid}"
        api_res = utils.make_request_with_retries(api_url)
        api_data = api_res.json()
        
        if not api_data.get("success", False): 
            return bundle
            
        tt_data = api_data.get("data", {})
        
        # 3. Parse Shareholding
        if holding_data := tt_data.get("holding", {}).get("data"):
            h_map = {"prom": "Promoter", "mf": "Mutual Funds", "dii": "Other Dom. Inst.", "fii": "Foreign Inst.", "ret": "Retail & Others"}
            sh = {h_map.get(i.get("type")): float(i.get("value")) for i in holding_data if i.get("type") in h_map and i.get("value") is not None}
            bundle["shareholding"] = {k: v for k, v in sh.items() if v > 0}
            
        # 4. Parse Ratios
        if ratios := tt_data.get("ratios", {}):
            if r := ratios.get("mcap"): bundle["metrics"]["Market Cap (Cr)"] = r / 1e7
            if r := ratios.get("pe"): bundle["metrics"]["P/E Ratio"] = r
            if r := ratios.get("pb"): bundle["metrics"]["P/B Ratio"] = r
            if r := ratios.get("dy"): bundle["metrics"]["Dividend Yield (%)"] = r
            
        # 5. Sector & Peers & Profile
        if sector_info := tt_data.get("sector"): 
            bundle["sector"] = sector_info.get("sector")
            
        if peers := tt_data.get("peers"):
            bundle["peers"] = {p.get("info", {}).get("ticker"): p.get("ratios", {}).get("pe") for p in peers[:4] if p.get("ratios", {}).get("pe")}
            
        if desc := tt_data.get("profile", {}).get("description"): 
            bundle["profile"] = desc[:800]
            
    except Exception as e: 
        print(f"      - ⚠️ TickerTape Fetch Error: {e}")
        pass
        
    return bundle

def fetch_yfinance_supplemental_details(y_symbol):
    details = {}
    try:
        ticker = yf.Ticker(y_symbol); info = ticker.info
        
        # CEO
        execs = info.get('companyOfficers', [])
        if execs:
            ceo = next((p for p in execs if 'CEO' in p.get('title', '')), execs[0] if execs else None)
            if ceo: details['ceo'] = ceo.get('name')
            
        # Metrics
        if roe := info.get('returnOnEquity'): details['returnOnEquity'] = roe
        if high := info.get('fiftyTwoWeekHigh'): details['52-Wk High'] = high
        if low := info.get('fiftyTwoWeekLow'): details['52-Wk Low'] = low
        if mcap := info.get('marketCap'): details['Market Cap (Cr)'] = mcap / 1e7
        
        # Sector Fallback
        if sector := info.get('sector'): details['sector'] = sector
        elif industry := info.get('industry'): details['sector'] = industry
    except: pass
    return details

def fetch_quarterly_financials(y_symbol):
    try:
        ticker = yf.Ticker(y_symbol); qf = ticker.quarterly_financials
        if not qf.empty:
            latest = qf.iloc[:, 0]
            return {
                "Quarterly Revenue (Cr)": latest.get('Total Revenue', 0) / 1e7, 
                "Quarterly Profit (Cr)": latest.get('Net Income', 0) / 1e7
            }
    except: pass
    return {}

def fetch_price_data(y_symbol):
    try:
        ticker = yf.Ticker(y_symbol); df = ticker.history(period="1y", interval="1d")
        if df.empty: raise ValueError("Empty price data")
        
        # Optional: Index data (can be removed if not strictly needed by deepdive, 
        # but kept for index comparison charts)
        try:
            index_ticker = yf.Ticker("^NSEI")
            df_index = index_ticker.history(period="1y", interval="1d")
        except:
            df_index = None
            
        return df, df_index
    except: return None, None

def compute_price_snapshot(df):
    if df is None or len(df) < 2: return {"last_close": 0, "d_pct": 0, "d5_pct": 0}
    last, prev = df.iloc[-1], df.iloc[-2]
    d_pct = (last["Close"] / prev["Close"] - 1) * 100
    
    prev5 = df.iloc[-6] if len(df) >= 6 else prev
    d5_pct = (last["Close"] / prev5["Close"] - 1) * 100
    
    return {"last_close": last["Close"], "d_pct": d_pct, "d5_pct": d5_pct}


def fetch_price_data_with_technicals(y_symbol):
    """
    Fetches 1 year history and calculates SMA 50/200 and RSI 14.
    """
    try:
        ticker = yf.Ticker(y_symbol)
        # Fetch 2 years to ensure we have enough data for SMA 200
        df = ticker.history(period="2y", interval="1d")
        
        if df.empty: return None, None

        # 1. SMA Calculation
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()

        # 2. RSI Calculation (14-day)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # 3. Trend Signal
        current_close = df['Close'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1]
        sma_200 = df['SMA_200'].iloc[-1]
        rsi = df['RSI'].iloc[-1]

        signals = {
            "price": current_close,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi": rsi,
            "trend": "Bullish" if current_close > sma_50 else "Bearish",
            "crossover": "Golden" if sma_50 > sma_200 else "Death" if sma_50 < sma_200 else "Neutral"
        }

        return df, signals
    except Exception as e:
        print(f"      - ⚠️ Technicals Error: {e}")
        return None, None

def fetch_3yr_fundamentals(y_symbol):
    """
    Extracts Sales, PAT, EPS, Debt for last 3 years from YFinance.
    """
    data = {"years": [], "sales": [], "pat": [], "debt": [], "eps": [], "roe": "N/A"}
    try:
        ticker = yf.Ticker(y_symbol)
        
        # 1. Income Statement (Sales, PAT, EPS)
        fin = ticker.financials
        if not fin.empty:
            # Get last 3 columns (years)
            cols = fin.columns[:3]
            data["years"] = [c.strftime('%Y') for c in cols]
            
            # Sales (Total Revenue)
            if 'Total Revenue' in fin.index:
                data["sales"] = [fin.loc['Total Revenue', c] / 1e7 for c in cols] # Convert to Cr
            
            # PAT (Net Income)
            if 'Net Income' in fin.index:
                data["pat"] = [fin.loc['Net Income', c] / 1e7 for c in cols] # Convert to Cr
                
            # Basic EPS
            if 'Basic EPS' in fin.index:
                data["eps"] = [fin.loc['Basic EPS', c] for c in cols]

        # 2. Balance Sheet (Debt)
        bs = ticker.balance_sheet
        if not bs.empty:
            cols = bs.columns[:3]
            if 'Total Debt' in bs.index:
                data["debt"] = [bs.loc['Total Debt', c] / 1e7 for c in cols] # Convert to Cr

        # 3. Ratios (ROE/ROCE fallback)
        info = ticker.info
        data['roe'] = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else "N/A"
        data['debt_to_equity'] = info.get('debtToEquity', "N/A")
        
        return data
    except Exception as e:
        print(f"      - ⚠️ Fundamentals Error: {e}")
        return data