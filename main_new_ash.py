import argparse
import os
import re
import time
import json
import random
from io import BytesIO
from urllib.parse import quote_plus, urlparse
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

# Core Libraries
import requests
import feedparser
import yfinance as yf
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
from gtts import gTTS
import whisper
from tqdm import tqdm
import webcolors

# MoviePy Libraries
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
    concatenate_videoclips, TextClip
)
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video import fx as vfx
from moviepy.audio import fx as afx

# Optional imports
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

# -------------------------
# Config & Constants
# -------------------------
VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE = 1280, 720
VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT = 720, 1280
BG_COLOR = "#080C14"
ACCENT = "#00ACC1"
TEXT_COLOR = "#F0F4F8"
FONT_PATHS_TRY = [
    # macOS standard paths
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    # Linux standard paths
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    # Windows standard paths
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\Arial.ttf",
]
LOOKBACK_NEWS_DAYS = 3
VIDEO_TARGET_SECS = 75
MAX_NEWS_ITEMS = 3
LOGO_API_URL = "https://logo.clearbit.com/{domain}"
CORP_KEYWORDS = [
    "dividend", "buyback", "acquisition", "merger", "demerger", "split", "bonus", "fund raising", "qip",
    "rights issue", "capex", "investment", "appoints", "resigns", "resignation", "ceo", "cfo", "board meeting",
    "order win", "secures order", "bags order", "signs deal", "pact", "deal", "contract", "partnership",
    "collaboration", "joint venture", "jv", "mou", "results", "earnings", "profit", "loss", "revenue",
    "ebitda", "pat", "q1", "q2", "q3", "q4", "guidance", "outlook", "forecast", "approval", "nod",
    "clearance", "sebi", "nclt", "rbi", "rating", "downgrade", "upgrade", "stake", "pledge", "promoter"
]
POSITIVE_CUES = ["buyback", "bonus", "split", "order win", "secures order", "upgrade", "raises guidance", "dividend", "approval", "mou", "joint venture", "contract", "record order"]
NEGATIVE_CUES = ["resigns", "resignation", "loss", "downgrade", "penalty", "pledge", "fraud", "default", "inquiry", "investigation"]

# -------------------------
# Helper Functions
# -------------------------
def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

def ensure_dirs():
    script_dir = get_script_dir()
    os.makedirs(os.path.join(script_dir, "outputs"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "outputs", "tmp"), exist_ok=True)

def now_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def seq_ratio(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()

def classify_impact(text):
    t = (text or "").lower()
    if any(k in t for k in POSITIVE_CUES): return "positive"
    if any(k in t for k in NEGATIVE_CUES): return "negative"
    return "uncertain"

def wrap_text_pil(text, font, max_width):
    if not text: return []
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    lines, cur = [], []
    words = text.split()
    for w in words:
        tentative = " ".join(cur + [w]) if cur else w
        if draw.textbbox((0,0), tentative, font=font)[2] <= max_width:
            cur.append(w)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [w]
    if cur: lines.append(" ".join(cur))
    return lines

def get_optimal_font_size(text, initial_size, max_width, max_height, font_path):
    font_size = initial_size
    font = ImageFont.truetype(font_path, font_size)
    def get_text_dimensions(txt, fnt):
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        lines = wrap_text_pil(txt, fnt, max_width)
        if not lines: return 0, 0
        line_heights = [draw.textbbox((0,0), line, font=fnt)[3] - draw.textbbox((0,0), line, font=fnt)[1] for line in lines]
        total_height = sum(line_heights) + (len(lines) - 1) * (font_size * 0.2)
        max_line_width = max(draw.textbbox((0,0), line, font=fnt)[2] for line in lines) if lines else 0
        return max_line_width, total_height
    width, height = get_text_dimensions(text, font)
    while (height > max_height or width > max_width) and font_size > 20:
        font_size -= 4
        font = ImageFont.truetype(font_path, font_size)
        width, height = get_text_dimensions(text, font)
    return font

def wrap_text_for_subtitles(text, max_width_chars=40):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_width_chars:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    lines.append(current_line.strip())
    return "\n".join(lines)

def _fix_url(u, base):
    if not u: return None
    return u if u.startswith("http") else f"{base.rstrip('/')}/{str(u).lstrip('/')}"

# -------------------------
# Data Fetching Functions
# -------------------------
def resolve_symbol(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={quote_plus(query)}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    data = r.json().get('quotes', [])
    picks = [q for q in data if ".NS" in q.get('symbol', '')] or data
    if not picks: raise ValueError(f"Could not find symbol for '{query}'")
    best = picks[0]
    display = best.get("longname") or best.get("shortname") or best["symbol"]
    nse_symbol = best["symbol"].replace(".NS", "")
    return nse_symbol, best["symbol"], display

def fetch_corporate_news(name, symbol, days=7):
    items = []
    now = now_ist()
    print("   -> Searching for specific corporate news...")
    q_corp = f'"{name}" OR {symbol} when:{days}d'
    feed_url_corp = f"https://news.google.com/rss/search?q={quote_plus(q_corp)}&hl=en-IN&gl=IN&ceid=IN:en"
    feed_corp = feedparser.parse(feed_url_corp)
    for e in feed_corp.entries:
        if any(k in e.title.lower() for k in CORP_KEYWORDS):
            try:
                published_time = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc).astimezone(now.tzinfo)
                items.append({"title": e.title, "link": e.link, "published": published_time, "type": "corporate"})
            except: continue
    if not items:
        print("   -> No specific corporate news found. Falling back to general news.")
        q_general = f'"{name}" OR {symbol} when:{days}d'
        feed_url_general = f"https://news.google.com/rss/search?q={quote_plus(q_general)}&hl=en-IN&gl=IN&ceid=IN:en"
        feed_general = feedparser.parse(feed_url_general)
        for e in feed_general.entries:
            try:
                published_time = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc).astimezone(now.tzinfo)
                items.append({"title": e.title, "link": e.link, "published": published_time, "type": "general"})
            except: continue
    return sorted(items, key=lambda x: x['published'], reverse=True)

def fetch_financial_metrics(y_symbol):
    print("  -> Fetching key financial metrics...")
    try:
        info = yf.Ticker(y_symbol).info
        metrics = {
            "P/E Ratio": info.get('trailingPE'), "P/B Ratio": info.get('priceToBook'),
            "Debt to Equity": info.get('debtToEquity'), "Market Cap (Cr)": info.get('marketCap', 0) / 1e7
        }
        for key, val in metrics.items():
            metrics[key] = f"{val:,.2f}" if isinstance(val, (int, float)) else "N/A"
        return metrics
    except Exception as e:
        print(f"  -> Could not fetch financial metrics: {e}")
        return None

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
            url = LOGO_API_URL.format(domain=domain)
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception: pass
    return None

def fetch_relevant_image(query):
    if not PEXELS_AVAILABLE or not os.getenv("PEXELS_API_KEY"): return None, None
    try:
        api = API(os.getenv("PEXELS_API_KEY"))
        api.search(query, page=1, results_per_page=1)
        if not api.get_entries(): return None, None
        photo = api.get_entries()[0]
        response = requests.get(photo.src['large2x'], stream=True, timeout=15)
        credit = f"Photo by {photo.photographer} on Pexels"
        return Image.open(BytesIO(response.content)).convert("RGB"), credit
    except Exception: return None, None

def make_price_chart(df, symbol, size, out_png="outputs/tmp/price.png"):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    ax.plot(df.index, df["Close"], color=ACCENT, linewidth=3)
    ax.fill_between(df.index, df["Close"], color=ACCENT, alpha=0.1)
    ax.set_title(f"{symbol} Price Trend", color="white", fontsize=18)
    ax.tick_params(colors='white')
    ax.grid(alpha=0.2)
    fig.tight_layout()
    plt.savefig(out_png, facecolor=BG_COLOR, transparent=True)
    plt.close()
    return out_png

def make_financials_chart(y_symbol, size, out_png="outputs/tmp/financials.png"):
    try:
        financials = yf.Ticker(y_symbol).financials.T.head(4)
        financials['Net Income'] /= 1e7
        financials['Total Revenue'] /= 1e7
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100), dpi=100)
        financials[['Total Revenue', 'Net Income']].plot(kind='bar', ax=ax, color=[ACCENT, '#FFFFFF'])
        ax.set_title("Financial Highlights (INR Crores)", color="white", fontsize=18)
        ax.tick_params(axis='x', labelrotation=0)
        fig.tight_layout()
        plt.savefig(out_png, facecolor=BG_COLOR, transparent=True)
        plt.close()
        return out_png
    except Exception: return None

# -------------------------
# Audio & Narration
# -------------------------
def build_narration(company, news_items, price_info):
    news_type = news_items[0].get("type", "general")
    news_summary = " and ".join([item['title'] for item in news_items[:2]])
    impact = classify_impact(news_summary)
    dir_word = "gaining" if price_info['d_pct'] >= 0 else "down"
    intro_line = f"Here is your daily briefing on {company}, focusing on key corporate developments." if news_type == "corporate" else f"Here is your daily briefing on {company}, with the latest headlines."
    script = f"""{intro_line} Recent news includes: {news_summary}. On the market front, the stock was last {dir_word} about {abs(price_info['d_pct']):.1f} percent, with a five-day change of about {abs(price_info['d5_pct']):.1f} percent. This content is for informational purposes only, and not financial advice."""
    return re.sub(r"\s+", " ", script).strip(), impact

def generate_voiceover(script, use_elevenlabs=False):
    output_path = os.path.join(get_script_dir(), "outputs", "tmp", "vo.mp3")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if use_elevenlabs and ELEVENLABS_AVAILABLE and api_key:
        try:
            print("  -> Generating voiceover with ElevenLabs...")
            client = ElevenLabs(api_key=api_key)
            response = client.tts.generate(text=script, voice="Rachel", model="eleven_multilingual_v2")
            with open(output_path, "wb") as f:
                for chunk in response:
                    if chunk: f.write(chunk)
            print("  -> ElevenLabs voiceover successful.")
            return output_path
        except Exception as e:
            print(f"  -> ElevenLabs failed: {e}. Falling back to gTTS.")
    print("  -> Generating voiceover with gTTS...")
    gTTS(text=script, lang="en", tld="co.in").save(output_path)
    return output_path

def generate_subtitles(audio_path):
    print("  -> Generating subtitles with Whisper...")
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, verbose=False)
        subtitles = [((seg['start'], seg['end']), seg['text'].strip()) for seg in result['segments']]
        print("  -> Subtitles generated successfully.")
        return subtitles
    except Exception as e:
        print(f"  -> Whisper transcription failed: {e}. Skipping subtitles.")
        return None

# -------------------------
# Video Composition
# -------------------------
def create_animated_text_clip(text, font_path, size, duration, color=TEXT_COLOR, initial_fontsize=70):
    font = get_optimal_font_size(text, initial_fontsize, size[0], size[1], font_path)
    txt_clip = TextClip(text, fontsize=font.size, color=color, font=font_path,
                        align='center', method='caption', size=size)
    return txt_clip.set_duration(duration).crossfadein(0.5)

def create_title_slide(text, duration, size, font_path, assets):
    bg_clip = assets.get('bg_clip')
    if bg_clip is None: bg_clip = ImageClip(np.array(Image.new("RGB", size, BG_COLOR)), ismask=False).set_duration(duration)
    animated_text = create_animated_text_clip(text, font_path, (size[0]*0.8, size[1]*0.4), duration, initial_fontsize=90)
    composited = [bg_clip, animated_text.set_position('center')]
    if assets.get('logo_clip'):
        logo_clip = assets['logo_clip'].set_duration(duration).crossfadein(0.5)
        logo_pos, text_pos = (('center', size[1] * 0.3), ('center', size[1] * 0.6))
        composited = [bg_clip, logo_clip.set_position(logo_pos), animated_text.set_position(text_pos)]
    return CompositeVideoClip(composited, size=size).set_duration(duration)

def create_news_slide(headline, duration, size, font_path, assets):
    bg_clip = assets.get('bg_clip')
    if bg_clip is None: bg_clip = ImageClip(np.array(Image.new("RGB", size, BG_COLOR)), ismask=False).set_duration(duration)
    news_text = create_animated_text_clip(headline, font_path, (size[0]*0.9, size[1]*0.8), duration, initial_fontsize=135).set_position('center')
    return CompositeVideoClip([bg_clip, news_text], size=size).set_duration(duration)

def create_metrics_slide(metrics, duration, size, font_path, assets):
    bg_clip = assets.get('bg_clip')
    if bg_clip is None: bg_clip = ImageClip(np.array(Image.new("RGB", size, BG_COLOR)), ismask=False).set_duration(duration)
    metrics_text = "Key Metrics\n\n" + "\n".join([f"{key}: {value}" for key, value in metrics.items()])
    text_clip = create_animated_text_clip(metrics_text, font_path, (size[0]*0.8, size[1]*0.8), duration, initial_fontsize=60).set_position('center')
    return CompositeVideoClip([bg_clip, text_clip], size=size).set_duration(duration)

def create_chart_slide(chart_path, duration, size, assets):
    bg_clip = assets.get('bg_clip')
    if bg_clip is None: bg_clip = ImageClip(np.array(Image.new("RGB", size, BG_COLOR)), ismask=False).set_duration(duration)
    chart_img = ImageClip(chart_path).set_duration(duration).resize(width=size[0] * 0.9).set_position('center')
    return CompositeVideoClip([bg_clip, chart_img], size=size).set_duration(duration)

def img_to_array(img):
    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size)
        bg.paste(img, mask=img.getchannel('A'))
        return np.array(bg)
    return np.array(img)

def make_video(company, news_items, metrics, price_df, financials_chart, price_info, out_path, video_format, assets):
    VIDEO_W, VIDEO_H = (VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE) if video_format == 'landscape' else (VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT)
    font_path = next((p for p in FONT_PATHS_TRY if os.path.exists(p)), None)
    if font_path is None: raise IOError("Could not find a valid font file. Please check FONT_PATHS_TRY.")
    print(f"  -> Using font: {font_path}")

    narration, impact = build_narration(company, news_items, price_info)
    voice_path = generate_voiceover(narration, assets.get('use_elevenlabs'))
    voice_audio = AudioFileClip(voice_path)
    total_dur = max(VIDEO_TARGET_SECS, voice_audio.duration + 2.0)
    try:
        music = AudioFileClip('background_music.mp3').audio_loop(duration=total_dur).volumex(0.25)
        final_audio = CompositeAudioClip([voice_audio, music])
    except (IOError, OSError):
        final_audio = voice_audio

    bg_img, credit = assets.get('bg_image'), assets.get('bg_credit')
    if bg_img:
        initial_size = (int(VIDEO_W * 1.15), int(VIDEO_H * 1.15))
        bg_img = bg_img.resize(initial_size, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(15))
        enhancer = ImageEnhance.Brightness(bg_img)
        bg_img = enhancer.enhance(0.4)
        bg_clip = ImageClip(img_to_array(bg_img)).set_duration(total_dur).resize(lambda t: 1.15 - 0.15 * (t / total_dur)).set_position('center')
        assets['bg_clip'] = bg_clip
    else:
        assets['bg_clip'] = None
    if assets.get('logo'):
        logo_size = int(min(VIDEO_W, VIDEO_H) * 0.2)
        assets['logo'].thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
        assets['logo_clip'] = ImageClip(img_to_array(assets['logo']))

    subtitles_data = generate_subtitles(voice_path)
    if subtitles_data:
        def subtitle_generator(txt):
            wrapped = wrap_text_for_subtitles(txt, 35 if video_format == 'portrait' else 50)
            return TextClip(wrapped, font=font_path, fontsize=38, color='white', stroke_color='#00000088', stroke_width=2, align='center', method='caption')
        subtitle_clip = SubtitlesClip(subtitles_data, subtitle_generator).set_position(('center', 0.88), relative=True).set_duration(total_dur)
    else:
        subtitle_clip = None

    print("  -> Composing video slides...")
    d_title = 5.0
    d_metrics = 8.0 if metrics else 0
    d_news_each = 8.0
    d_price_chart = 12.0
    d_financials_chart = 10.0 if financials_chart else 0
    num_news_slides = len(news_items)
    base_duration = d_title + d_metrics + (d_news_each * num_news_slides) + d_price_chart + d_financials_chart
    if num_news_slides > 0:
        extra_time = max(0, total_dur - base_duration)
        d_news_each += extra_time / num_news_slides

    clips = [create_title_slide(f"{company}\nDaily Briefing", d_title, (VIDEO_W, VIDEO_H), font_path, assets)]
    if metrics: clips.append(create_metrics_slide(metrics, d_metrics, (VIDEO_W, VIDEO_H), font_path, assets))
    for item in news_items: clips.append(create_news_slide(item['title'], d_news_each, (VIDEO_W, VIDEO_H), font_path, assets))
    clips.append(create_chart_slide(make_price_chart(price_df, company, (VIDEO_W, VIDEO_H)), d_price_chart, (VIDEO_W, VIDEO_H), assets))
    if financials_chart: clips.append(create_chart_slide(financials_chart, d_financials_chart, (VIDEO_W, VIDEO_H), assets))
    
    print("  -> Adding transitions and finalizing video...")
    if clips:
        clips[0] = clips[0].fadein(0.5)
        clips[-1] = clips[-1].fadeout(0.5)
    video = concatenate_videoclips(clips).set_duration(total_dur)
    
    final_composited = [video]
    if subtitle_clip: final_composited.append(subtitle_clip)
    footer_clip = TextClip("Source: Google News, Yahoo Finance. Not financial advice.", fontsize=20, color='gray', font=font_path).set_position(('center', VIDEO_H * 0.95)).set_duration(total_dur)
    final_composited.append(footer_clip)
    if credit:
        credit_clip = TextClip(credit, fontsize=16, color='gray', font=font_path).set_position((10, VIDEO_H - 30)).set_duration(total_dur)
        final_composited.append(credit_clip)

    final_video = CompositeVideoClip(final_composited, size=(VIDEO_W, VIDEO_H))
    final_video.audio = final_audio
    final_video.duration = total_dur
    
    print("  -> Writing video file...")
    final_video.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", bitrate="3000k", threads=4, preset="medium", logger='bar')
    
    voice_audio.close()
    if 'music' in locals() and music: music.close()
    return out_path

# -------------------------
# Main Orchestration
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate a daily briefing video for an Indian stock.")
    parser.add_argument("query", help="Company name or NSE ticker")
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='landscape', help="Video format")
    parser.add_argument("--elevenlabs", action='store_true', help="Use ElevenLabs for premium voiceover")
    parser.add_argument("--out", help="Output MP4 path")
    args = parser.parse_args()
    ensure_dirs()
    script_dir = get_script_dir()
    try:
        print(f"🎬 Starting video generation for '{args.query}' in {args.format} format.")

        print("\n1. Resolving symbol...")
        nse_symbol, y_symbol, display = resolve_symbol(args.query)
        print(f"   -> Found: {display} (NSE: {nse_symbol})")

        print("\n2. Fetching recent news...")
        news_items = fetch_corporate_news(display, nse_symbol, days=LOOKBACK_NEWS_DAYS)[:MAX_NEWS_ITEMS]
        if not news_items:
            print("   -> No relevant news found. Exiting.")
            return
        print(f"   -> Found {len(news_items)} headlines for the video.")

        print("\n3. Fetching financial & price data...")
        df = fetch_price_data(y_symbol)
        snap = compute_price_snapshot(df)
        metrics = fetch_financial_metrics(y_symbol)
        print(f"   -> Last Close: {snap['last_close']:.2f}, Daily Change: {snap['d_pct']:.2f}%")

        print("\n4. Fetching visual assets...")
        assets = {'use_elevenlabs': args.elevenlabs}
        assets['logo'] = fetch_company_logo(y_symbol)
        search_queries = [f"{display.split()[0]} factory", f"{display.split()[0]} corporate", "stock market chart"]
        for query in search_queries:
            assets['bg_image'], assets['bg_credit'] = fetch_relevant_image(query)
            if assets['bg_image']:
                print(f"   -> Found background image for query: '{query}'")
                break
        
        print("\n5. Generating charts...")
        chart_size = (1200, 600) if args.format == 'landscape' else (680, 500)
        financials_chart = make_financials_chart(y_symbol, chart_size)
        
        print("\n6. Rendering video...")
        out_path = args.out or os.path.join(script_dir, "outputs", f"{nse_symbol}_{args.format}_briefing.mp4")
        
        try:
            print("\nStarting video render process...")
            make_video(
                company=display,
                news_items=news_items,
                metrics=metrics,
                price_df=df.tail(60),
                financials_chart=financials_chart,
                price_info=snap,
                out_path=out_path,
                video_format=args.format,
                assets=assets
            )
            
            print("\n--- Independent File Verification ---")
            if os.path.exists(out_path):
                file_size = os.path.getsize(out_path) / 1024 / 1024
                print(f"✅✅✅ SUCCESS: File FOUND! Size: {file_size:.2f} MB")
                if file_size < 0.1: print("🚨 WARNING: File size is very small, video may be corrupt.")
            else:
                print("❌❌❌ FAILURE: File NOT FOUND. A silent FFmpeg error likely occurred.")
            print("------------------------------------")
        
        except Exception as e:
            print(f"\n❌ An error occurred during video rendering: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            tmp_dir = os.path.join(script_dir, "outputs", "tmp")
            if os.path.exists(tmp_dir) and os.listdir(tmp_dir):
                print(f"\nFYI: Temp directory ('{tmp_dir}') contains files: {os.listdir(tmp_dir)}")

    except Exception as e:
        print(f"\n❌ An error occurred in the main process: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()