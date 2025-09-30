import argparse
import os
import re
import time
import json
import math
import random
from io import BytesIO
from urllib.parse import quote_plus, urlparse
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import requests
import feedparser
import yfinance as yf
import numpy as np
import pandas as pd

from gtts import gTTS

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# -------------------------
# Config
# -------------------------
VIDEO_W, VIDEO_H = 1280, 720
BG_COLOR = (8, 12, 20)          # dark bg
ACCENT = (0, 172, 193)          # cyan-ish accent
TEXT_COLOR = (240, 244, 248)
FONT_PATHS_TRY = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
]
LOOKBACK_NEWS_DAYS = 7
VIDEO_TARGET_SECS = 60

CORP_KEYWORDS = [
    "dividend","buyback","acquisition","merger","capex","pledge",
    "resigns","resignation","appoints","order win","secures order","mou",
    "joint venture","jv","results","earnings","profit","loss","q1","q2","q3","q4",
    "fund raising","qip","preferential","rights issue","bonus","split",
    "demerger","scheme of arrangement","rating","downgrade","upgrade",
    "approval","shareholder","agm","guidance","forecast","revenue","ebitda",
    "tender","contract","nclt","sebi","board"
]

POSITIVE_CUES = [
    "buyback","bonus","split","order win","secures order","upgrade","raises guidance",
    "dividend","approval","mou","joint venture","contract","record order"
]
NEGATIVE_CUES = [
    "resigns","resignation","loss","downgrade","penalty","pledge","pledged",
    "fraud","default","inquiry","investigation"
]

# -------------------------
# Utils
# -------------------------
def ensure_dirs():
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("outputs/tmp", exist_ok=True)

def try_load_font(size=48):
    for p in FONT_PATHS_TRY:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()

def measure_text(draw, text, font):
    """
    Cross-version Pillow text measurement.
    Returns (width, height).
    """
    if text is None:
        return (0, 0)
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    except Exception:
        try:
            return draw.textsize(text, font=font)
        except Exception:
            try:
                l, t, r, b = font.getbbox(text)
                return r - l, b - t
            except Exception:
                return (int(len(text) * (getattr(font, "size", 12)) * 0.6),
                        getattr(font, "size", 12))

def wrap_text(draw, text, font, max_width):
    if not text:
        return []
    words = text.split()
    lines, cur = [], []
    for w in words:
        tentative = (" ".join(cur + [w])) if cur else w
        w_width, _ = measure_text(draw, tentative, font)
        if w_width <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                # very long single word; hard break
                lines.append(w)
                cur = []
    if cur:
        lines.append(" ".join(cur))
    return lines

def seq_ratio(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()

def now_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def human_date(dt):
    try:
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(dt)

# -------------------------
# Step 1: Resolve stock symbol
# -------------------------
def resolve_symbol(query):
    """
    Resolve an NSE symbol from a free Yahoo Finance search endpoint.
    Returns (nse_symbol, yahoo_symbol_with_suffix, display_name)
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query, "quotesCount": 6, "newsCount": 0}
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    picks = []
    for q in data.get("quotes", []):
        sym = q.get("symbol", "")
        exch = (q.get("exchDisp") or q.get("exchange") or "").upper()
        if sym.endswith(".NS") or exch in ("NSE", "NSI"):
            picks.append(q)
    if not picks and data.get("quotes"):
        picks = data["quotes"]
    if not picks:
        raise ValueError(f"Could not find symbol for '{query}'")

    best = picks[0]
    y_symbol = best["symbol"]
    display = best.get("longname") or best.get("shortname") or y_symbol
    nse_symbol = y_symbol.replace(".NS", "").replace(".BO","")
    if not y_symbol.endswith(".NS"):
        y_symbol = nse_symbol + ".NS"
    return nse_symbol, y_symbol, display

# -------------------------
# Step 2: Fetch news (Google News RSS)
# -------------------------
def fetch_corporate_news(name, symbol, days=7, max_items=8):
    q = f'"{name}" OR {symbol} when:{days}d'
    feed_url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(feed_url)
    items = []
    cutoff = now_ist() - timedelta(days=days)
    for e in feed.entries[: max_items * 2]:
        title = getattr(e, "title", "")
        link = getattr(e, "link", "")
        if not title or not link:
            continue
        if hasattr(e, "published_parsed") and e.published_parsed:
            published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
        else:
            published = now_ist()
        low = title.lower()
        if not any(k in low for k in CORP_KEYWORDS):
            continue
        if published < cutoff:
            continue
        items.append({
            "title": title,
            "link": link,
            "published": published,
            "source": urlparse(link).netloc
        })
        if len(items) >= max_items:
            break
    return items

# -------------------------
# Step 3: NSE session + Verify via NSE (robust)
# -------------------------
def _build_retry():
    try:
        # Newer urllib3
        return Retry(
            total=3,
            backoff_factor=0.6,
            status_forcelist=[401, 403, 429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
    except TypeError:
        # Older urllib3
        return Retry(
            total=3,
            backoff_factor=0.6,
            status_forcelist=[401, 403, 429, 500, 502, 503, 504],
            method_whitelist=["GET"],  # deprecated name
            raise_on_status=False,
        )

def make_nse_session(symbol_hint=None):
    """
    Build a requests.Session that looks like a real browser and warm it up
    so NSE sets the necessary cookies (ak_bmsc, bm_sv, etc).
    """
    s = requests.Session()
    retries = _build_retry()
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/127.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive",
        "DNT": "1",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "sec-ch-ua": '"Google Chrome";v="127", "Chromium";v="127", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    })
    # Warm-up requests to set cookies
    warm_urls = ["https://www.nseindia.com/"]
    if symbol_hint:
        warm_urls.append(f"https://www.nseindia.com/get-quotes/equity?symbol={symbol_hint}")
        warm_urls.append("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY")
    for u in warm_urls:
        try:
            s.get(u, timeout=10)
            time.sleep(0.6 + random.random() * 0.6)
        except Exception:
            pass
    return s

def _fix_url(u, base):
    if not u:
        return None
    u = str(u).strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return base.rstrip("/") + "/" + u.lstrip("/")

def nse_corporate_announcements(symbol, session=None, attempts=3):
    """
    Robust NSE announcements fetch with warm-up, retries, and cookie refresh.
    Returns list of dicts: {heading, url, date}
    """
    s = session or make_nse_session(symbol)
    url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"
    last_error = None

    for i in range(attempts):
        try:
            r = s.get(url, timeout=15)
            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception:
                    data = None
                if data:
                    rows = data.get("data", data)
                    anns = []
                    for it in rows:
                        head = it.get("HEADLINE") or it.get("heading") or it.get("HEADING") or it.get("subject") or it.get("title")
                        urlx  = it.get("ATTACHMENTURL") or it.get("attchmntUrl") or it.get("pdfUrl") or it.get("url")
                        dts   = it.get("DISSEMINATIONDATE") or it.get("dissemDate") or it.get("date") or it.get("dissem_dt")
                        if not head:
                            continue
                        # parse date robustly
                        dt = None
                        for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                            try:
                                dt = datetime.strptime(str(dts), fmt).replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                                break
                            except Exception:
                                pass
                        if not dt:
                            dt = now_ist()
                        urlx = _fix_url(urlx, "https://www.nseindia.com")
                        anns.append({"heading": head.strip(), "url": urlx, "date": dt})
                    return anns

            # If blocked, refresh cookies and retry
            if r.status_code in (401, 403):
                last_error = f"{r.status_code} {r.reason}"
                s = make_nse_session(symbol)
                time.sleep(0.8 + i * 0.5)
                continue

            # Other HTTP errors
            r.raise_for_status()

        except Exception as e:
            last_error = str(e)
            time.sleep(1 + i * 0.7)

    raise RuntimeError(f"NSE corporate announcements failed for {symbol}. Last error: {last_error}")

# -------------------------
# Optional: BSE fallback
# -------------------------
def bse_corporate_announcements(query, days=7, max_rows=50):
    """
    Lightweight BSE corporate announcements search by company name.
    Returns list of dicts similar to NSE version: {heading, url, date}
    """
    to_dt = now_ist().date()
    from_dt = to_dt - timedelta(days=days)
    url = ("https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
           f"?strCat=-1&strType=C&strScrip=&strSearch={quote_plus(query)}"
           f"&strFromDate={from_dt.strftime('%Y%m%d')}"
           f"&strToDate={to_dt.strftime('%Y%m%d')}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bseindia.com/",
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else data.get("Table", []) or data.get("Rows", [])
    anns = []
    for it in rows[:max_rows]:
        head = it.get("HEADLINE") or it.get("Nm") or it.get("Subject") or it.get("DESCRIPTION") or ""
        pdf  = it.get("ATTACHMENTNAME") or it.get("FilePath") or it.get("ATTACHMENTURL") or it.get("Url")
        dt   = it.get("DT_TM") or it.get("NEWSSUBDT") or it.get("NEWS_DT") or it.get("DISSEMINATIONDATE")
        # Parse date
        dt_parsed = None
        for fmt in ("%d %b %Y", "%d-%b-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
            try:
                dt_parsed = datetime.strptime(str(dt), fmt).replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
                break
            except Exception:
                pass
        if not dt_parsed:
            dt_parsed = now_ist()
        pdf = _fix_url(pdf, "https://www.bseindia.com")
        anns.append({"heading": head.strip(), "url": pdf, "date": dt_parsed})
    return anns

# -------------------------
# Step 4: Price data and chart
# -------------------------
def fetch_price_data(y_symbol, period="2mo"):
    tk = yf.Ticker(y_symbol)
    df = tk.history(period=period, interval="1d", auto_adjust=False)
    if df.empty:
        raise ValueError(f"No price data for {y_symbol}")
    df = df.tz_localize(None)
    df.index = pd.to_datetime(df.index)
    return df

def compute_price_snapshot(df):
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None
    last_close = float(last["Close"])
    prev_close = float(prev["Close"]) if prev is not None else last_close
    d_change = last_close - prev_close
    d_pct = (d_change / prev_close) * 100 if prev_close else 0
    # 5d change
    if len(df) >= 6:
        prev5 = float(df.iloc[-6]["Close"])
        d5 = last_close - prev5
        d5_pct = (d5 / prev5) * 100 if prev5 else 0
    else:
        d5_pct = 0
    return {
        "last_close": last_close,
        "prev_close": prev_close,
        "d_pct": d_pct,
        "d5_pct": d5_pct
    }

def make_price_chart(df, symbol, out_png="outputs/tmp/price.png"):
    plt.figure(figsize=(12.8, 7.2), dpi=100)
    plt.plot(df.index, df["Close"], color="#00ACC1", linewidth=3, label="Close")
    plt.fill_between(df.index, df["Close"], color="#00ACC1", alpha=0.1)
    plt.title(f"{symbol} - Last {len(df)} trading days", color="white", fontsize=18, pad=12)
    plt.grid(alpha=0.2)
    plt.xlabel("")
    plt.ylabel("Price (INR)", color="white")
    plt.tick_params(colors="white")
    plt.legend(loc="upper left")
    plt.gca().set_facecolor("#0B121A")
    plt.gcf().patch.set_facecolor("#0B121A")
    plt.tight_layout()
    plt.savefig(out_png, transparent=False, facecolor="#0B121A")
    plt.close()
    return out_png

# -------------------------
# Step 5: Heuristic impact + narration
# -------------------------
def classify_impact(text):
    t = (text or "").lower()
    pos = any(k in t for k in POSITIVE_CUES)
    neg = any(k in t for k in NEGATIVE_CUES)
    if pos and not neg:
        return "positive"
    if neg and not pos:
        return "negative"
    return "uncertain"

def build_narration(company, news_title, nse_heading, price_info, verified, nse_url):
    # Aim ~120-140 words for ~60s voiceover
    impact = classify_impact((nse_heading or news_title or ""))
    today = f"as of {now_ist().strftime('%d %b %Y')}"
    dir_word = "up" if price_info["d_pct"] >= 0 else "down"
    d_abs = abs(price_info["d_pct"])
    d5_abs = abs(price_info["d5_pct"])

    verification_line = ""
    if verified and nse_url:
        verification_line = f"This update is verified from NSE corporate announcements. Link in description."

    impact_line = {
        "positive": "This development is typically seen as positive for sentiment and valuations.",
        "negative": "This development can weigh on sentiment and near-term valuations.",
        "uncertain": "Market impact can be mixed and may depend on details and guidance."
    }[impact]

    script = f"""
Here’s a quick update on {company}. {news_title}.
{verification_line}
On prices, {today}, the stock is {dir_word} about {d_abs:.1f} percent versus the previous close, and about {d5_abs:.1f} percent over the last week.
{impact_line}
Investors often track follow-up disclosures, management commentary, and volumes after such announcements.
This video is for information only and is not investment advice.
"""
    # Clean spacing
    script = re.sub(r"\s+", " ", script).strip()
    return script, impact

# -------------------------
# MoviePy compatibility helpers (v1.x and v2.x)
# -------------------------
def clip_with_duration(clip, duration):
    if hasattr(clip, "set_duration"):
        return clip.set_duration(duration)
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    try:
        clip.duration = duration
    except Exception:
        pass
    return clip

def clip_with_audio(clip, audio):
    if hasattr(clip, "set_audio"):
        return clip.set_audio(audio)
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    try:
        clip.audio = audio
    except Exception:
        pass
    return clip

def clip_resize(clip, size):
    if hasattr(clip, "resize"):
        return clip.resize(size)
    if hasattr(clip, "with_size"):
        return clip.with_size(size)
    return clip

# -------------------------
# Step 6: Render text slides (PIL) and compose video (MoviePy)
# -------------------------
def draw_panel(text, title=False, subtitle=False, footer=None, width=VIDEO_W, height=VIDEO_H):
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    title_font = try_load_font(64 if title else 48)
    body_font = try_load_font(40 if not title else 44)

    margin = 80
    max_w = width - 2 * margin
    y = 90 if title else 120

    # Headline/body
    font = title_font if title else body_font
    lines = wrap_text(draw, text or "", font, max_w)

    for line in lines:
        lw, lh = measure_text(draw, line, font)
        draw.text((margin, y), line, fill=TEXT_COLOR, font=font)
        y += lh + 10

    # Footer
    if footer:
        foot_font = try_load_font(28)
        fw, fh = measure_text(draw, footer, foot_font)
        draw.text((margin, height - fh - 40), footer, fill=(170, 180, 190), font=foot_font)

    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def save_panel_to_file(text, out_path, title=False, footer=None):
    bio = draw_panel(text, title=title, footer=footer)
    with open(out_path, "wb") as f:
        f.write(bio.getbuffer())
    return out_path

def make_video(company, verified_news, price_df, price_info, narration, impact, out_path):
    ensure_dirs()
    # Slides
    title_txt = f"{company}\nCorporate Update"
    summary_txt = verified_news["title"]
    impact_txt = f"Possible market impact: {impact.capitalize()}\nToday: {price_info['d_pct']:+.2f}% | 5D: {price_info['d5_pct']:+.2f}%"
    footer = "Data: NSE/BSE (verification), Yahoo Finance (prices). Not investment advice."

    title_img = "outputs/tmp/title.png"
    summary_img = "outputs/tmp/summary.png"
    impact_img = "outputs/tmp/impact.png"
    chart_img = make_price_chart(price_df, company, out_png="outputs/tmp/chart.png")

    save_panel_to_file(title_txt, title_img, title=True, footer=footer)
    save_panel_to_file(summary_txt, summary_img, title=False, footer=footer)
    save_panel_to_file(impact_txt, impact_img, title=False, footer=footer)

    # Voiceover
    voice_mp3 = "outputs/tmp/vo.mp3"
    tts = gTTS(text=narration, lang="en", tld="co.in")
    tts.save(voice_mp3)
    audio = AudioFileClip(voice_mp3)

    # Timing: 60s target, but ensure >= audio duration
    audio_dur = getattr(audio, "duration", None) or 0
    total_dur = max(VIDEO_TARGET_SECS, audio_dur + 1.0)
    # Title: 5s, Summary: 22s, Chart: 25s, Impact: rest
    d_title = 5
    d_summary = 22
    d_chart = 25
    d_impact = max(6, total_dur - (d_title + d_summary + d_chart))

    clips = []
    clips.append(clip_resize(clip_with_duration(ImageClip(title_img), d_title), (VIDEO_W, VIDEO_H)))
    clips.append(clip_resize(clip_with_duration(ImageClip(summary_img), d_summary), (VIDEO_W, VIDEO_H)))
    clips.append(clip_resize(clip_with_duration(ImageClip(chart_img), d_chart), (VIDEO_W, VIDEO_H)))
    clips.append(clip_resize(clip_with_duration(ImageClip(impact_img), d_impact), (VIDEO_W, VIDEO_H)))

    video = concatenate_videoclips(clips, method="compose")
    video = clip_with_audio(video, audio)

    out = out_path
    video.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", bitrate="2500k", threads=4, preset="medium")
    audio.close()
    return out

# -------------------------
# Step 7: Match news to announcements
# -------------------------
def verify_news_with_nse(news_items, announcements, window_days=7):
    verified = []
    for n in news_items:
        best = None
        best_score = 0
        for a in announcements:
            try:
                delta_days = abs((n["published"] - a["date"]).days)
            except Exception:
                delta_days = window_days
            if delta_days > window_days:
                continue
            score = seq_ratio(n["title"], a["heading"])
            if score > best_score:
                best = a
                best_score = score
        is_verified = best is not None and best_score >= 0.5
        verified.append({
            **n,
            "verified": is_verified,
            "match_score": round(best_score, 3),
            "nse_heading": best["heading"] if best else None,
            "nse_url": best["url"] if best else None,
            "nse_date": best["date"] if best else None,
        })
    verified.sort(key=lambda x: (x["verified"], x["match_score"], x["published"]), reverse=True)
    return verified

# -------------------------
# Orchestration
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Corporate update finder + 1-min video generator (India stocks)")
    parser.add_argument("query", help="Company name or ticker (e.g., 'TCS' or 'Tata Consultancy Services')")
    parser.add_argument("--days", type=int, default=LOOKBACK_NEWS_DAYS, help="News lookback days (default 7)")
    parser.add_argument("--out", default=None, help="Output MP4 path (default outputs/<SYMBOL>_news.mp4)")
    args = parser.parse_args()

    ensure_dirs()

    print("Resolving symbol...")
    nse_symbol, y_symbol, display = resolve_symbol(args.query)
    print(f"Resolved: NSE={nse_symbol}, Yahoo={y_symbol}, Name={display}")

    print("Fetching recent news...")
    news = fetch_corporate_news(display, nse_symbol, days=args.days, max_items=8)
    if not news:
        print("No corporate-looking news found in lookback window.")
        return

    print("Fetching corporate announcements for verification...")
    try:
        anns = nse_corporate_announcements(nse_symbol)
        source_used = "NSE"
    except Exception as e:
        print(f"NSE verification failed ({e}). Trying BSE fallback...")
        anns = bse_corporate_announcements(display, days=args.days)
        source_used = "BSE"

    print("Matching news with announcements...")
    ranked = verify_news_with_nse(news, anns, window_days=args.days)
    top = ranked[0]
    print(json.dumps({
        "top_news": {
            "title": top["title"],
            "published": human_date(top["published"]),
            "source": top["source"],
            "verified": top["verified"],
            "regulator_source": source_used,
            "nse_heading": top["nse_heading"],
            "nse_url": top["nse_url"],
            "match_score": top["match_score"]
        }
    }, indent=2, default=str))

    print("Fetching price data...")
    df = fetch_price_data(y_symbol, period="2mo")
    snap = compute_price_snapshot(df)

    print("Building narration...")
    narr, impact = build_narration(display, top["title"], top.get("nse_heading"), snap, top["verified"], top.get("nse_url"))

    print("Creating video (this can take ~1–2 minutes)...")
    out_path = args.out or f"outputs/{nse_symbol}_news.mp4"
    mp4 = make_video(display, top, df.tail(30), snap, narr, impact, out_path=out_path)

    print(f"Done! Video saved to: {mp4}")
    if top.get("nse_url"):
        print(f"Verification link: {top['nse_url']} (source: {source_used})")

if __name__ == "__main__":
    main()