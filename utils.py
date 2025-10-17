# utils.py
import os
import time
import requests
import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse

try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False

import config

def query_local_llm(prompt, max_words=40):
    """Sends a prompt to the local Ollama server and gets a cleaned, truncated response."""
    print("   -> Querying local LLM for insights...")
    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        
        analysis = response.json().get("response", "").strip()

        # --- Aggressive Cleaning Logic ---
        # Remove any leading text that ends in a colon, e.g., "Here's my analysis:"
        analysis = re.sub(r'^(.*:)\s*', '', analysis, flags=re.IGNORECASE | re.DOTALL)
        # Remove markdown bolding/italics and backticks
        analysis = re.sub(r'[\*_`]', '', analysis)
        # Remove any list-like formatting at the beginning (e.g., "1. ", "- ")
        analysis = re.sub(r'^\s*[\d-]+\.\s*', '', analysis)
        
        analysis = analysis.strip().replace('"', '')

        # --- Truncation Logic ---
        words = analysis.split()
        if len(words) > max_words:
            analysis = " ".join(words[:max_words]) + "..."
        
        print("      - LLM analysis received and cleaned.")
        return analysis

    except requests.exceptions.RequestException as e:
        print(f"      - WARNING: Could not connect to local LLM. Is Ollama running? Error: {e}")
        return None

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

def get_browser_headers(url=""):
    base_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.tickertape.in/",
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    if FAKE_USERAGENT_AVAILABLE:
        base_headers['User-Agent'] = UserAgent().random
    if "tickertape.in" in urlparse(url).netloc:
        base_headers['x-tickertape-div'] = "7df92dc3-b097-421b-8c28-724d265a7098"
    return base_headers

def make_request_with_retries(url, headers=None, timeout=45, retries=3, delay=5):
    request_headers = headers if headers is not None else get_browser_headers(url)
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
    text = text.strip()
    if not text: return ""
    words = text.split();
    if not words: return ""
    lines, current_line = [], ""
    for word in words:
        if not current_line: current_line = word
        elif len(current_line) + 1 + len(word) <= max_chars_per_line: current_line += " " + word
        else: lines.append(current_line); current_line = word
    lines.append(current_line)
    if len(lines) > 1:
        last_line, second_last_line = lines[-1], lines[-2]
        if len(last_line.split()) == 1 and len(last_line) < 15:
            last_word_of_prev_line = second_last_line.split()[-1]
            if len(second_last_line) - len(last_word_of_prev_line) > 5:
                new_second_last_line = " ".join(second_last_line.split()[:-1])
                new_last_line = last_word_of_prev_line + " " + last_line
                if len(new_last_line) <= max_chars_per_line:
                    lines[-2], lines[-1] = new_second_last_line, new_last_line
    return "\n".join(lines)
