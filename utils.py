# utils.py
import os
import time
import requests
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont

# Conditional import for fake_useragent
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False

import config

def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

def ensure_dirs():
    script_dir = get_script_dir()
    os.makedirs(os.path.join(script_dir, "outputs"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "outputs", "tmp"), exist_ok=True)
    os.makedirs(os.path.join(script_dir, "music"), exist_ok=True)

def now_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def seq_ratio(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()

def classify_impact(text):
    t = (text or "").lower()
    if any(k in t for k in config.POSITIVE_CUES): return "positive"
    if any(k in t for k in config.NEGATIVE_CUES): return "negative"
    return "uncertain"

def get_browser_headers():
    """Returns a dictionary of headers to mimic a real browser request."""
    base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    if FAKE_USERAGENT_AVAILABLE:
        base_headers['User-Agent'] = UserAgent().random
    return base_headers

def make_request_with_retries(url, headers=None, timeout=45, retries=3, delay=5):
    request_headers = headers if headers is not None else get_browser_headers()
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=request_headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"      - Attempt {attempt + 1}/{retries} failed for URL: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise
    return None

def wrap_text_pil(text, font, max_width):
    if not text: return []
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, cur, words = [], [], text.split()
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
    if len(text) <= max_chars_per_line or len(words) < 5:
        return text.strip()
    mid_point = len(words) // 2; best_split = mid_point; min_diff = float('inf')
    for i in range(max(0, mid_point - 5), min(len(words), mid_point + 5)):
        line1 = " ".join(words[:i]); line2 = " ".join(words[i:])
        diff = abs(len(line1) - len(line2))
        if diff < min_diff: min_diff = diff; best_split = i
    line1 = " ".join(words[:best_split]); line2 = " ".join(words[best_split:])
    return f"{line1}\n{line2}"
