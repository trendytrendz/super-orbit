# -----------------------------------------------------------------------------
# Stock Video Briefing Generator
# Version: 1.2.4 (Frozen)
#
# Description: A comprehensive script to automatically generate daily financial
#              briefing videos for a given stock symbol.
#
# Changes in v1.2.4:
# - Candlestick chart now uses a 60% translucent background for better
#   readability against dynamic video backgrounds.
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

# MoviePy & Optional Libraries
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, TextClip
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

# Charting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import mplfinance as mpf

# -------------------------
# Version & Config
# -------------------------
__version__ = "1.2.4"

VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE = 1280, 720
VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT = 720, 1280
BG_COLOR = "#080C14"; ACCENT = "#00ACC1"; TEXT_COLOR = "#F0F4F8"
FONT_PATHS_TRY = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf"
]
LOOKBACK_NEWS_DAYS = 7; VIDEO_TARGET_SECS = 90; MAX_NEWS_ITEMS = 5
IMPACT_KEYWORDS = ["profit", "loss", "earnings", "revenue", "deal", "order", "appoints", "launches", "acquires", "merger", "results", "guidance", "upgrade", "downgrade", "stake"]
POSITIVE_CUES = ["buyback", "bonus", "split", "order win", "upgrade", "raises guidance", "dividend", "approval", "record order", "profit", "acquires", "launches"]
NEGATIVE_CUES = ["resigns", "resignation", "loss", "downgrade", "penalty", "pledge", "fraud", "default", "investigation"]
ICON_SVG = {
    "positive": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#4CAF50" d="m280-400 200-200 200 200H280Z"/></svg>',
    "negative": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#F44336" d="M480-560 280-760h400L480-560Z"/></svg>',
    "uncertain": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>',
}
SOURCE_BONUS = {
    "Yahoo Finance": 20,
    "MoneyControl": 15,
    "Economic Times": 10,
    "Google News": 0
}

# (Helper functions and Data Fetching are unchanged from v1.2.3)
# ...
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
def make_request_with_retries(url, headers=None, timeout=15, retries=3, delay=3):
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        }
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
    font_size = initial_size
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
def resolve_symbol(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote_plus(query)}"
    r = make_request_with_retries(url)
    data = r.json().get('quotes', [])
    picks = [q for q in data if ".NS" in q.get('symbol', '')] or data
    if not picks: raise ValueError(f"Could not find symbol for '{query}'")
    best = picks[0]
    display = best.get("longname") or best.get("shortname") or best["symbol"]
    return best["symbol"].replace(".NS", ""), best["symbol"], display
def fetch_yfinance_news(y_symbol):
    print("   -> Fetching from Yahoo Finance...")
    try:
        news = yf.Ticker(y_symbol).news; items = []; now = now_ist()
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
        info = yf.Ticker(y_symbol).info
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
    except Exception: return None
def fetch_price_data(y_symbol):
    df = yf.Ticker(y_symbol).history(period="3mo", interval="1d")
    if df.empty: raise ValueError(f"No price data for {y_symbol}")
    return df
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

# -------------------------
# Chart & Infographic Generation
# -------------------------
def make_candlestick_chart(df, symbol, size, out_png="outputs/tmp/price.png"):
    df_resampled = df.tail(45)
    mc = mpf.make_marketcolors(up=ACCENT, down='#F44336', edge={'up':ACCENT, 'down':'#F44336'},
                               wick={'up':ACCENT, 'down':'#F44336'}, volume=ACCENT, ohlc='i')
    # FIX: Use a translucent background color for better readability.
    # The '99' at the end of the hex code sets ~60% opacity.
    s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds',
                           figcolor=BG_COLOR + '99', gridcolor=mcolors.to_hex(mcolors.to_rgba(TEXT_COLOR, alpha=0.1)))
                           
    fig, axlist = mpf.plot(df_resampled, type='candle', style=s,
                           title=f"\n{symbol} Price Action",
                           ylabel='Price (INR)', volume=True, ylabel_lower='Volume',
                           figsize=(size[0]/100, size[1]/100), returnfig=True)
    for ax in axlist:
        ax.yaxis.label.set_color('white'); ax.xaxis.label.set_color('white')
        for label in ax.get_xticklabels() + ax.get_yticklabels(): label.set_color('white')
        # Make axes backgrounds transparent so the figcolor shows through
        ax.set_facecolor((0,0,0,0))
    axlist[0].title.set_color('white')
    
    # Save with transparency to capture the semi-transparent background
    fig.savefig(out_png, dpi=100, pad_inches=0.2, transparent=True); plt.close(fig)
    return out_png

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
    except Exception: return None

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
# -------------------------
# Audio & Narration
# -------------------------
def build_narration(company, news_items, price_info):
    news_summary = ". ".join([item['title'] for item in news_items[:2]])
    dir_word = "gaining" if price_info['d_pct'] >= 0 else "down"
    script = f"""Here is your daily briefing on {company}. Recent headlines include: {news_summary}. On the market, the stock was last {dir_word} about {abs(price_info['d_pct']):.1f} percent, with a five-day change of about {abs(price_info['d5_pct']):.1f} percent. This is for informational purposes only."""
    return re.sub(r"\s+", " ", script).strip()
def generate_voiceover_azure(script, output_path):
    synthesizer = None
    try:
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        if not all([speech_key, speech_region]):
            print("  -> Azure credentials (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION) not found.")
            return False
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        print("  -> Generating voiceover with Microsoft Azure...")
        result = synthesizer.speak_text_async(script).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("  -> Azure voiceover successful.")
            return True
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"  -> Azure TTS failed: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"     Error details: {cancellation_details.error_details}")
            return False
    except Exception as e:
        print(f"  -> An exception occurred during Azure TTS generation: {e}")
    finally:
        if synthesizer:
            del synthesizer
    return False
def generate_voiceover(script, use_elevenlabs=False):
    output_path = os.path.join(get_script_dir(), "outputs", "tmp", "vo.mp3")
    if generate_voiceover_azure(script, output_path):
        return output_path
    eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
    if use_elevenlabs and ELEVENLABS_AVAILABLE and eleven_api_key:
        print("  -> Azure failed. Falling back to ElevenLabs...")
        try:
            client = ElevenLabs(api_key=eleven_api_key)
            response = client.text_to_speech.convert(voice_id="21m00Tcm4TlvDq8ikWAM", text=script, model_id="eleven_multilingual_v2")
            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk: f.write(chunk)
            print("  -> ElevenLabs voiceover successful.")
            return output_path
        except Exception as e:
            print(f"  -> ElevenLabs also failed: {e}")
    print("  -> All premium TTS failed. Falling back to gTTS...")
    gTTS(text=script, lang="en", tld="co.in").save(output_path)
    return output_path
def generate_subtitles(audio_path):
    try:
        print("  -> Generating subtitles with Whisper...")
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, verbose=False)
        return [((seg['start'], seg['end']), seg['text'].strip()) for seg in result['segments']]
    except Exception as e:
        print(f"  -> Whisper transcription failed: {e}."); return None
# -------------------------
# Video Composition
# -------------------------
def create_slide_image(content_elements, background_path, size, font_path):
    try:
        with Image.open(background_path) as bg_img_file:
            bg_img = bg_img_file.convert("RGBA")
            initial_size = (int(size[0] * 1.25), int(size[1] * 1.25))
            bg_img = bg_img.resize(initial_size, Image.Resampling.LANCZOS)
            x_offset = random.randint(0, bg_img.width - size[0])
            y_offset = random.randint(0, bg_img.height - size[1])
            bg_img = bg_img.crop((x_offset, y_offset, x_offset + size[0], y_offset + size[1]))
            overlay = Image.new('RGBA', size, (0, 0, 0, 180))
            bg_img = Image.alpha_composite(bg_img, overlay)
    except Exception:
        bg_img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(bg_img)
    for element in content_elements:
        if element['type'] == 'text':
            font = get_optimal_font_size(element['text'], element.get('initial_fontsize', 70), element['box'][0], element['box'][1], font_path)
            lines = wrap_text_pil(element['text'], font, element['box'][0])
            line_heights = [draw.textbbox((0,0), line, font=font)[3] for line in lines]
            total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2)
            y_pos = element['position'][1] - total_text_height / 2
            for i, line in enumerate(lines):
                line_width = draw.textlength(line, font=font)
                x_pos = element['position'][0] - line_width / 2
                draw.text((x_pos + 3, y_pos + 3), line, font=font, fill="#00000088")
                draw.text((x_pos, y_pos), line, font=font, fill=element.get('color', TEXT_COLOR))
                y_pos += line_heights[i] * 1.2
        elif element['type'] == 'image':
             with Image.open(element['path']) as img_to_paste_file:
                img_to_paste = img_to_paste_file.convert("RGBA")
                img_to_paste.thumbnail(element['size'], Image.Resampling.LANCZOS)
                bg_img.paste(img_to_paste, element['position'], img_to_paste)
    return bg_img
def create_chart_slide_image(chart_path, background_path, size):
    try:
        with Image.open(background_path) as bg_img_file, Image.open(chart_path) as chart_img_file:
            bg_img = bg_img_file.convert("RGBA")
            bg_img = bg_img.resize(size, Image.Resampling.LANCZOS)
            overlay = Image.new('RGBA', size, (0, 0, 0, 150))
            bg_img = Image.alpha_composite(bg_img, overlay)
            chart_img = chart_img_file.convert("RGBA")
            chart_img.thumbnail((size[0] * 0.9, size[1] * 0.9), Image.Resampling.LANCZOS)
            paste_x = (size[0] - chart_img.width) // 2
            paste_y = (size[1] - chart_img.height) // 2
            bg_img.paste(chart_img, (paste_x, paste_y), chart_img)
            return bg_img.convert("RGB")
    except Exception as e:
        print(f"      - Could not create chart slide: {e}. Using chart directly.")
        return Image.open(chart_path)
def make_video(company, news_items, metrics, price_df, financials_chart, price_info, out_path, video_format, assets):
    VIDEO_W, VIDEO_H = (VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT)
    font_path = next((p for p in FONT_PATHS_TRY if os.path.exists(p)), None)
    if font_path is None: raise IOError("Could not find a valid font file.")
    print(f"  -> Using font: {font_path}")
    narration = build_narration(company, news_items, price_info)
    voice_path = generate_voiceover(narration, assets.get('use_elevenlabs'))
    voice_audio = AudioFileClip(voice_path)
    total_dur = max(VIDEO_TARGET_SECS, voice_audio.duration + 2.0)
    try:
        music_path = os.path.join(get_script_dir(), 'background_music.mp3')
        if os.path.exists(music_path):
            music = AudioFileClip(music_path).audio_loop(duration=total_dur).volumex(0.25)
            final_audio = CompositeAudioClip([voice_audio.set_start(0), music])
        else: final_audio = voice_audio
    except Exception: final_audio = voice_audio
    slide_paths, slide_durations = [], []
    bg_images = assets.get('bg_images', [])
    bg_idx = 0
    d_title = 5.0; d_news_each = 8.0; d_price_chart = 12.0
    d_financials_chart = 10.0 if financials_chart else 0
    d_metrics = 10.0 if metrics else 0
    num_news_slides = len(news_items)
    base_duration = d_title + (d_news_each * num_news_slides) + d_price_chart + d_financials_chart + d_metrics
    if num_news_slides > 0: d_news_each += max(0, total_dur - base_duration) / num_news_slides
    print("   -> Generating slide 1: Title")
    content = [{"type": "text", "text": f"{company}\nDaily Briefing", "position": (VIDEO_W / 2, VIDEO_H * 0.6), "box": (VIDEO_W * 0.8, VIDEO_H * 0.4), "initial_fontsize": 90}]
    if assets.get('logo'):
        logo_path = os.path.join(get_script_dir(), "outputs", "tmp", "logo.png")
        assets['logo'].save(logo_path)
        logo_size = int(min(VIDEO_W, VIDEO_H) * 0.25)
        content[0]['position'] = (VIDEO_W / 2, VIDEO_H * 0.65)
        content.insert(0, {"type": "image", "path": logo_path, "size": (logo_size, logo_size), "position": (int(VIDEO_W/2 - logo_size/2), int(VIDEO_H * 0.25))})
    slide_img = create_slide_image(content, bg_images[bg_idx % len(bg_images)] if bg_images else None, (VIDEO_W, VIDEO_H), font_path)
    path = os.path.join(get_script_dir(), "outputs", "tmp", "slide_0.jpg"); slide_img.convert("RGB").save(path)
    slide_paths.append(path); slide_durations.append(d_title); bg_idx += 1
    for i, item in enumerate(news_items):
        print(f"   -> Generating slide {i+2}: News")
        sentiment = classify_impact(item['title'])
        icon_path = os.path.join(get_script_dir(), "outputs", "tmp", f"{sentiment}_icon.png")
        cairosvg.svg2png(bytestring=ICON_SVG[sentiment], write_to=icon_path, output_height=80)
        content = [
            {"type": "text", "text": item['title'], "color": ACCENT, "position": (VIDEO_W / 2, VIDEO_H / 2), "box": (VIDEO_W * 0.85, VIDEO_H * 0.8), "initial_fontsize": 108},
            {"type": "image", "path": icon_path, "size": (80, 80), "position": (int(VIDEO_W * 0.05), int(VIDEO_H * 0.05))}
        ]
        slide_img = create_slide_image(content, bg_images[bg_idx % len(bg_images)] if bg_images else None, (VIDEO_W, VIDEO_H), font_path)
        path = os.path.join(get_script_dir(), "outputs", "tmp", f"slide_news_{i}.jpg"); slide_img.convert("RGB").save(path)
        slide_paths.append(path); slide_durations.append(d_news_each); bg_idx += 1
    chart_bg = bg_images[bg_idx % len(bg_images)] if bg_images else None
    print("   -> Generating slide: Price Chart")
    price_chart_path = make_candlestick_chart(price_df, company, (VIDEO_W, VIDEO_H))
    price_slide_img = create_chart_slide_image(price_chart_path, chart_bg, (VIDEO_W, VIDEO_H))
    path = os.path.join(get_script_dir(), "outputs", "tmp", "slide_price.jpg"); price_slide_img.save(path)
    slide_paths.append(path); slide_durations.append(d_price_chart); bg_idx += 1
    if financials_chart:
        print("   -> Generating slide: Financials Chart")
        chart_bg = bg_images[bg_idx % len(bg_images)] if bg_images else None
        financials_slide_img = create_chart_slide_image(financials_chart, chart_bg, (VIDEO_W, VIDEO_H))
        path = os.path.join(get_script_dir(), "outputs", "tmp", "slide_financials.jpg"); financials_slide_img.save(path)
        slide_paths.append(path); slide_durations.append(d_financials_chart); bg_idx += 1
    if metrics:
        print("   -> Generating slide: Metrics Infographic")
        chart_bg = bg_images[bg_idx % len(bg_images)] if bg_images else None
        metrics_graphic_path = make_metrics_infographic(metrics, (VIDEO_W, VIDEO_H))
        metrics_slide_img = create_chart_slide_image(metrics_graphic_path, chart_bg, (VIDEO_W, VIDEO_H))
        path = os.path.join(get_script_dir(), "outputs", "tmp", "slide_metrics.jpg"); metrics_slide_img.save(path)
        slide_paths.append(path); slide_durations.append(d_metrics)
    print("\n  -> Stitching slides into video...")
    clips = [ImageClip(p).set_duration(d) for p, d in zip(slide_paths, slide_durations)]
    video = concatenate_videoclips(clips, method="compose").set_duration(sum(slide_durations)).resize(width=VIDEO_W)
    composited_elements = [video]
    subtitles_data = generate_subtitles(voice_path)
    if subtitles_data:
        def subtitle_generator(txt):
            wrapped = wrap_text_for_subtitles(txt, 35 if video_format == 'portrait' else 50)
            return TextClip(wrapped, font=font_path, fontsize=38, color='white', stroke_color='#000000CC', stroke_width=2.5, align='center', method='caption')
        subtitle_clip = SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.88), relative=True)
        composited_elements.append(subtitle_clip)
    footer_clip = TextClip(txt="Sources: Multiple. Not financial advice.", fontsize=20, color='gray', font=font_path).set_position(('center', VIDEO_H * 0.95))
    composited_elements.append(footer_clip)
    if assets.get('bg_credit'):
        credit_clip = TextClip(txt=assets['bg_credit'], fontsize=16, color='gray', font=font_path).set_position((10, VIDEO_H - 30))
        composited_elements.append(credit_clip)
    final_video = CompositeVideoClip(composited_elements).set_duration(total_dur)
    final_video.audio = final_audio
    print("  -> Writing final video file...")
    final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, preset="medium", logger='bar')
    voice_audio.close()
    if 'music' in locals() and music: music.close()
    return out_path

# -------------------------
# Main Orchestration
# -------------------------
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
        print("\n1. Resolving symbol...")
        nse_symbol, y_symbol, display = resolve_symbol(args.query)
        print(f"   -> Found: {display} (NSE: {nse_symbol})")

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

        print("\n3. Fetching financial & price data...")
        df = fetch_price_data(y_symbol)
        snap = compute_price_snapshot(df)
        metrics = fetch_financial_metrics(y_symbol)
        print(f"   -> Last Close: {snap['last_close']:.2f}, Daily Change: {snap['d_pct']:.2f}%")

        print("\n4. Generating charts and tables...")
        chart_size = (1200, 600) if args.format == 'landscape' else (680, 500)
        financials_chart = make_financials_chart(y_symbol, chart_size)

        print("\n5. Fetching visual assets...")
        assets = {'use_elevenlabs': args.elevenlabs, 'bg_images': []}
        assets['logo'] = fetch_company_logo(y_symbol)
        
        num_bgs_needed = 1 + len(news_items)
        if not df.empty: num_bgs_needed += 1
        if financials_chart: num_bgs_needed += 1
        if metrics: num_bgs_needed += 1

        search_queries = [f"{display.split()[0]} abstract", "data visualization", "stock market", "business analytics", "corporate meeting"]
        random.shuffle(search_queries)
        if PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY"):
            print(f"   -> Fetching {num_bgs_needed} background images from Pexels...")
            api = API(os.getenv("PEXELS_API_KEY"))
            for query in search_queries:
                if len(assets['bg_images']) >= num_bgs_needed: break
                try:
                    api.search(query, page=random.randint(1, 5), results_per_page=5)
                    for photo in api.get_entries():
                        if hasattr(photo, 'large2x'):
                            img_url = photo.large2x
                            img_path = os.path.join(script_dir, "outputs", "tmp", f"bg_{len(assets['bg_images'])}.jpg")
                            response = make_request_with_retries(img_url, timeout=20)
                            if response:
                                with open(img_path, 'wb') as f: f.write(response.content)
                                assets['bg_images'].append(img_path)
                                assets['bg_credit'] = "Photos by various artists on Pexels"
                                if len(assets['bg_images']) >= num_bgs_needed: break
                except Exception as e:
                    print(f"      - Pexels search for '{query}' failed: {e}")
                    continue

        print("\n6. Rendering video...")
        out_path = args.out or os.path.join(script_dir, "outputs", f"{nse_symbol}_{args.format}_briefing.mp4")
        make_video(company=display, news_items=news_items, metrics=metrics, price_df=df, financials_chart=financials_chart,
                   price_info=snap, out_path=out_path, video_format=args.format, assets=assets)

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