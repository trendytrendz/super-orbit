# ai_art_director/data/news_engine.py
# v25.7.3 - Strict Deduplication (70%) & Enhanced Logging

import time
import feedparser
import requests
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
import yfinance as yf
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from .. import utils, config

# --- FETCHERS (unchanged from previous restoration) ---
# [Keep fetch_yfinance_news, fetch_google_news, fetch_moneycontrol_news, fetch_economic_times_news as they were]
# I will include them briefly to ensure the file is complete.

def fetch_yfinance_news(y_symbol):
    # ... (Standard Yahoo Fetcher)
    print(f"   -> 📡 Fetching Yahoo Finance news for {y_symbol}...")
    try:
        ticker = yf.Ticker(y_symbol); news = ticker.news; items = []; now = utils.now_ist()
        for item in news:
            try:
                pub_ts = item.get('provider_publish_time')
                if not pub_ts: continue 
                published = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                if (now - published).days <= config.LOOKBACK_NEWS_DAYS:
                    img = item.get('thumbnail', {}).get('originalUrl')
                    items.append({"title": item['title'].strip(), "link": item['link'], "published": published, "source": "Yahoo Finance", "image": img})
            except: continue
        return items
    except: return []

def fetch_google_news(name, symbol, days=7):
    # ... (Standard Google Fetcher)
    print(f"   -> 📡 Fetching Google News for {name}...")
    items = []; now = utils.now_ist(); q = f'"{name}" OR {symbol} when:{days}d'
    try:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        for e in feed.entries:
            try:
                dt = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
                if (now - dt).days <= days:
                    title = e.title.rsplit(" - ", 1)[0] if " - " in e.title else e.title
                    items.append({"title": title.strip(), "link": e.link, "published": dt, "source": "Google News", "image": None})
            except: continue
    except: pass
    return items

def fetch_moneycontrol_news(query):
    # ... (Standard MC Fetcher with "Remove Ad" fix)
    print(f"   -> 📡 Fetching MoneyControl News for {query}...")
    items = []
    try:
        s_query = query.replace(' Ltd', '').replace(' Limited', '').replace('&', '').replace(' ', '-').lower()
        url = f"https://www.moneycontrol.com/news/tags/{s_query}.html"
        r = utils.make_request_with_retries(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        for link in soup.select("#cagetory a")[:20]:
            try:
                h2 = link.find('h2'); title = h2.get_text(strip=True) if h2 else link.get('title')
                if not title or title.lower() in ["remove ad", "pro", "moneycontrol", "personal finance"]: continue
                
                img = link.find('img')
                img_url = img.get('data') or img.get('data-src') or img.get('src') if img else None
                # Enhancement: Upgrade thumbnail to larger image if possible
                if img_url and "200x200" in img_url: img_url = img_url.replace("200x200", "600x600")

                pub_date = utils.now_ist()
                date_span = link.find('span')
                if date_span:
                    clean = date_span.get_text(strip=True).replace(" IST", "").strip()
                    try: pub_date = datetime.strptime(clean, "%B %d, %Y %I:%M %p").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                    except: pass
                
                items.append({"title": title.strip(), "link": link.get('href'), "published": pub_date, "source": "MoneyControl", "image": img_url})
            except: continue
    except: pass
    return items

def fetch_economic_times_news(query):
    # ... (Standard ET Fetcher)
    print(f"   -> 📡 Fetching Economic Times (RSS) for {query}...")
    items = []
    try:
        url = "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"
        feed = feedparser.parse(url)
        qp = query.lower().split()[0]
        for e in feed.entries:
            if qp in e.title.lower():
                img = e.enclosures[0].get('href') if hasattr(e, 'enclosures') and e.enclosures else None
                dt = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc) if hasattr(e, 'published_parsed') else utils.now_ist()
                items.append({"title": e.title.strip(), "link": e.link, "published": dt, "source": "Economic Times", "image": img})
    except: pass
    return items

# --- LOGIC UPDATE STARTS HERE ---

def score_news_relevance(headline, company_name, source):
    # (Helper used by single news story, kept for compatibility)
    score = 0; hl = headline.lower(); cn = company_name.lower().split()[0]
    if hl.startswith(cn): score += 30
    elif cn in hl: score += 10
    for k in config.IMPACT_KEYWORDS:
        if k in hl: score += 15
    score += config.SOURCE_BONUS.get(source, 0)
    return score

def rank_news_with_llm(news_list, company_name):
    """
    1. Sort by Recency.
    2. Exact Dedupe.
    3. LLM Pick (Top 3).
    4. Fuzzy Dedupe (70% Similarity).
    5. Return Top 2.
    """
    if not news_list: return []

    # 1. Sort by Recency (Newest First)
    news_list.sort(key=lambda x: x['published'], reverse=True)

    # 2. Pre-Dedupe (Exact Match) - Keep newest version
    candidates = []
    seen_titles = set()
    print(f"   -> 🧹 Pre-filtering {len(news_list)} items...")
    
    for item in news_list:
        clean_t = item['title'].lower().strip()
        if clean_t not in seen_titles:
            candidates.append(item)
            seen_titles.add(clean_t)
    
    # Limit to 12 for LLM context
    candidates = candidates[:12]
    
    print(f"\n   🧠 [LLM Judge] Assessing {len(candidates)} distinct headlines for '{company_name}'...")
    
    prompt_text = f"""
    Role: Financial News Editor. 
    Task: Select top 3 most impactful stories for stock '{company_name}'.
    
    CRITICAL RULES:
    1. IGNORE duplicate events (e.g. same earnings report from different sources).
    2. IGNORE generic advice ("Should you buy?").
    3. PRIORITIZE: Earnings, Dividends, Contracts, Regulatory Action, Stock Surge/Drop.
    
    HEADLINES:
    {chr(10).join([f"{i}. {item['title']} (Source: {item['source']})" for i, item in enumerate(candidates)])}
    
    OUTPUT:
    Return JSON list of indices only: [0, 2, 5]
    """
    
    try:
        response = utils.query_local_llm(prompt_text, max_words=20, temperature=0.1)
        print(f"      - LLM Raw Response: {response}")
        
        # Extract indices
        indices = [int(n) for n in re.findall(r'\d+', response)]
        valid_indices = [ix for ix in indices if 0 <= ix < len(candidates)]
        
        # 3. Post-Dedupe (Fuzzy Logic - 70% Threshold)
        selected_news = []
        
        for idx in valid_indices:
            candidate_item = candidates[idx]
            
            is_duplicate = False
            for existing in selected_news:
                # Calculate similarity ratio
                sim = SequenceMatcher(None, candidate_item['title'].lower(), existing['title'].lower()).ratio()
                
                if sim > 0.70: # User requested 70% threshold
                    print(f"      - ✂️  Duplicate Rejected (Similarity {sim:.2f}):")
                    print(f"           Reject: {candidate_item['title'][:50]}...")
                    print(f"           Keep:   {existing['title'][:50]}...")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                selected_news.append(candidate_item)
                print(f"      - ✅ Accepted Story #{len(selected_news)}: {candidate_item['title'][:60]}...")
                
            if len(selected_news) >= 2: # We only need top 2
                break
        
        # Fallback: If LLM failed to give us 2 distinct stories, fill with Recency
        if len(selected_news) < 1:
            print("      - ⚠️ LLM picked nothing/duplicates. Filling with recency.")
            return candidates[:2]
            
        return selected_news

    except Exception as e:
        print(f"      - ⚠️ LLM Ranking Failed: {e}")
        return candidates[:2]