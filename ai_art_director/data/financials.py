# ai_art_director/data/financials.py
# v25.7.1 - RESTORED FULL LOGIC (TickerTape + YF + Price)

import yfinance as yf
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