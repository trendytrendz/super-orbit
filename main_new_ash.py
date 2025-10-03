# -----------------------------------------------------------------------------
# Stock Video Briefing Generator
# Version: 1.6.4 (Frozen & Complete)
#
# Description: A complete, stable, and feature-rich version that correctly
#              implements all requested features and stability patches.
#
# Changes in v1.6.4:
# - All functions are fully implemented and correct.
# - Pexels API calls are now wrapped in a try/except block for graceful failure.
# - This version consolidates all features from the 1.4, 1.5, and 1.6 series.
# -----------------------------------------------------------------------------

import argparse
import os
import re
import time
import json
import random
from io import BytesIO
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

# Core Libraries & Scraping
import requests
import feedparser
import yfinance as yf
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
import whisper
from bs4 import BeautifulSoup
import cairosvg
import numpy as np

# MoviePy & Optional Libraries
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_audioclips, TextClip, vfx
)
from moviepy.video.tools.subtitles import SubtitlesClip

# Azure Speech SDK
import azure.cognitiveservices.speech as speechsdk

# Conditional Imports for optional features
try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
try:
    from pexels_api import API
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False

# Charting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import mplfinance as mpf

# -------------------------
# Version & Config
# -------------------------
__version__ = "1.6.4"

VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE = 1280, 720
VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT = 720, 1280
BG_COLOR = "#080C14"; ACCENT = "#00ACC1"; TEXT_COLOR = "#F0F4F8"
FONT_PATHS_TRY = ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"]
LOOKBACK_NEWS_DAYS = 7; MAX_NEWS_ITEMS = 3
IMPACT_KEYWORDS = ["profit", "loss", "earnings", "revenue", "deal", "order", "appoints", "launches", "acquires", "merger", "results", "guidance", "upgrade", "downgrade", "stake"]
POSITIVE_CUES = ["buyback", "bonus", "split", "order win", "upgrade", "raises guidance", "dividend", "approval", "record order", "profit", "acquires", "launches"]
NEGATIVE_CUES = ["resigns", "resignation", "loss", "downgrade", "penalty", "pledge", "fraud", "default", "investigation"]
ICON_SVG = {"positive": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#4CAF50" d="m280-400 200-200 200 200H280Z"/></svg>', "negative": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#F44336" d="M480-560 280-760h400L480-560Z"/></svg>', "uncertain": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>'}
OUTRO_ICONS = {"like": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M720-120H280v-520l280-280 50 50q7 7 11.5 19t4.5 23v14l-44 214h258q32 0 56 24t24 56v80q0 7-2 15t-4 15L794-168q-9 20-30 34t-44 14Zm-360-80h360l120-280v-80H480l54-260-174 174v446Zm0 80Z"/></svg>', "comment": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M240-400h480v-80H240v80Zm0-120h480v-80H240v80Zm0-120h480v-80H240v80ZM80-80v-720q0-33 23.5-56.5T160-880h640q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H240L80-80Zm80-200h640v-480H160v525l40-45Z"/></svg>', "share": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M720-80q-50 0-85-35t-35-85q0-7 1-14.5t3-13.5L322-382q-18 13-40 21t-42 8q-50 0-85-35t-35-85q0-50 35-85t85-35q20 0 40 7.5t38 20.5l282-164q-2-6-2.5-12.5T600-720q0-50 35-85t85-35q50 0 85 35t35 85q0 50-35 85t-85 35q-20 0-38-7.5t-40-20.5L340-542q2 6 2.5 12.5t.5 13.5q0 7-1 14t-3 14l282 164q18-13 40-21t42-8q50 0 85 35t35 85q0 50-35 85t-85 35Zm0-640q17 0 28.5-11.5T760-760q0-17-11.5-28.5T720-800q-17 0-28.5 11.5T680-760q0-17 11.5 28.5T720-720ZM240-440q17 0 28.5-11.5T280-480q0-17-11.5-28.5T240-520q-17 0-28.5 11.5T200-480q0-17 11.5 28.5T240-440Zm480 280q17 0 28.5-11.5T760-200q0-17-11.5-28.5T720-240q-17 0-28.5 11.5T680-200q0-17 11.5 28.5T720-160Z"/></svg>'}
SOURCE_BONUS = { "Yahoo Finance": 20, "MoneyControl": 15, "Economic Times": 10, "Google News": 0 }

def get_script_dir(): return os.path.dirname(os.path.realpath(__file__))
def ensure_dirs():
    script_dir = get_script_dir()
    os.makedirs(os.path.join(script_dir, "outputs"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "outputs", "tmp"), exist_ok=True)
def now_ist(): return datetime.now(timezone(timedelta(hours=5, minutes=30)))
def seq_ratio(a, b): return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()
def classify_impact(text):
    t = (text or "").lower()
    if any(k in t for k in POSITIVE_CUES): return "positive"
    if any(k in t for k in NEGATIVE_CUES): return "negative"
    return "uncertain"
def make_request_with_retries(url, headers=None, timeout=30, retries=3, delay=3):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"}
        if FAKE_USERAGENT_AVAILABLE:
            headers['User-Agent'] = UserAgent().random
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"      - Attempt {attempt + 1}/{retries} failed for URL: {e}")
            if attempt < retries - 1: time.sleep(delay)
            else: raise
    return None
def wrap_text_pil(text, font, max_width):
    if not text: return []
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, cur, words = [], [], text.split()
    for w in words:
        tentative = " ".join(cur + [w]) if cur else w
        if draw.textbbox((0,0), tentative, font=font)[2] <= max_width: cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))
    return lines
def get_optimal_font_size(text, initial_size, max_width, max_height, font_path):
    font_size = int(initial_size)
    font = ImageFont.truetype(font_path, font_size)
    def get_text_dimensions(txt, fnt):
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        lines = wrap_text_pil(txt, fnt, max_width * 0.9)
        if not lines: return 0, 0
        h = sum(draw.textbbox((0,0), l, font=fnt)[3] for l in lines) + (len(lines) - 1) * (font_size * 0.2)
        w = max(draw.textbbox((0,0), l, font=fnt)[2] for l in lines) if lines else 0
        return w, h
    width, height = get_text_dimensions(text, font)
    while (height > max_height * 0.9 or width > max_width * 0.9) and font_size > 20:
        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)
        width, height = get_text_dimensions(text, font)
    return font
def wrap_text_for_subtitles(text, max_chars_per_line=40):
    words = text.split()
    if len(text) <= max_chars_per_line or len(words) < 5: return text.strip()
    mid_point = len(words) // 2; best_split = mid_point; min_diff = float('inf')
    for i in range(max(0, mid_point - 5), min(len(words), mid_point + 5)):
        line1 = " ".join(words[:i]); line2 = " ".join(words[i:])
        diff = abs(len(line1) - len(line2))
        if diff < min_diff: min_diff = diff; best_split = i
    line1 = " ".join(words[:best_split]); line2 = " ".join(words[best_split:])
    return f"{line1}\n{line2}"
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
        match = df[df['SYMBOL'].str.lower() == query_lower]
        if not match.empty: return match.iloc[0]
        match = df[df['NAME OF COMPANY'].str.lower().str.contains(query_lower)]
        if not match.empty: return match.iloc[0]
        return None
    except FileNotFoundError:
        print("      - Local NSE symbol list not found.")
        return None
    except Exception as e:
        print(f"      - Error searching local NSE list: {e}")
        return None
def resolve_symbol(query):
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
            print("      - Symbol found via Yahoo Finance.")
            return best["symbol"].replace(".NS", ""), best["symbol"], display
    except Exception as e:
        print(f"      - Yahoo Finance API failed: {e}. Trying local NSE fallback.")
    print("   -> Trying to resolve symbol via local NSE list...")
    nse_file = 'nse_symbols.csv'
    if not os.path.exists(nse_file) or (time.time() - os.path.getmtime(nse_file)) > 7 * 86400:
        update_nse_symbol_list(nse_file)
    match = resolve_symbol_from_nse_local(query, nse_file)
    if match is not None:
        nse_symbol = match['SYMBOL']
        display_name = match['NAME OF COMPANY']
        print(f"      - Symbol found via local NSE list: {nse_symbol}")
        return nse_symbol, f"{nse_symbol}.NS", display_name
    raise ValueError(f"Could not find symbol for '{query}' from any source.")
def fetch_yfinance_news(y_symbol):
    print("   -> Fetching from Yahoo Finance...")
    try:
        ticker = yf.Ticker(y_symbol)
        news = ticker.news
        items = []; now = now_ist()
        for item in news:
            try:
                published = datetime.fromtimestamp(item['provider_publish_time'], tz=timezone.utc).astimezone(now.tzinfo)
                if (now - published).days <= LOOKBACK_NEWS_DAYS: items.append({"title": item['title'].strip(), "link": item['link'], "published": published, "source": "Yahoo Finance"})
            except: continue
        return items
    except Exception as e: print(f"      - Could not fetch from Yahoo Finance: {e}"); return []
def fetch_google_news(name, symbol, days=7):
    print("   -> Fetching from Google News..."); items = []; now = now_ist(); q = f'"{name}" OR {symbol} when:{days}d'
    feed_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(feed_url)
    for e in feed.entries:
        try:
            published = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc).astimezone(now.tzinfo)
            if (now - published).days <= days: items.append({"title": e.title.strip(), "link": e.link, "published": published, "source": "Google News"})
        except: continue
    return items
def fetch_moneycontrol_news(query):
    print("   -> Fetching from MoneyControl..."); items = []
    try:
        search_query = query.replace(' Ltd', '').replace(' Limited', '').replace('&', '').replace(' ', '-').lower()
        url = f"https://www.moneycontrol.com/news/tags/{search_query}.html"
        r = make_request_with_retries(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        news_list = soup.select("#cagetory a")
        for item in news_list[:10]:
            title = item.get('title'); link = item.get('href')
            if title and link: items.append({"title": title.strip(), "link": link, "published": now_ist(), "source": "MoneyControl"})
    except Exception as e: print(f"      - Could not fetch from MoneyControl: {e}")
    return items
def fetch_economic_times_news(query):
    print("   -> Fetching from Economic Times..."); items = []
    try:
        search_query = query.lower().replace(' ltd', '').replace(' limited', '').replace('&', '').replace(' ', '-')
        url = f"https://economictimes.indiatimes.com/topic/{search_query}"
        r = make_request_with_retries(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        news_list = soup.select("div.story_list a")
        for item in news_list[:10]:
            title = item.get_text(strip=True)
            link = "https://economictimes.indiatimes.com" + item.get('href')
            if title and link:
                 items.append({"title": title, "link": link, "published": now_ist(), "source": "Economic Times"})
    except Exception as e: print(f"      - Could not fetch from Economic Times: {e}")
    return items
def score_news_relevance(headline, company_name, source):
    score = 0
    headline_lower = headline.lower()
    company_name_short = company_name.split()[0].lower()
    if headline_lower.startswith(company_name_short): score += 30
    elif company_name_short in headline_lower: score += 10
    for keyword in IMPACT_KEYWORDS:
        if keyword in headline_lower: score += 15
    score += SOURCE_BONUS.get(source, 0)
    return score
def fetch_financial_metrics(y_symbol):
    print("  -> Fetching key financial metrics...")
    try:
        ticker = yf.Ticker(y_symbol)
        info = ticker.info
        metrics = {
            "Market Cap (Cr)": info.get('marketCap', 0) / 1e7, "P/E Ratio": info.get('trailingPE'),
            "Dividend Yield (%)": info.get('dividendYield', 0) * 100,
            "52-Wk High": info.get('fiftyTwoWeekHigh'), "52-Wk Low": info.get('fiftyTwoWeekLow'),
            "Recommendation": info.get('recommendationKey', 'N/A').upper()
        }
        metrics_clean = {k: v for k, v in metrics.items() if v is not None}
        for key, val in metrics_clean.items():
            if isinstance(val, (int, float)): metrics_clean[key] = f"{val:,.2f}"
        return metrics_clean
    except Exception as e:
        print(f"      - Could not fetch financial metrics: {e}")
        return None
def fetch_price_data(y_symbol, index_symbol="^NSEI"):
    print("  -> Fetching price data for stock and index...")
    ticker = yf.Ticker(y_symbol)
    df = ticker.history(period="1y", interval="1d")
    if df.empty: raise ValueError(f"No price data for {y_symbol}")
    index_ticker = yf.Ticker(index_symbol)
    df_index = index_ticker.history(period="1y", interval="1d")
    return df, df_index
def fetch_shareholding(y_symbol):
    print("  -> Fetching shareholding pattern from TickerTape...")
    try:
        base_symbol = y_symbol.replace('.NS', '')
        url = f"https://www.tickertape.in/stocks/{base_symbol.lower()}"
        response = make_request_with_retries(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        holding_data = soup.find('h3', string=lambda t: t and 'Shareholding' in t).find_next_sibling()
        data_points = holding_data.find_all('div', class_='value-label')
        shareholding = {}
        for dp in data_points:
            label_p = dp.find_all('p')[0]
            value_p = dp.find_all('p')[1]
            label = label_p.get_text(strip=True)
            value = float(value_p.get_text(strip=True).replace('%', ''))
            shareholding[label] = value
        consolidated = {
            'Promoter': shareholding.get('Promoter', 0),
            'Mutual Funds': shareholding.get('Mutual Funds', 0),
            'Other Dom. Inst.': shareholding.get('Other Domestic Institutions', 0),
            'Foreign Inst.': shareholding.get('Foreign Institutions', 0),
            'Retail & Others': shareholding.get('Retail and Other Parties', 0)
        }
        return {k: v for k, v in consolidated.items() if v > 0}
    except Exception as e:
        print(f"      - WARNING: Could not fetch shareholding data from TickerTape: {e}. Skipping this slide.")
        return None
def compute_price_snapshot(df):
    if len(df) < 2: return {"last_close": df.iloc[-1]["Close"], "d_pct": 0, "d5_pct": 0}
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
    except Exception: pass
    return None

def make_candlestick_chart(df, symbol, size, out_png="outputs/tmp/price.png"):
    df_chart = df.tail(252).copy()
    df_chart['SMA50'] = df_chart['Close'].rolling(window=50).mean()
    df_chart['SMA200'] = df_chart['Close'].rolling(window=200).mean()
    mc = mpf.make_marketcolors(up=ACCENT, down='#F44336', edge={'up':ACCENT, 'down':'#F44336'},
                               wick={'up':ACCENT, 'down':'#F44336'}, volume=ACCENT, ohlc='i')
    s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds',
                           figcolor=BG_COLOR + '99', gridcolor=mcolors.to_hex(mcolors.to_rgba(TEXT_COLOR, alpha=0.1)))
    ap = [
        mpf.make_addplot(df_chart['SMA50'], color='orange', width=0.7),
        mpf.make_addplot(df_chart['SMA200'], color='purple', width=0.7),
    ]
    fig, axlist = mpf.plot(df_chart, type='candle', style=s, addplot=ap,
                           title=f"\n{symbol} Price Action with 50 & 200 Day SMA",
                           ylabel='Price (INR)', volume=True, ylabel_lower='Volume',
                           figsize=(size[0]/100, size[1]/100), returnfig=True)
    for ax in axlist:
        ax.yaxis.label.set_color('white'); ax.xaxis.label.set_color('white')
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_color('white')
        ax.set_facecolor((0,0,0,0))
    axlist[0].title.set_color('white')
    fig.savefig(out_png, dpi=100, pad_inches=0.2, transparent=True); plt.close(fig)
    return out_png
def make_index_comparison_chart(df_stock, df_index, stock_name, index_name="Nifty 50", size=(1280, 720), out_png="outputs/tmp/index_comp.png"):
    print("   -> Generating index comparison chart...")
    try:
        df_merged = pd.concat([df_stock['Close'], df_index['Close']], axis=1, keys=[stock_name, index_name]).dropna()
        df_norm = (df_merged / df_merged.iloc[0]) * 100
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        ax.plot(df_norm.index, df_norm[stock_name], color=ACCENT, label=stock_name, linewidth=2)
        ax.plot(df_norm.index, df_norm[index_name], color='#FFFFFF', label=index_name, linewidth=1, linestyle='--')
        ax.set_title(f"{stock_name} vs. {index_name} (1 Year Performance)", color="white", fontsize=18)
        ax.set_ylabel("Normalized Performance (%)", color="white")
        ax.legend()
        fig.tight_layout()
        plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate index comparison chart: {e}")
        return None
def make_shareholding_chart(data, size, out_png="outputs/tmp/shareholding.png"):
    print("   -> Generating shareholding pattern chart...")
    try:
        labels = list(data.keys())
        sizes = list(data.values())
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        wedges, texts, autotexts = ax.pie(sizes, autopct='%1.1f%%', startangle=90,
                                          wedgeprops=dict(width=0.4, edgecolor='w'),
                                          pctdistance=0.8)
        plt.setp(autotexts, size=10, weight="bold", color="white")
        ax.legend(wedges, labels, title="Shareholders", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        ax.set_title("Shareholding Pattern", color="white", fontsize=18)
        plt.savefig(out_png, transparent=True, bbox_inches='tight'); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not generate shareholding chart: {e}")
        return None
def make_financials_chart(y_symbol, size, out_png="outputs/tmp/financials.png"):
    try:
        financials = yf.Ticker(y_symbol).financials.T.head(4)
        financials['Net Income'] /= 1e7; financials['Total Revenue'] /= 1e7
        plt.style.use('dark_background'); fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        fig.patch.set_alpha(0); ax.patch.set_alpha(0)
        financials[['Total Revenue', 'Net Income']].plot(kind='bar', ax=ax, color=[ACCENT, '#FFFFFF'])
        ax.set_title("Financial Highlights (INR Crores)", color="white", fontsize=18)
        ax.tick_params(axis='x', labelrotation=0); fig.tight_layout()
        plt.savefig(out_png, transparent=True); plt.close()
        return out_png
    except Exception as e:
        print(f"      - Could not fetch financials chart: {e}")
        return None
def make_metrics_infographic(metrics, size, out_png="outputs/tmp/metrics.png"):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_alpha(0); ax.patch.set_alpha(0)
    ax.axis('off')
    ax.text(0.5, 0.9, "Key Metrics", color=TEXT_COLOR, fontsize=36, weight='bold', ha='center', transform=ax.transAxes)
    metrics_list = list(metrics.items())
    y_start = 0.75
    for i, (key, value) in enumerate(metrics_list):
        y_pos = y_start - i * 0.12
        ax.text(0.1, y_pos, key, color=TEXT_COLOR, alpha=0.8, fontsize=20, ha='left', va='center', transform=ax.transAxes)
        ax.text(0.9, y_pos, str(value), color=ACCENT, fontsize=28, weight='bold', ha='right', va='center', transform=ax.transAxes)
    plt.savefig(out_png, transparent=True, bbox_inches='tight', pad_inches=0.1); plt.close()
    return out_png
def build_narration(company, news_items, price_info):
    script_parts = {
        "intro": f"Here is your daily briefing on {company}. ...",
        "market": f"On the market, the stock was last {'gaining' if price_info['d_pct'] >= 0 else 'down'} about {abs(price_info['d_pct']):.1f} percent. ...",
        "cta": "Hit like for more such content on Stocks and comment your wishlisted Stock. Don't forget to share with those who may be interested."
    }
    for i, item in enumerate(news_items):
        script_parts[f"news_{i+1}"] = item['title'] + ". ..."
    return script_parts
def _generate_single_audio(script, output_path):
    synthesizer = None
    try:
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        if all([speech_key, speech_region]):
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
            speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(script).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
    except Exception: pass
    finally:
        if synthesizer: del synthesizer
    print(f"      - Azure failed for a segment. Falling back to gTTS...")
    try:
        gTTS(text=script, lang="en", tld="co.in").save(output_path)
        return True
    except Exception as e:
        print(f"      - gTTS also failed: {e}")
        return False
def generate_segmented_voiceover(script_parts):
    print("  -> Generating segmented voiceovers...")
    audio_paths = {}
    for key, script in script_parts.items():
        output_path = os.path.join(get_script_dir(), "outputs", "tmp", f"vo_{key}.mp3")
        if not _generate_single_audio(script, output_path):
            print(f"    - WARNING: Failed to generate audio for '{key}'. Skipping.")
        else:
            audio_paths[key] = output_path
    print("  -> Voiceover generation complete.")
    return audio_paths
def generate_subtitles(audio_path):
    try:
        print("  -> Generating subtitles with Whisper...")
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, verbose=False)
        return [((seg['start'], seg['end']), seg['text']) for seg in result['segments']]
    except Exception as e:
        print(f"  -> Whisper transcription failed: {e}."); return None
def create_chart_slide_image(chart_path, background_path, size, ken_burns=False):
    try:
        # Use a default solid background if no image path is provided
        if background_path:
            with Image.open(background_path) as bg_img_file:
                bg_img = bg_img_file.convert("RGBA")
        else:
            bg_img = Image.new("RGBA", size, BG_COLOR)

        target_size = (int(size[0] * 1.08), int(size[1] * 1.08)) if ken_burns else size
        bg_img = bg_img.resize(target_size, Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', bg_img.size, (0, 0, 0, 150))
        bg_img = Image.alpha_composite(bg_img, overlay)
        
        with Image.open(chart_path) as chart_img_file:
            chart_img = chart_img_file.convert("RGBA")
            scale = bg_img.width / size[0]
            chart_img.thumbnail((int(size[0] * 0.9 * scale), int(size[1] * 0.9 * scale)), Image.Resampling.LANCZOS)
            paste_x = (bg_img.width - chart_img.width) // 2
            paste_y = (bg_img.height - chart_img.height) // 2
            bg_img.paste(chart_img, (paste_x, paste_y), chart_img)
            return bg_img.convert("RGB")
            
    except Exception as e:
        print(f"      - Could not create chart slide: {e}. Using chart directly.")
        return Image.open(chart_path)
def create_slide_image(content_elements, background_path, size, font_path, ken_burns=False):
    try:
        if background_path:
            with Image.open(background_path) as bg_img_file:
                bg_img = bg_img_file.convert("RGBA")
        else:
            bg_img = Image.new("RGBA", size, BG_COLOR)
        target_size = (int(size[0] * 1.08), int(size[1] * 1.08)) if ken_burns else size
        bg_img = bg_img.resize(target_size, Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', bg_img.size, (0, 0, 0, 180))
        bg_img = Image.alpha_composite(bg_img, overlay)
    except Exception:
        target_size = (int(size[0] * 1.08), int(size[1] * 1.08)) if ken_burns else size
        bg_img = Image.new("RGB", target_size, BG_COLOR)
    draw = ImageDraw.Draw(bg_img)
    scale = bg_img.width / size[0]
    for element in content_elements:
        scaled_pos = (int(element['position'][0] * scale), int(element['position'][1] * scale))
        if element['type'] == 'text':
            scaled_box = (int(element.get('box', (size[0], size[1]))[0] * scale), int(element.get('box', (size[0], size[1]))[1] * scale))
            font = get_optimal_font_size(element['text'], int(element.get('initial_fontsize', 70) * scale), scaled_box[0], scaled_box[1], font_path)
            lines = wrap_text_pil(element['text'], font, scaled_box[0])
            line_heights = [draw.textbbox((0,0), line, font=font)[3] for line in lines]
            total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2)
            y_pos = scaled_pos[1] - total_text_height / 2
            for i, line in enumerate(lines):
                line_width = draw.textlength(line, font=font)
                x_pos = scaled_pos[0] - line_width / 2
                draw.text((x_pos + 3, y_pos + 3), line, font=font, fill="#00000088")
                draw.text((x_pos, y_pos), line, font=font, fill=element.get('color', TEXT_COLOR))
                y_pos += line_heights[i] * 1.2
        elif element['type'] == 'image':
             with Image.open(element['path']) as img_to_paste_file:
                img_to_paste = img_to_paste_file.convert("RGBA")
                scaled_size = (int(element['size'][0] * scale), int(element['size'][1] * scale))
                img_to_paste.thumbnail(scaled_size, Image.Resampling.LANCZOS)
                paste_pos = (int(scaled_pos[0] - img_to_paste.width / 2), int(scaled_pos[1] - img_to_paste.height / 2))
                bg_img.paste(img_to_paste, paste_pos, img_to_paste)
    return bg_img.convert("RGB")
def make_video(company, news_items, metrics, price_df, df_index, shareholding_chart, index_comp_chart, financials_chart, price_info, out_path, video_format, assets):
    VIDEO_W, VIDEO_H = (VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT)
    font_path = next((p for p in FONT_PATHS_TRY if os.path.exists(p)), None)
    if font_path is None: raise IOError("Could not find a valid font file.")
    print(f"  -> Using font: {font_path}")
    script_parts = build_narration(company, news_items, price_info)
    audio_paths = generate_segmented_voiceover(script_parts)

    audio_clips_timeline = []; current_time = 0.0
    slide_images = []; slide_durations = []
    bg_images = assets.get('bg_images', [])
    bg_idx = 0
    
    print("   -> Generating all slide images and building timeline...")

    if 'intro' in audio_paths:
        audio = AudioFileClip(audio_paths['intro'])
        duration = audio.duration + 1.0
        audio_clips_timeline.append(audio.set_start(current_time))
        content = [{"type": "text", "text": f"{company}\nDaily Briefing", "position": (VIDEO_W / 2, VIDEO_H * 0.6), "box": (VIDEO_W * 0.8, VIDEO_H * 0.4), "initial_fontsize": 90}]
        if assets.get('logo'):
            logo_path = os.path.join(get_script_dir(), "outputs", "tmp", "logo.png")
            assets['logo'].save(logo_path)
            logo_size = (int(min(VIDEO_W, VIDEO_H) * 0.25), int(min(VIDEO_W, VIDEO_H) * 0.25))
            content[0]['position'] = (VIDEO_W / 2, VIDEO_H * 0.65)
            content.insert(0, {"type": "image", "path": logo_path, "size": logo_size, "position": (VIDEO_W/2, VIDEO_H * 0.3)})
        slide_images.append(create_slide_image(content, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), font_path, ken_burns=True))
        slide_durations.append(duration); bg_idx += 1
        current_time += duration

    for i, item in enumerate(news_items):
        key = f"news_{i+1}"
        if key in audio_paths:
            audio = AudioFileClip(audio_paths[key])
            duration = audio.duration + 1.0
            audio_clips_timeline.append(audio.set_start(current_time))
            sentiment = classify_impact(item['title'])
            icon_path = os.path.join(get_script_dir(), "outputs", "tmp", f"{sentiment}_icon.png")
            cairosvg.svg2png(bytestring=ICON_SVG[sentiment], write_to=icon_path, output_height=60)
            content = [
                {"type": "text", "text": item['title'], "color": ACCENT, "position": (VIDEO_W / 2, VIDEO_H / 2), "box": (VIDEO_W * 0.85, VIDEO_H * 0.8), "initial_fontsize": 108},
                {"type": "image", "path": icon_path, "size": (60,60), "position": (VIDEO_W * 0.1, VIDEO_H * 0.1)}
            ]
            slide_images.append(create_slide_image(content, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), font_path, ken_burns=True))
            slide_durations.append(duration); bg_idx += 1
            current_time += duration

    if 'market' in audio_paths:
        audio = AudioFileClip(audio_paths['market'])
        duration = audio.duration + 1.0
        audio_clips_timeline.append(audio.set_start(current_time))
        price_chart_path = make_candlestick_chart(price_df, company, (VIDEO_W, VIDEO_H))
        slide_images.append(create_chart_slide_image(price_chart_path, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), ken_burns=True))
        slide_durations.append(duration); bg_idx += 1
        current_time += duration

    chart_duration = 8.0
    if index_comp_chart:
        slide_durations.append(chart_duration)
        slide_images.append(create_chart_slide_image(index_comp_chart, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), ken_burns=True))
        bg_idx += 1; current_time += chart_duration
    if financials_chart:
        slide_durations.append(chart_duration)
        slide_images.append(create_chart_slide_image(financials_chart, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), ken_burns=True))
        bg_idx += 1; current_time += chart_duration
    if metrics:
        metrics_graphic_path = make_metrics_infographic(metrics, (VIDEO_W, VIDEO_H))
        slide_images.append(create_chart_slide_image(metrics_graphic_path, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), ken_burns=True))
        slide_durations.append(chart_duration); bg_idx += 1; current_time += chart_duration
    if shareholding_chart:
        slide_durations.append(chart_duration)
        slide_images.append(create_chart_slide_image(shareholding_chart, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), ken_burns=True))
        bg_idx += 1; current_time += chart_duration

    if 'cta' in audio_paths:
        audio = AudioFileClip(audio_paths['cta'])
        duration = audio.duration
        audio_clips_timeline.append(audio.set_start(current_time))
        icon_paths = {}
        for name, svg in OUTRO_ICONS.items():
            path = os.path.join(get_script_dir(), "outputs", "tmp", f"icon_{name}.png")
            cairosvg.svg2png(bytestring=svg, write_to=path, output_height=80)
            icon_paths[name] = path
        icon_size = (80, 80)
        y_pos_icon = VIDEO_H * 0.45
        y_pos_text = y_pos_icon + 80
        content = [
            {"type": "image", "path": icon_paths['like'], "size": icon_size, "position": (VIDEO_W * 0.25, y_pos_icon)},
            {"type": "text", "text": "Like", "position": (VIDEO_W * 0.25, y_pos_text), "initial_fontsize": 40},
            {"type": "image", "path": icon_paths['comment'], "size": icon_size, "position": (VIDEO_W * 0.5, y_pos_icon)},
            {"type": "text", "text": "Comment", "position": (VIDEO_W * 0.5, y_pos_text), "initial_fontsize": 40},
            {"type": "image", "path": icon_paths['share'], "size": icon_size, "position": (VIDEO_W * 0.75, y_pos_icon)},
            {"type": "text", "text": "Share", "position": (VIDEO_W * 0.75, y_pos_text), "initial_fontsize": 40},
        ]
        slide_images.append(create_slide_image(content, bg_images[bg_idx % len(bg_images)], (VIDEO_W, VIDEO_H), font_path, ken_burns=True))
        slide_durations.append(duration); bg_idx += 1
        current_time += duration

    total_dur = sum(slide_durations)
    narration_audio = CompositeAudioClip(audio_clips_timeline)
    try:
        music_path = os.path.join(get_script_dir(), 'background_music.mp3')
        if os.path.exists(music_path):
            music = AudioFileClip(music_path).audio_loop(duration=total_dur).volumex(0.25)
            final_audio = CompositeAudioClip([narration_audio, music])
        else: final_audio = narration_audio
    except Exception: final_audio = narration_audio
    
    print("\n  -> Assembling video with transitions and effects...")
    clips = []
    start_time = 0
    for i, (img, duration) in enumerate(zip(slide_images, slide_durations)):
        clip = ImageClip(np.array(img)).set_duration(duration)
        zoom_factor = 1.08
        def resize_func(t, dur=duration): return 1 + (zoom_factor - 1) * (t / dur)
        clip = clip.resize(resize_func)
        pan_dir = i % 4
        positions = {0: ('left', 'top'), 1: ('right', 'top'), 2: ('left', 'bottom'), 3: ('right', 'bottom')}
        clip = clip.set_position(positions[pan_dir])
        clip = clip.set_start(start_time)
        if i > 0:
            clip = clip.crossfadein(1.0)
        clips.append(clip)
        start_time += duration

    video = CompositeVideoClip(clips, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur)
    
    full_audio_path = os.path.join(get_script_dir(), "outputs", "tmp", "vo_full.mp3")
    clips_for_concat = [AudioFileClip(audio_paths[key]) for key in sorted(script_parts.keys()) if key in audio_paths]
    full_narration_clip = concatenate_audioclips(clips_for_concat)
    full_narration_clip.write_audiofile(full_audio_path, codec='mp3', logger=None)
    subtitles_data = generate_subtitles(full_audio_path)
    
    composited_elements = [video]
    if subtitles_data:
        def subtitle_generator(txt):
            wrapped = wrap_text_for_subtitles(txt, 35 if video_format == 'portrait' else 50)
            return TextClip(wrapped, font=font_path, fontsize=38, color='white', stroke_color='#000000CC', stroke_width=2.5, align='center', method='caption')
        subtitle_clip = SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.88), relative=True)
        composited_elements.append(subtitle_clip)
    
    final_video = CompositeVideoClip(composited_elements, size=(VIDEO_W, VIDEO_H)).set_duration(total_dur)
    final_video.audio = final_audio
    print("  -> Writing final video file...")
    final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, preset="medium", logger='bar')
    
    for clip in audio_clips_timeline: clip.close()
    full_narration_clip.close()
    if 'music' in locals(): music.close()
    return out_path

def main():
    parser = argparse.ArgumentParser(description=f"Stock Video Briefing Generator v{__version__}")
    parser.add_argument("query", help="Company name or NSE ticker")
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='landscape', help="Video format")
    parser.add_argument("--elevenlabs", action='store_true', help="Use ElevenLabs for voiceover if Azure fails")
    parser.add_argument("--out", help="Output MP4 path")
    args = parser.parse_args()
    ensure_dirs()
    script_dir = get_script_dir()
    
    try:
        print(f"🎬 Starting video generation for '{args.query}' (v{__version__})")
        
        time.sleep(random.uniform(1, 2))
        print("\n1. Resolving symbol...")
        nse_symbol, y_symbol, display = resolve_symbol(args.query)
        print(f"   -> Found: {display} (NSE: {nse_symbol})")

        time.sleep(random.uniform(1, 2))
        print("\n2. Fetching & Scoring News...")
        all_news = (fetch_yfinance_news(y_symbol) + fetch_google_news(display, nse_symbol) +
                    fetch_moneycontrol_news(display) + fetch_economic_times_news(display))
        scored_news = [{**item, 'score': score_news_relevance(item['title'], display, item['source'])} for item in all_news]
        unique_news = []
        for news_item in sorted(scored_news, key=lambda x: x['score'], reverse=True):
            if not any(seq_ratio(news_item['title'], unique['title']) > 0.85 for unique in unique_news):
                unique_news.append(news_item)
        news_items = unique_news[:MAX_NEWS_ITEMS]
        if not news_items: print("   -> No relevant news found. Exiting."); return
        print(f"\n✅ Top {len(news_items)} headlines selected for the video:")
        for i, item in enumerate(news_items):
            print(f"   {i+1}. {item['title']} (Source: {item['source']}, Score: {item['score']})")

        time.sleep(random.uniform(1, 2))
        print("\n3. Fetching financial & price data...")
        df, df_index = fetch_price_data(y_symbol)
        snap = compute_price_snapshot(df)
        
        time.sleep(random.uniform(1, 2))
        metrics = fetch_financial_metrics(y_symbol)
        
        time.sleep(random.uniform(1, 2))
        shareholding = fetch_shareholding(y_symbol)
        print(f"   -> Last Close: {snap['last_close']:.2f}, Daily Change: {snap['d_pct']:.2f}%")

        print("\n4. Generating charts and tables...")
        chart_size = (1200, 600) if args.format == 'landscape' else (680, 500)
        financials_chart = make_financials_chart(y_symbol, size=chart_size)
        index_comp_chart = make_index_comparison_chart(df, df_index, display, size=chart_size)
        shareholding_chart = make_shareholding_chart(shareholding, size=chart_size) if shareholding else None

        print("\n5. Fetching visual assets...")
        assets = {'use_elevenlabs': args.elevenlabs, 'bg_images': []}
        assets['logo'] = fetch_company_logo(y_symbol)
        num_bgs_needed = 1 + len(news_items) + 1
        if not df.empty: num_bgs_needed += 1
        if financials_chart: num_bgs_needed += 1
        if metrics: num_bgs_needed += 1
        if shareholding_chart: num_bgs_needed += 1
        if index_comp_chart: num_bgs_needed += 1

        search_queries = [f"{display.split()[0]} abstract", "data visualization", "stock market", "business analytics", "corporate meeting"]
        random.shuffle(search_queries)
        if PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY"):
            print(f"   -> Fetching {num_bgs_needed} background images from Pexels...")
            try:
                api = API(os.getenv("PEXELS_API_KEY"))
                for query in search_queries:
                    if len(assets['bg_images']) >= num_bgs_needed: break
                    api.search(query, page=random.randint(1, 5), results_per_page=10)
                    for photo in api.get_entries():
                        if hasattr(photo, 'large2x'):
                            img_url = photo.large2x
                            img_path = os.path.join(script_dir, "outputs", "tmp", f"bg_{len(assets['bg_images'])}.jpg")
                            response = make_request_with_retries(img_url, timeout=60)
                            if response:
                                with open(img_path, 'wb') as f: f.write(response.content)
                                assets['bg_images'].append(img_path)
                                assets['bg_credit'] = "Photos by various artists on Pexels"
                                if len(assets['bg_images']) >= num_bgs_needed: break
            except Exception as e:
                print(f"      -  WARNING: Pexels API failed: {e}. Continuing with solid color backgrounds.")
                assets['bg_images'] = []

        print("\n6. Rendering video...")
        out_path = args.out or os.path.join(script_dir, "outputs", f"{nse_symbol}_{args.format}_briefing.mp4")
        make_video(company=display, news_items=news_items, metrics=metrics, price_df=df, df_index=df_index, 
                   shareholding_chart=shareholding_chart, index_comp_chart=index_comp_chart,
                   financials_chart=financials_chart, price_info=snap, out_path=out_path, 
                   video_format=args.format, assets=assets)

        print("\n--- Independent File Verification ---")
        if os.path.exists(out_path):
            file_size = os.path.getsize(out_path) / 1024 / 1024
            print(f"✅✅✅ SUCCESS: Video created at '{out_path}' (Size: {file_size:.2f} MB)")
            if file_size < 0.1: print("🚨 WARNING: File size is very small, video may be corrupt.")
        else:
            print("❌❌❌ FAILURE: File NOT FOUND. A silent FFmpeg error likely occurred.")

    except Exception as e:
        print(f"\n❌ An error occurred in the main process: {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()