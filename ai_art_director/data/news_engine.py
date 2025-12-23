# ai_art_director/data/news_engine.py
# v26.4.0 - Dynamic Limit & Backfill Logic

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

# --- 1. Yahoo Finance ---
def fetch_yfinance_news(y_symbol):
    print(f"   -> 📡 Fetching Yahoo Finance news for {y_symbol}...")
    try:
        ticker = yf.Ticker(y_symbol); news = ticker.news; items = []; now = utils.now_ist()
        print(f"      - [Yahoo] Raw Items Found: {len(news)}")
        
        for item in news:
            try:
                pub_ts = item.get('provider_publish_time')
                if not pub_ts: continue 
                published = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                if (now - published).days <= config.LOOKBACK_NEWS_DAYS:
                    img = item.get('thumbnail', {}).get('originalUrl')
                    title = item['title'].strip()
                    items.append({
                        "title": title, "link": item['link'], 
                        "published": published, "source": "Yahoo Finance", "image": img
                    })
                    print(f"      - [Yahoo] ✅ Accepted: {title[:50]}...")
            except: continue
        return items
    except Exception as e: 
        print(f"      - ⚠️ Yahoo fetch error: {e}"); return []

# --- 2. Google News ---
def fetch_google_news(name, symbol, days=7):
    print(f"   -> 📡 Fetching Google News for {name}...")
    items = []; now = utils.now_ist(); q = f'"{name}" OR {symbol} when:{days}d'
    try:
        feed_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(feed_url)
        print(f"      - [Google] Raw Items Found: {len(feed.entries)}")
        
        for e in feed.entries:
            try:
                published = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
                if (now - published).days <= days: 
                    title_full = e.title.strip(); source_name = "Google News"
                    if " - " in title_full:
                        parts = title_full.rsplit(" - ", 1); title_clean = parts[0]; source_name = parts[1]
                    else: title_clean = title_full
                    items.append({
                        "title": title_clean, "link": e.link, 
                        "published": published, "source": source_name, "image": None
                    })
                    print(f"      - [Google] ✅ Accepted: {title_clean[:50]}...")
            except: continue
    except Exception as e: print(f"      - ⚠️ Google fetch error: {e}")
    return items

# --- 3. MoneyControl ---
def fetch_moneycontrol_news(query):
    print(f"   -> 📡 Fetching MoneyControl News for {query}...")
    items = []
    try:
        s_query = query.replace(' Ltd', '').replace(' Limited', '').replace('&', '').replace(' ', '-').lower()
        url = f"https://www.moneycontrol.com/news/tags/{s_query}.html"
        r = utils.make_request_with_retries(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        links = soup.select("#cagetory a")[:20]
        print(f"      - [MoneyControl] Raw Items Found: {len(links)}")
        
        for link_tag in links:
            try:
                h2 = link_tag.find('h2'); title = h2.get_text(strip=True) if h2 else link_tag.get('title')
                if not title or title.lower() in ["remove ad", "pro", "moneycontrol", "personal finance"]: continue
                href = link_tag.get('href')
                if not href: continue
                img = link_tag.find('img')
                image_url = img.get('data') or img.get('data-src') or img.get('src') if img else None
                if image_url and "200x200" in image_url: image_url = image_url.replace("200x200", "600x600")
                
                pub_date = utils.now_ist()
                date_span = link_tag.find('span')
                if date_span:
                    clean_str = date_span.get_text(strip=True).replace(" IST", "").strip()
                    try: pub_date = datetime.strptime(clean_str, "%B %d, %Y %I:%M %p").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                    except: pass
                
                items.append({
                    "title": title.strip(), "link": href, 
                    "published": pub_date, "source": "MoneyControl", "image": image_url
                })
                print(f"      - [MoneyControl] ✅ Accepted: {title[:50]}...")
            except: continue
    except Exception as e: print(f"      - ⚠️ MoneyControl fetch error: {e}")
    return items

# --- 4. Economic Times ---
def fetch_economic_times_news(query):
    print(f"   -> 📡 Fetching Economic Times (RSS) for {query}...")
    items = []
    try:
        rss_url = "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"
        feed = feedparser.parse(rss_url)
        print(f"      - [ET RSS] Raw Items Found: {len(feed.entries)}")
        
        query_parts = query.lower().split(); main_keyword = query_parts[0] if query_parts else query.lower() 
        for e in feed.entries:
            try:
                title = e.title.strip()
                if main_keyword in title.lower():
                    image_url = e.enclosures[0].get('href') if hasattr(e, 'enclosures') and e.enclosures else None
                    pub_date = utils.now_ist()
                    if hasattr(e, 'published_parsed') and e.published_parsed:
                        try: pub_date = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
                        except: pass
                    items.append({
                        "title": title, "link": e.link, "published": pub_date, "source": "Economic Times", "image": image_url
                    })
                    print(f"      - [ET] ✅ Accepted: {title[:50]}...")
            except: continue
    except Exception as e: print(f"      - ⚠️ ET fetch error: {e}")
    return items

# --- RANKING LOGIC (UPDATED) ---

def score_news_relevance(headline, company_name, source):
    # (Helper unchanged)
    score = 0; hl = headline.lower(); cn = company_name.lower().split()[0]
    if hl.startswith(cn): score += 30
    elif cn in hl: score += 10
    for keyword in config.IMPACT_KEYWORDS:
        if keyword in hl: score += 15
    score += config.SOURCE_BONUS.get(source, 0)
    return score

def rank_news_with_llm(news_list, company_name, limit=2):
    """
    Rank news using LLM + Backfill Strategy.
    limit: Number of stories required (default 2).
    """
    if not news_list: return []

    # 1. Sort by Recency
    news_list.sort(key=lambda x: x['published'], reverse=True)

    # 2. Pre-Dedupe
    candidates = []
    seen_titles = set()
    print(f"   -> 🧹 Pre-filtering {len(news_list)} raw items...")
    
    for item in news_list:
        clean_t = item['title'].lower().strip()
        if clean_t not in seen_titles:
            candidates.append(item)
            seen_titles.add(clean_t)
    
    # Context Size: 25 items
    candidates = candidates[:25]
    print(f"\n   🧠 [LLM Judge] Assessing {len(candidates)} distinct headlines for '{company_name}' (Target: {limit})...")
    
    for i, item in enumerate(candidates):
        print(f"      [{i}] {item['source']}: {item['title'][:60]}...")

    # Ask for more than limit to have a buffer
    req_count = limit + 3
    
    prompt_text = f"""
    Role: Financial News Analyst. 
    Task: Select top {req_count} most impactful stories for stock '{company_name}'.
    
    CRITICAL RULES:
    1. IGNORE duplicate events.
    2. PRIORITIZE: Earnings, Dividends, Contracts, Regulatory Action, Stock Surge/Drop.
    
    HEADLINES:
    {chr(10).join([f"{i}. {item['title']} (Source: {item['source']})" for i, item in enumerate(candidates)])}
    
    OUTPUT:
    Return JSON list of indices only: [0, 2, 5]
    """
    
    selected_news = []
    
    try:
        response = utils.query_local_llm(prompt_text, max_words=20, temperature=0.1)
        print(f"      - 🗣️ LLM Raw Response: {response}")
        
        indices = [int(n) for n in re.findall(r'\d+', response)]
        valid_indices = []
        seen_idx = set()
        
        # Preserve LLM order
        for ix in indices:
            if 0 <= ix < len(candidates) and ix not in seen_idx:
                valid_indices.append(ix)
                seen_idx.add(ix)
        
        print(f"      - 🕵️ Deduplication Check (Threshold 70%)...")
        
        # --- PASS 1: LLM Choices ---
        for idx in valid_indices:
            if len(selected_news) >= limit: break
            
            candidate_item = candidates[idx]
            if not _is_duplicate(candidate_item, selected_news):
                selected_news.append(candidate_item)
                print(f"        ✅ LLM Pick Accepted (#{idx}): {candidate_item['title'][:60]}...")

        # --- PASS 2: Backfill (If LLM picked duplicates) ---
        if len(selected_news) < limit:
            needed = limit - len(selected_news)
            print(f"      - ⚠️ Need {needed} more stories. Backfilling from Recency...")
            
            for i, item in enumerate(candidates):
                if len(selected_news) >= limit: break
                
                # Skip if already selected (by checking object identity or title)
                if any(s['title'] == item['title'] for s in selected_news): continue
                
                if not _is_duplicate(item, selected_news):
                    selected_news.append(item)
                    print(f"        ✅ Backfill Accepted (#{i}): {item['title'][:60]}...")

        return selected_news

    except Exception as e:
        print(f"      - ⚠️ LLM Ranking Failed: {e}")
        return candidates[:limit]

def _is_duplicate(candidate, selected_list):
    """Helper to check 70% similarity against list"""
    for existing in selected_list:
        sim = SequenceMatcher(None, candidate['title'].lower(), existing['title'].lower()).ratio()
        if sim > 0.70:
            print(f"        ✂️  Duplicate Rejected (Sim: {sim:.2f})")
            print(f"             Reject: {candidate['title'][:40]}...")
            print(f"             Keep:   {existing['title'][:40]}...")
            return True
    return False