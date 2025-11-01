# utils.py
# v20.2.7 - Added missing draw_gradient_text and enhanced market cap formatting

import os
import time
import requests
import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
import base64
from io import BytesIO
import random

try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False

import config

def draw_gradient_text(draw, text, font, position, color1, color2):
    """Draw gradient text on a PIL ImageDraw object"""
    try:
        x, y = position
        lines = wrap_text_pil(text, font, 10000)
        
        if not lines:
            return
            
        # Calculate total text height
        line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
        total_text_height = sum(line_heights) + (len(lines) - 1) * (font.size * 0.2)
        
        if total_text_height == 0:
            return
            
        current_y = y
        
        for i, line in enumerate(lines):
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width, line_height = line_bbox[2], line_bbox[3]
            
            # Create text mask
            text_mask = Image.new('L', (line_width, line_height))
            mask_draw = ImageDraw.Draw(text_mask)
            mask_draw.text((0, 0), line, font=font, fill=255)
            
            # Calculate gradient colors for this line
            start_ratio = (current_y - y) / total_text_height if total_text_height > 0 else 0
            end_ratio = (current_y + line_height - y) / total_text_height if total_text_height > 0 else 1
            
            # Convert colors to RGB tuples
            c1 = tuple(int(color1.lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
            c2 = tuple(int(color2.lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
            
            # Interpolate colors
            line_c1 = tuple(int(c1[k] + (c2[k] - c1[k]) * start_ratio) for k in range(3))
            line_c2 = tuple(int(c1[k] + (c2[k] - c1[k]) * end_ratio) for k in range(3))
            
            # Create gradient image
            gradient_img = create_gradient_image(
                (line_width, line_height), 
                f"rgb{line_c1}", 
                f"rgb{line_c2}", 
                'vertical'
            )
            
            # Draw text with shadow and gradient
            draw.text((x + 2, current_y + 2), line, font=font, fill="#00000088")
            draw._image.paste(gradient_img, (int(x), int(current_y)), text_mask)
            
            current_y += line_heights[i] * 1.2
            
    except Exception as e:
        print(f"      - ❌ Gradient text drawing failed: {e}")
        # Fallback: draw regular text
        draw.text(position, text, font=font, fill=color1)

def generate_plain_text_script(context_data, instruction, max_words=35):
    """Uses an LLM to generate a single, engaging, PLAIN TEXT sentence."""
    prompt = f"""
    You are a scriptwriter for a viral financial YouTube Short. Your task is to transform dry data into a single, engaging, and concise sentence for a voiceover.

    **CRITICAL RULES:**
    1.  **One Sentence Only:** Your output must be a single, complete sentence.
    2.  **Plain Text:** Do NOT use any XML or SSML tags. Just write the sentence.
    3.  **Use Exact Numbers:** Use the exact market cap and financial numbers provided in the context.
    4.  **Conversational Tone:** Write in a clear, slightly informal, and punchy style.

    ---
    **DATA CONTEXT FOR THIS SCENE:**
    {context_data}
    ---
    **YOUR INSTRUCTION FOR THIS SCENE:**
    {instruction}
    ---
    **YOUR SCRIPT (plain text):**
    """
    script = query_local_llm(prompt, max_words=max_words)
    
    if script:
        script = script.strip()
        if not script.endswith(('.', '?', '!')):
            script += '.'
        print(f"      - LLM Script: {script}")
        return script
        
    print(f"      - WARNING: LLM script generation failed. Falling back to instruction text.")
    return instruction.split('.')[0] + '.'

def get_llm_search_terms(company_name, business_summary):
    context = business_summary if business_summary and business_summary.strip() else company_name
    prompt = f"""
    You are an AI Art Director for a professional financial video. Your task is to generate visually evocative, SFW (Safe for Work), and abstract search terms for a stock photo website.
    **Instructions:**
    1.  **Analyze the Context:** Read the company's description.
    2.  **Generate Professional Keywords:** Create a list of 5-7 concise, one or two-word keywords.
    3.  **CRITICAL RULE - AVOID UNPROFESSIONAL IMAGERY AT ALL COSTS:**
        - **ABSOLUTELY NO** people, faces, crowds, hands, or body parts. I will be penalized if a person appears.
        - **ABSOLUTELY NO** flowers, plants, animals, or overtly "natural" scenes (unless the company is in that specific industry like agriculture).
        - **FOCUS EXCLUSIVELY ON:** Abstract textures, data visualizations, server rooms, architectural lines, clean office interiors, industrial machinery (if relevant), financial charts, glowing light trails, geometric patterns, and motion blur cityscapes.
    4.  **Output Format:** Provide the output as a single, comma-separated line.
    **Context:** - Company: "{company_name}" - Business Summary: "{context}"
    **Your Professional & Abstract Keywords (comma-separated):**
    """
    print("   -> Using LLM to brainstorm professional background keywords...")
    response = query_local_llm(prompt, max_words=40)
    if response:
        first_line = response.split('\n')[0]
        keywords = [k.strip() for k in first_line.split(',') if k.strip() and len(k.strip()) < 30]
        if keywords:
            print(f"      - LLM suggested keywords: {keywords}")
            return keywords
    print("      - LLM keyword generation failed or returned invalid output. Using fallbacks.")
    return []

def query_local_llm(prompt, max_words=45):
    try:
        url = "http://localhost:11434/api/generate"
        payload = { "model": "llama3:8b", "prompt": prompt, "stream": False, "options": { "temperature": 0.3 } }
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        analysis = response.json().get("response", "").strip()
        analysis = re.sub(r'^(.*:)\s*', '', analysis, flags=re.IGNORECASE | re.DOTALL)
        analysis = re.sub(r'[\*_`#]', '', analysis)
        analysis = re.sub(r'^\s*[\d-]+\.\s*', '', analysis)
        analysis = analysis.strip().replace('"', '')
        words = analysis.split()
        if len(words) > max_words: 
            end_index = analysis.rfind('.', 0, max_words * 6)
            if end_index != -1:
                analysis = analysis[:end_index + 1]
            else:
                analysis = " ".join(words[:max_words]) + "..."
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
    prompt = f"""Analyze the sentiment of the following financial news headline. Your response must be only one word: 'positive', 'negative', or 'neutral'.\n\nHeadline: "{t}"\nSentiment:"""
    sentiment = query_local_llm(prompt, max_words=2)
    if sentiment:
        cleaned_sentiment = sentiment.lower().strip().replace('.', '')
        if cleaned_sentiment in ['positive', 'negative', 'neutral']:
            return cleaned_sentiment
    print("      - LLM sentiment failed, falling back to keyword matching.")
    if any(k in t for k in config.POSITIVE_CUES):
        return "positive"
    if any(k in t for k in config.NEGATIVE_CUES):
        return "negative"
    return "uncertain"

def get_browser_headers(url=""):
    base_headers = { "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en;q=0.9", "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"', "Sec-Ch-Ua-Mobile": "?0", "Sec-Ch-Ua-Platform": '"macOS"', "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1", "Upgrade-Insecure-Requests": "1", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36" }
    if FAKE_USERAGENT_AVAILABLE:
        base_headers['User-Agent'] = UserAgent().random
    if "tickertape.in" in urlparse(url).netloc:
        base_headers.update({'x-tickertape-div': "7df92dc3-b097-421b-8c28-724d265a7098", 'Referer': "https://www.tickertape.in/", 'Sec-Fetch-Site': "same-site"})
    return base_headers

def make_request_with_retries(url, headers=None, timeout=45, retries=3, delay=5):
    request_headers = headers if headers is not None else get_browser_headers(url)
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=request_headers, timeout=timeout)
            if 400 <= response.status_code < 500:
                print(f"      - ❌ Client Error: {response.status_code}. Request is invalid. Not retrying.")
                response.raise_for_status() 
            if 500 <= response.status_code < 600:
                print(f"      - ⚠️ Server Error: {response.status_code}. The server is having issues. Retrying.")
                response.raise_for_status()
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"      - Attempt {attempt + 1}/{retries} failed for URL. Error: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"      - ❌ All {retries} retries failed for {url}.")
                raise
    return None

def wrap_text_pil(text, font, max_width):
    if not text:
        return []
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, cur, words = [], [], text.split()
    for w in words:
        tentative = " ".join(cur + [w]) if cur else w
        if draw.textbbox((0,0), tentative, font=font)[2] <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

def get_optimal_font_size(text, initial_size, max_width, max_height, font_path):
    font_size = int(initial_size)
    font = ImageFont.truetype(font_path, font_size)
    def get_text_dimensions(txt, fnt):
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        lines = wrap_text_pil(txt, fnt, max_width * 0.9)
        if not lines:
            return 0, 0
        h = sum(draw.textbbox((0,0), l, font=fnt)[3] for l in lines) + (len(lines) - 1) * (font_size * 0.2)
        w = max(draw.textbbox((0,0), l, font=fnt)[2] for l in lines) if lines else 0
        return w, h
    width, height = get_text_dimensions(text, font)
    while (height > max_height * 0.9 or width > max_width * 0.9) and font_size > 20:
        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)
        width, height = get_text_dimensions(text, font)
    return font

def create_gradient_image(size, color1, color2, direction='horizontal'):
    width, height = size
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    if direction == 'horizontal':
        mask = Image.new('L', (width, height))
        mask_data = []
        for x in range(width):
            mask_data.extend([int(255 * (x / width))] * height)
        mask.putdata(mask_data)
    else: # vertical
        mask = Image.new('L', (width, height))
        mask_data = []
        for y in range(height):
            mask_data.extend([int(255 * (y / height))] * width)
        mask.putdata(mask_data)
    
    base.paste(top, (0, 0), mask)
    return base

def wrap_text_for_subtitles(text, max_chars_per_line=40):
    text = text.strip()
    if not text:
        return ""
    words = text.split()
    lines, current_line = [], ""
    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= max_chars_per_line:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word
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
