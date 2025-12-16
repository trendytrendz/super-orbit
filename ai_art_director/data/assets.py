# ai_art_director/data/assets.py
# v25.7.2 - Aggressive Logo Fetching

import os
import requests
import time
from io import BytesIO
from PIL import Image
from .. import config

def fetch_company_logo(y_symbol):
    """
    Robust logo fetcher. 
    Priority: Local -> Clearbit -> Google Favicon -> Placeholder
    """
    clean_ticker = y_symbol.replace('.NS', '').replace('.BO', '').lower()
    
    # 1. Local Override (Manual)
    local_files = [
        f"{clean_ticker}_logo.png", f"{clean_ticker}.png",
        f"{clean_ticker}_logo.jpg", f"{clean_ticker}.jpg"
    ]
    
    for fname in local_files:
        local_path = config.ASSETS_DIR / "Logo" / fname
        if local_path.exists():
            try:
                print(f"      - 🛡️ Found Manual Local Logo: {fname}")
                return Image.open(str(local_path)).convert("RGBA")
            except: pass

    # 2. Try Online Sources
    domain_guess = f"{clean_ticker}.com"
    
    # Optimization: Known domains map (expandable)
    known_domains = {
        'hdfcbank': 'hdfcbank.com',
        'icicibank': 'icicibank.com',
        'sbin': 'sbi.co.in',
        'tatamotors': 'tatamotors.com',
        'reliance': 'ril.com',
        'infosys': 'infosys.com'
    }
    
    domain = known_domains.get(clean_ticker, domain_guess)
    
    # Attempt 1: Clearbit
    try:
        url = f"https://logo.clearbit.com/{domain}?size=200"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            print(f"      - ✅ Logo fetched (Clearbit): {domain}")
            return Image.open(BytesIO(r.content)).convert("RGBA")
    except: pass

    # Attempt 2: Google Favicon (High Res)
    try:
        url = f"https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=256"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
             print(f"      - ✅ Logo fetched (Google): {domain}")
             return Image.open(BytesIO(r.content)).convert("RGBA")
    except: pass
    
    print(f"      - ❌ Logo not found for {clean_ticker}")
    return None