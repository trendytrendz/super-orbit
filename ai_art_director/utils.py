# ai_art_director/utils.py
# v25.8.0 - RESTORED FULL UTILITY BELT

import os
import shutil
import re
import time
import requests
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import List
from . import config

# Graceful imports
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False

# --- Directory Utils ---
def setup_project_directories():
    dirs = [
        config.OUTPUT_DIR, config.TMP_DIR, config.AUDIO_VOICEOVERS_DIR,
        config.AUDIO_CACHE_DIR, config.AUDIO_FALLBACKS_DIR,
        config.TMP_IMG_DIR, config.MUSIC_DIR, config.FONT_DIR,
        config.FALLBACK_BACKGROUND_DIR,
    ]
    for d in dirs: os.makedirs(d, exist_ok=True)
    ensure_fonts()

def ensure_fonts():
    # 1. Hindi Font
    _validate_and_download("https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari-Bold.ttf", config.FONT_DIR / config.HINDI_FONT_NAME, "Hindi")
    # 2. English Font
    _validate_and_download("https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf", config.FONT_DIR / "Roboto-Bold.ttf", "English")

def _validate_and_download(url, path, name):
    if path.exists():
        try:
            with open(path, 'rb') as f:
                if b'<!DOCTYPE' in f.read(20): os.remove(path)
                elif path.stat().st_size < 1000: os.remove(path)
        except: pass
    if not path.exists():
        print(f"   -> ⬇️  Downloading {name} Font...")
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
            if r.status_code == 200 and b'<!DOCTYPE' not in r.content[:20]:
                with open(path, 'wb') as f: f.write(r.content)
        except: pass

def cleanup_temp_images():
    try:
        if os.path.exists(config.TMP_IMG_DIR): shutil.rmtree(config.TMP_IMG_DIR)
        os.makedirs(config.TMP_IMG_DIR, exist_ok=True)
    except: pass

def get_script_dir(): return str(config.SRC_DIR)

# --- LLM Utils ---
def now_ist(): return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def query_local_llm(prompt, max_words=45, temperature=0.3):
    try:
        url = "http://127.0.0.1:11434/api/generate"
        payload = {"model": config.WHISPER_MODEL, "prompt": f"Response: {prompt}", "stream": False, "options": {"temperature": temperature, "num_predict": max_words * 10}}
        r = requests.post(url, json=payload, timeout=120)
        if r.status_code == 200: return r.json().get("response", "").strip()
    except: pass
    return None

def query_local_llm_improved(prompt, max_words=45, temperature=0.3): return query_local_llm(prompt, max_words, temperature)

def generate_plain_text_script(context, instruction):
    return query_local_llm(f"Data: {context}. Instruction: {instruction}. One plain sentence.", max_words=35)

def get_llm_search_terms(company_name, summary):
    res = query_local_llm(f"5 search keywords for background images about {company_name}. Business: {summary}. No people.", max_words=20)
    if res: return [k.strip("'\" ") for k in res.split(',') if len(k) > 2][:5]
    return ["business", "finance"]

# --- Text & Logic Utils (RESTORED) ---
def create_ssml(text, lang='en'):
    vc = config.get_voice_for_lang(lang); p = vc["ssml_prosody"]
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}"><voice name="{vc['azure_voice']}"><express-as style="{p['style']}"><prosody rate="{p['rate']}" pitch="{p['pitch']}" volume="{p['volume']}">{text}</prosody></express-as></voice></speak>"""

def seq_ratio(a, b): return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()

def classify_impact(text):
    t = text.lower()
    pos = sum(1 for w in ['profit', 'growth', 'gain', 'rise', 'up', 'positive', 'beat', 'surge'] if w in t)
    neg = sum(1 for w in ['loss', 'fall', 'drop', 'down', 'negative', 'miss', 'decline', 'cut'] if w in t)
    return "positive" if pos > neg else "negative" if neg > pos else "neutral"

def make_request_with_retries(url, headers=None, retries=3, delay=2, timeout=30):
    for _ in range(retries):
        try:
            r = requests.get(url, headers=headers or {'User-Agent': 'Mozilla/5.0'}, timeout=timeout)
            if r.status_code == 200: return r
        except: time.sleep(delay)
    return None

# --- VISUAL UTILS (RESTORED FOR COMPATIBILITY) ---
def get_optimal_font_size(text, initial_size, max_w, max_h, font_path):
    if not PIL_AVAILABLE: return None
    font_size = initial_size
    while font_size > 18:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
            if hasattr(font, 'getbbox'): bbox = font.getbbox(text)
            else: bbox = font.getmask(text).getbbox()
            w = bbox[2] - bbox[0] if bbox else font.getlength(text)
            h = bbox[3] - bbox[1] if bbox else font.size
            if w <= max_w and h <= max_h: return font
        except: pass
        font_size -= 2
    return ImageFont.load_default()

def wrap_text_pil(text, font, max_width):
    """Wraps text to fit width. Restored to utils.py to fix Video Renderer crash."""
    if not text: return []
    words = text.split()
    lines, current_line = [], []
    for word in words:
        test_line = ' '.join(current_line + [word])
        w = font.getlength(test_line) if hasattr(font, 'getlength') else font.getmask(test_line).getbbox()[2]
        if w <= max_width: current_line.append(word)
        else:
            if current_line: lines.append(' '.join(current_line))
            current_line = [word]
    if current_line: lines.append(' '.join(current_line))
    return lines

def draw_gradient_text(draw, text, font, position, color1, color2):
    draw.text(position, text, font=font, fill=color1)