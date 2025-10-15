# config.py
import os

# Version
__version__ = "13.1.8"

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

# Outro Icons (SVG)
OUTRO_ICONS = {
    "like": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M720-120H280v-520l280-280 50 50q7 7 11.5 19t4.5 23v14l-44 214h258q32 0 56 24t24 56v80q0 7-2 15t-4 15L794-168q-9 20-30 34t-44 14Zm-360-80h360l120-280v-80H480l54-260-174 174v446Zm0 80Z"/></svg>',
    "comment": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M240-400h480v-80H240v80Zm0-120h480v-80H240v80Zm0-120h480v-80H240v80ZM80-80v-720q0-33 23.5-56.5T160-880h640q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H240L80-80Zm80-200h640v-480H160v525l40-45Z"/></svg>',
    "share": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M720-80q-50 0-85-35t-35-85q0-7 1-14.5t3-13.5L322-382q-18 13-40 21t-42 8q-50 0-85-35t-35-85q0-50 35-85t85-35q20 0 40 7.5t38 20.5l282-164q-2-6-2.5-12.5T600-720q0-50 35-85t85-35q50 0 85 35t35 85q0 50-35 85t-85 35q-20 0-38-7.5t-40-20.5L340-542q2 6 2.5 12.5t.5 13.5q0 7-1 14t-3 14l282 164q18-13 40-21t42-8q50 0 85 35t35 85q0 50-35 85t-85 35Zm0-640q17 0 28.5-11.5T760-760q0-17-11.5-28.5T720-800q-17 0-28.5 11.5T680-760q0-17 11.5 28.5T720-720ZM240-440q17 0 28.5-11.5T280-480q0-17-11.5-28.5T240-520q-17 0-28.5 11.5T200-480q0-17 11.5 28.5T240-440Zm480 280q17 0 28.5-11.5T760-200q0-17-11.5-28.5T720-240q-17 0-28.5 11.5T680-200q0-17 11.5 28.5T720-160Z"/></svg>'
}

# Base Theme Palettes
BASE_THEMES = [
    {"accent": "#00ACC1", "text": "#F0F4F8"},
    {"accent": "#4CAF50", "text": "#E8F5E9"},
    {"accent": "#FFC107", "text": "#FFF8E1"},
    {"accent": "#E91E63", "text": "#FCE4EC"},
    {"accent": "#9C27B0", "text": "#F3E5F5"}
]
