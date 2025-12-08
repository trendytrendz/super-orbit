# ai_art_director/utils.py
# v24.3.2 - Consolidated & Fixed

import os
import shutil
import re
import time
import requests
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import List
from . import config

# Graceful third-party imports
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

# --- Path & Directory Utilities ---

def get_script_dir() -> str:
    return str(config.SRC_DIR)

def setup_project_directories():
    """Ensures all absolute output directories exist."""
    print(f"   -> Validating absolute paths...")
    dirs_to_create = [
        config.OUTPUT_DIR,
        config.TMP_DIR,
        config.AUDIO_VOICEOVERS_DIR,
        config.AUDIO_CACHE_DIR,
        config.AUDIO_FALLBACKS_DIR,
        config.TMP_IMG_DIR,
        config.MUSIC_DIR,
        config.FONT_DIR,
        config.FALLBACK_BACKGROUND_DIR,
    ]
    for d in dirs_to_create:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError as e:
            # Ignore music dir creation error if user manages it
            if d != config.MUSIC_DIR:
                print(f"      - ❌ Error creating {d}: {e}")    
     # FIX: Download BOTH fonts
    ensure_fonts()
    print("   ✅ Directories ready.")

def ensure_fonts():
    """Downloads English (Roboto) and Hindi (Noto) fonts with corruption checks."""
    
    # 1. Hindi Font
    hindi_path = config.FONT_DIR / config.HINDI_FONT_NAME
    _validate_and_download(
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf",
        hindi_path,
        "Hindi"
    )

    # 2. English Font (Roboto-Bold)
    # FIX: Updated to correct Static path in Google Fonts repo
    eng_path = config.FONT_DIR / "Roboto-Bold.ttf"
    _validate_and_download(
        "https://github.com/PolymerElements/font-roboto-local/blob/master/fonts/roboto/Roboto-Bold.ttf",
        eng_path,
        "English"
    )

def _validate_and_download(url, path, name):
    # Check for corruption (0-byte files)
    if path.exists() and path.stat().st_size < 1000:
        print(f"   -> ⚠️  Found corrupt {name} font. Deleting...")
        os.remove(path)
        
    if not path.exists():
        print(f"   -> ⬇️  Downloading {name} Font ({os.path.basename(path)})...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                with open(path, 'wb') as f: f.write(r.content)
                print(f"      - ✅ Download success.")
            else:
                print(f"      - ❌ Failed to download (Status: {r.status_code})")
        except Exception as e:
            print(f"      - ❌ Download Error: {e}")

def cleanup_temp_images():
    """Force cleanup of temp images."""
    try:
        if os.path.exists(config.TMP_IMG_DIR):
            shutil.rmtree(config.TMP_IMG_DIR)
        os.makedirs(config.TMP_IMG_DIR, exist_ok=True)
    except Exception as e:
        print(f"   -> ⚠️ Cleanup error: {e}")

def ensure_dirs():
    setup_project_directories()

# --- Time Utilities ---

def now_ist():
    """Returns current time in Indian Standard Time (UTC+5:30)"""
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

# --- LLM Utilities ---

def query_local_llm(prompt: str, max_words: int = 45, temperature: float = 0.3) -> str | None:
    """Sends a prompt to a locally running LLM (Ollama:Qwen)."""
    try:
        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": "qwen2.5:3b",
            "prompt": f"Please provide a concise response to: {prompt}",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_words * 10}
        }
        response = requests.post(url, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("      - ❌ Connection Error: Ensure Ollama is running")
    except Exception as e:
        print(f"      - ❌ LLM Error: {e}")
    return None

def query_local_llm_improved(prompt: str, max_words: int = 45, temperature: float = 0.3) -> str | None:
    """Wrapper for improved query (currently same implementation)."""
    return query_local_llm(prompt, max_words, temperature)

def generate_plain_text_script(context: str, instruction: str) -> str | None:
    prompt = f"Data: {context}. Instruction: {instruction}. Respond with one engaging sentence in plain text."
    script = query_local_llm(prompt, max_words=35)
    return script.strip() if script else None

def get_llm_search_terms(company_name: str, business_summary: str) -> List[str]:
    prompt = f"Generate 5 comma-separated search keywords for background images for a video about {company_name}. Business: {business_summary[:100]}. No people."
    response = query_local_llm(prompt, max_words=20)
    if response:
        keywords = [k.strip().strip('"').strip("'") for k in response.split(',')]
        return [k for k in keywords if len(k) > 2][:5]
    return ["business", "finance", "abstract"]

# --- Text Utilities ---

def create_ssml(text: str, lang: str = 'en') -> str:
    voice_conf = config.get_voice_for_lang(lang)
    prosody = voice_conf["ssml_prosody"]
    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}"><voice name="{voice_conf['azure_voice']}"><express-as style="{prosody['style']}"><prosody rate="{prosody['rate']}" pitch="{prosody['pitch']}" volume="{prosody['volume']}">{text}</prosody></express-as></voice></speak>"""
    return " ".join(ssml.strip().split())

def seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()

def classify_impact(text: str) -> str:
    text_lower = text.lower()
    pos = sum(1 for w in ['profit', 'growth', 'gain', 'rise', 'up', 'positive', 'beat', 'surge'] if w in text_lower)
    neg = sum(1 for w in ['loss', 'fall', 'drop', 'down', 'negative', 'miss', 'decline', 'cut'] if w in text_lower)
    return "positive" if pos > neg else "negative" if neg > pos else "neutral"

def make_request_with_retries(url: str, headers: dict = None, retries: int = 3, delay: int = 2, timeout: int = 30) -> requests.Response | None:
    for _ in range(retries):
        try:
            r = requests.get(url, headers=headers or {}, timeout=timeout)
            if r.status_code == 200: return r
        except: time.sleep(delay)
    return None

# --- Image/Font Utilities ---

def get_optimal_font(text: str, initial_size: int, max_w: int, max_h: int, font_path: str):
    return get_optimal_font_size(text, initial_size, max_w, max_h, font_path)

def get_optimal_font_size(text, initial_size, max_w, max_h, font_path):
    if not PIL_AVAILABLE: return None
    font_size = initial_size
    while font_size > 18:
        try:
            font = ImageFont.truetype(font_path, font_size)
            bbox = font.getbbox(text) if hasattr(font, 'getbbox') else font.getmask(text).getbbox()
            w = bbox[2] - bbox[0] if bbox else font.getlength(text)
            h = bbox[3] - bbox[1] if bbox else font.size
            if w <= max_w and h <= max_h: return font
        except: pass
        font_size -= 2
    return ImageFont.truetype(font_path, 18)

def wrap_text_pil(text, font, max_width):
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

def create_gradient_image(size, color1, color2, direction='horizontal'):
    return None