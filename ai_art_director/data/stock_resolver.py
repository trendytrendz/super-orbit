#ai_art_director/data/stock_resolver.py
import os
import json
import time
import pandas as pd
from difflib import SequenceMatcher
from urllib.parse import quote_plus
from .. import utils, config

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
        print(f"   -> Found '{query_key}' in cache.")
        c = cache[query_key]
        return c['nse'], c['yahoo'], c['display']
    
    print(f"   -> Resolving '{query_key}' (Live)...")
    
    # 1. Try Local NSE List
    nse_file = 'nse_symbols.csv'
    if not os.path.exists(nse_file) or (time.time() - os.path.getmtime(nse_file)) > 604800: # 7 days
        _update_nse_symbol_list(nse_file)
        
    match = _resolve_from_local_list(query, nse_file)
    if match is not None:
        nse, disp, y_sym = match['SYMBOL'], match['NAME OF COMPANY'], f"{match['SYMBOL']}.NS"
        cache[query_key] = {'nse': nse, 'yahoo': y_sym, 'display': disp}
        save_cache(cache)
        return nse, y_sym, disp

    # 2. Fallback to Yahoo API
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote_plus(query)}"
        r = utils.make_request_with_retries(url, timeout=10)
        data = r.json().get('quotes', [])
        # Prioritize NSE/BSE
        picks = [q for q in data if ".NS" in q.get('symbol', '')] or data
        if picks:
            best = picks[0]
            nse = best['symbol'].replace(".NS", "")
            y_sym = best['symbol']
            disp = best.get("longname") or best.get("shortname") or nse
            cache[query_key] = {'nse': nse, 'yahoo': y_sym, 'display': disp}
            save_cache(cache)
            return nse, y_sym, disp
    except Exception as e:
        print(f"      - Yahoo Search failed: {e}")

    raise ValueError(f"Could not resolve symbol for '{query}'")

def update_nse_symbol_list(file_path):  # <--- WAS _update_nse_symbol_list
    try:
        url = 'https://archives.nseindia.com/content/equities/EQUITY_L.csv'
        r = utils.make_request_with_retries(url)
        with open(file_path, 'wb') as f: f.write(r.content)
    except: pass
    
def _resolve_from_local_list(query, file_path):
    try:
        df = pd.read_csv(file_path); df.columns = df.columns.str.strip()
        q_lower = query.lower()
        best, highest = None, 0.0
        for _, row in df.iterrows():
            sym = str(row['SYMBOL']).lower(); name = str(row['NAME OF COMPANY']).lower()
            # Scoring: Exact symbol match > Name contains > Fuzzy
            if sym == q_lower: return row 
            
            score = max(SequenceMatcher(None, q_lower, sym).ratio(), SequenceMatcher(None, q_lower, name).ratio() * 0.9)
            if q_lower in name: score = max(score, 0.85)
            
            if score > highest: highest, best = score, row
        return best if highest > 0.6 else None
    except: return None
