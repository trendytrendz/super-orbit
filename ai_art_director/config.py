# ai_art_director/config.py
# v24.3.17 - Fixed English Font Selection

import os
import sys
from pathlib import Path

# --- 1. ABSOLUTE PATH ANCHORING ---
CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent
if SRC_DIR.name == "ai_art_director":
    ROOT_DIR = SRC_DIR.parent
else:
    ROOT_DIR = SRC_DIR

OUTPUT_DIR = ROOT_DIR / "outputs"
TMP_DIR = OUTPUT_DIR / "tmp"
ASSETS_DIR = ROOT_DIR / "assets"
MUSIC_DIR = ROOT_DIR / "music" 
# --- NEW DIRECTORY ---
CUSTOM_INPUT_DIR = ASSETS_DIR / "custom_input"

FALLBACK_BACKGROUND_DIR = ASSETS_DIR / "fallback_backgrounds"
FONT_DIR = ASSETS_DIR / "fonts"

AUDIO_VOICEOVERS_DIR = TMP_DIR / "voiceovers"
AUDIO_CACHE_DIR = TMP_DIR / "audio_cache"
AUDIO_FALLBACKS_DIR = TMP_DIR / "audio_fallbacks"
TMP_IMG_DIR = TMP_DIR / "images"

# --- SETTINGS ---
VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE = 1280, 720
VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT = 720, 1280
BG_COLOR = "#080C14"
TITLE_SLIDE_DURATION = 3.5

# --- FONT CONFIG (FIXED) ---
# 1. Define File Names
HINDI_FONT_NAME = "NotoSansDevanagari-Bold.ttf"
ENGLISH_FONT_NAME = "Roboto-Bold.ttf"

# 2. Define Absolute Paths
HINDI_FONT = str(FONT_DIR / HINDI_FONT_NAME)
DEFAULT_FONT = str(FONT_DIR / ENGLISH_FONT_NAME) # Strict mapping

# 3. Fallback (Only if file is truly missing, use system Arial)
if not os.path.exists(DEFAULT_FONT):
    DEFAULT_FONT = "Arial"

# --- THEMES ---
BASE_THEMES = [
    {"accent": "#00ACC1", "text": "#F0F4F8", "gradient_end": "#006064"}, 
    {"accent": "#66BB6A", "text": "#E8F5E9", "gradient_end": "#1B5E20"}, 
    {"accent": "#FFA726", "text": "#FFF8E1", "gradient_end": "#E65100"},
]

def get_chart_size(video_format: str) -> tuple:
    if video_format == 'landscape': return (1100, 550)
    return (680, 500)

# --- VOICE CONFIG (UPDATED FOR EDGE) ---
# --- VOICE CONFIG ---
# --- VOICE CONFIG ---
VOICE_CONFIG = {
    "en": {
        "edge_voice": "en-IN-NeerjaNeural",    # Try Neerja instead of Aashi
        "edge_rate": "+0%",                    # Keep explicit rate
        "azure_voice": "en-US-AvaNeural", 
        "google_voice": "en-US-Journey-F", 
        "gtts_lang": "en"
    },
    "hi": {
        "edge_voice": "hi-IN-SwaraNeural",     
        "edge_rate": "+10%",
        "azure_voice": "hi-IN-SwaraNeural", 
        "google_voice": "hi-IN-Neural2-A", 
        "gtts_lang": "hi"
    }
}
def get_voice_for_lang(lang: str = 'en') -> dict:
    return VOICE_CONFIG.get(lang, VOICE_CONFIG["en"])

# --- KEYS & FLAGS ---
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
DEV_MODE = os.getenv("DEV_MODE", "True").lower() == "true"

MAX_NEWS_ITEMS = 3
# Check env for model, default to qwen for codespaces
WHISPER_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# --- STORY THEMES ---
STORY_THEMES = {
    "news": {
        "intro_text": "Latest News: {company_name}", 
        "cta_text": "Stay updated with daily coverage!", 
        "cta_icons": ["like", "subscribe", "bell", "share"]
    },
    "deepdive": {
        "intro_text": "Deep Dive: {company_name}", 
        "cta_text": "Subscribe for more insights!", 
        "cta_icons": ["like", "subscribe", "comment", "share"] 
    },
    "comparison": {
        "intro_text": "Comparison Analysis", 
        "cta_text": "Which stock do you prefer? Vote now!", 
        "cta_icons": ["share", "like", "comment", "subscribe"] # Prioritized Share
    },
    "spotlight": {
        "intro_text": "Spotlight: {company_name}", 
        "cta_text": "Want more spotlights? Subscribe!", 
        "cta_icons": ["like", "subscribe", "bell", "share"]
    },
    
    # NEW: Custom News (Same as News but maybe different styling?)
    "custom_news": {
        "intro_text": "Exclusive Update: {company_name}", 
        "cta_text": "Follow for detailed analysis!", 
        "cta_icons": ["bell", "like", "subscribe", "share"]
    },
    
    # NEW: News Roundup
    "news_roundup": {
        "intro_text": "Market Roundup: Top Stories", 
        "cta_text": "Which stock are you tracking? Comment below!", 
        "cta_icons": ["comment", "like", "share", "subscribe"]
    },
     "stock360": {
        "intro_text": "Stock 360: {company_name}",
        "cta_text": "Buy, Sell or Hold? Comment now!",
        "cta_icons": ["like", "comment", "share", "subscribe"]
    },
    
    
    # NEW: TV Broadcast Format
    "custom_json": {
        "intro_text": "Breaking News", 
        "cta_text": "Subscribe now for daily market updates.", 
        "cta_icons": ["subscribe", "bell", "like", "share"] # Good for metadata, though CustomJson uses 'market_dashboard' theme for outro usually
    }
}

ICONS = {
    "positive": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>""",
    "negative": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path></svg>""",
    "neutral": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="16" y2="6"></line><line x1="8" y1="12" x2="16" y2="12"></line><line x1="8" y1="18" x2="16" y2="18"></line></svg>""",
    "like": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>""",
    "subscribe": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5.52 19c.64-2.2 1.84-3 3.22-3h6.52c1.38 0 2.58.8 3.22 3"/><circle cx="12" cy="10" r="3"/><circle cx="12" cy="12" r="10"/></svg>""",
    "bell": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>""",
    "comment": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>""",
    "poll": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>""",
    "share": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>"""
}

LOOKBACK_NEWS_DAYS = 7
IMPACT_KEYWORDS = ['profit', 'loss', 'revenue', 'growth', 'surge', 'plunge', 'record', 'acquisition', 'merger', 'dividend', 'bonus', 'split', 'results', 'quarterly']
SOURCE_BONUS = {
    'Yahoo Finance': 10,
    'Google News': 5,
    'MoneyControl': 8,
    'Economic Times': 8,
    'Trendlyne Announcements': 15
}

__version__ = "24.3.17"