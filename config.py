# config.py
import os

# Version
__version__ = "15.0.9"

# Video Dimensions & Timings
VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE = 1280, 720
VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT = 720, 1280
BG_COLOR = "#080C14"
TITLE_SLIDE_DURATION = 3.0 # Duration in seconds for silent title slides

# Font Discovery
FONT_PATHS = [
    f for f in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Verdana.ttf",
        "C:\\Windows\\Fonts\\verdana.ttf"
    ] if os.path.exists(f)
]

# News & Scoring Configuration
LOOKBACK_NEWS_DAYS = 7
MAX_NEWS_ITEMS = 3
IMPACT_KEYWORDS = [
    "profit", "loss", "earnings", "revenue", "deal", "order", "appoints",
    "launches", "acquires", "merger", "results", "guidance", "upgrade",
    "downgrade", "stake"
]
POSITIVE_CUES = [
    "buyback", "bonus", "split", "order win", "upgrade", "raises guidance",
    "dividend", "approval", "record order", "profit", "acquires", "launches"
]
NEGATIVE_CUES = [
    "resigns", "resignation", "loss", "downgrade", "penalty", "pledge",
    "fraud", "default", "investigation"
]
SOURCE_BONUS = {
    "Yahoo Finance": 20,
    "MoneyControl": 15,
    "Economic Times": 10,
    "Google News": 0,
    "Trendlyne Announcements": 25
}

# Base Theme Palettes
BASE_THEMES = [
    {"accent": "#00ACC1", "text": "#F0F4F8"},
    {"accent": "#4CAF50", "text": "#E8F5E9"},
    {"accent": "#FFC107", "text": "#FFF8E1"},
    {"accent": "#E91E63", "text": "#FCE4EC"},
    {"accent": "#9C27B0", "text": "#F3E5F5"}
]
