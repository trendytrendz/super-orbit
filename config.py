# config.py
# v20.2.1 - Fixed missing BASE_THEMES and complete configuration

import os
from pathlib import Path

# Version
__version__ = "20.2.1"

# Video Dimensions & Timings
VIDEO_W_LANDSCAPE, VIDEO_H_LANDSCAPE = 1280, 720
VIDEO_W_PORTRAIT, VIDEO_H_PORTRAIT = 720, 1280
BG_COLOR = "#080C14"
TITLE_SLIDE_DURATION = 3.0

# Font Discovery with better validation
def get_available_fonts():
    """Get available fonts with proper validation"""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
        #"/System/Library/Fonts/Arial.ttf",
        #"/System/Library/Fonts/Arial Bold.ttf",
        str(Path.home() / "Library" / "Fonts" / "Arial.ttf"),
    ]
    available_fonts = [f for f in font_paths if os.path.exists(f)]
    
    if not available_fonts:
        print("⚠️  WARNING: No system fonts found. Video generation may fail.")
    
    return available_fonts

FONT_PATHS = get_available_fonts()

# Language configurations
LANGUAGES = {
    "en": {
        "azure_voice": "en-IN-NeerjaNeural",
        "gtts_lang": "en"
    },
    "hi": {
        "azure_voice": "hi-IN-SwaraNeural", 
        "gtts_lang": "hi"
    }
}

# Central repository for all SVG icon data.
ICONS = {
    "positive": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="m280-400 200-200 200 200H280Z"/></svg>',
    "negative": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M480-560 280-760h400L480-560Z"/></svg>',
    "neutral": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M200-450h560v-60H200v60Z"/></svg>',
    "uncertain": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M200-450h560v-60H200v60Z"/></svg>',
    "like": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M720-120H280v-520l280-280 50 50q7 7 11.5 19t4.5 23v14l-44 214h258q32 0 56 24t24 56v80q0 7-2 15t-4 15L794-168q-9 20-30 34t-44 14Zm-360-80h360l120-280v-80H480l54-260-174 174v446Zm0 80Z"/></svg>',
    "comment": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M240-400h480v-80H240v80Zm0-120h480v-80H240v80Zm0-120h480v-80H240v80ZM80-80v-720q0-33 23.5-56.5T160-880h640q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H240L80-80Zm80-200h640v-480H160v525l40-45Z"/></svg>',
    "subscribe": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h640q33 0 56.5 23.5T880-720v480q0 33-23.5 56.5T800-160H160Zm0-80h640v-480H160v480Zm160-160h320v-80H320v80Zm0-120h320v-80H320v80ZM160-240v-480 480Z"/></svg>',
    "bell": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M200-80v-40q0-33 11-62.5T241-239l219-219q28-28 44-64.5t16-76.5v-120q0-83 58.5-141.5T640-800h-3q-7 0-13 .5t-13 1.5q-13 3-25 9t-23 15.5q-11 9.5-22 22t-19 28.5q-8 16-12.5 33.5T420-640v40h-80v-40q0-30 11-57t31-48q20-21 44.5-35.5T511-791q27-10 56-14.5t59-4.5h3q91 0 155.5 64.5T840-560v120q0 40-16.5 76.5T779-299L560-80H200Z"/></svg>',
    "poll": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M320-240v-480h80v480h-80Zm220 0v-240h80v240h-80Zm220 0v-360h80v360h-80ZM160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h640q33 0 56.5 23.5T880-720v480q0 33-23.5 56.5T800-160H160Z"/></svg>',
    "share": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path d="M720-80q-50 0-85-35t-35-85q0-7 1-14.5t3-13.5L323-400q-22 20-51 31.5T200-356q-66 0-113-47t-47-113q0-66 47-113t113-47q38 0 70 17.5t54 46.5l281-163q-2-6-3-13t-1-14q0-50 35-85t85-35q50 0 85 35t35 85q0 50-35 85t-85 35q-38 0-70-17.5T596-748L315-585q2 6 3 13t1 14q0 7-1 13.5T315-531l281 163q22-29 54-46.5t70-17.5q50 0 85 35t35 85q0 50-35 85t-85 35Zm0-640q17 0 28.5-11.5T760-760q0-17-11.5-28.5T720-800q-17 0-28.5 11.5T680-760q0 17 11.5 28.5T720-720ZM200-440q17 0 28.5-11.5T240-480q0-17-11.5-28.5T200-520q-17 0-28.5 11.5T160-480q0 17 11.5 28.5T200-440Zm520 280q17 0 28.5-11.5T760-200q0-17-11.5-28.5T720-240q-17 0-28.5 11.5T680-200q0 17 11.5 28.5T720-160Z"/></svg>'
}

# Central theme definitions for each story type.
STORY_THEMES = {
    "news": { "intro_text": "{company_name}\nDaily Briefing", "cta_text": "Subscribe for daily updates", "cta_icons": ["like", "subscribe", "bell"] },
    "deepdive": { "intro_text": "{company_name}\nStock Deep Dive", "cta_text": "Like & Subscribe for more deep dives", "cta_icons": ["like", "comment", "subscribe", "share"] },
    "comparison": { "intro_text": "Head-to-Head", "cta_text": "Which stock wins? Vote in the comments!", "cta_icons": ["like", "comment", "poll", "share"] },
    "spotlight": { "intro_text": "{company_name}\nInvestor Spotlight", "cta_text": "Like & Subscribe for more case studies", "cta_icons": ["like", "comment", "subscribe", "share"] }
}

# --- News & Other Configs ---
LOOKBACK_NEWS_DAYS, MAX_NEWS_ITEMS = 7, 3
IMPACT_KEYWORDS = ["profit", "loss", "earnings", "revenue", "deal", "order", "appoints", "launches", "acquires", "merger", "results", "guidance", "upgrade", "downgrade", "stake"]
POSITIVE_CUES = ["buyback", "bonus", "split", "order win", "upgrade", "raises guidance", "dividend", "approval", "record order", "profit", "acquires", "launches"]
NEGATIVE_CUES = ["resigns", "resignation", "loss", "downgrade", "penalty", "pledge", "fraud", "default", "investigation"]
SOURCE_BONUS = {"Yahoo Finance": 20, "MoneyControl": 15, "Economic Times": 10, "Google News": 0, "Trendlyne Announcements": 25}

# BASE_THEMES - RESTORED FROM ORIGINAL CONFIG
BASE_THEMES = [
    {"accent": "#00ACC1", "text": "#F0F4F8", "gradient_end": "#006064"}, 
    {"accent": "#66BB6A", "text": "#E8F5E9", "gradient_end": "#1B5E20"}, 
    {"accent": "#FFA726", "text": "#FFF8E1", "gradient_end": "#E65100"}, 
    {"accent": "#EC407A", "text": "#FCE4EC", "gradient_end": "#880E4F"}, 
    {"accent": "#AB47BC", "text": "#F3E5F5", "gradient_end": "#4A148C"}
]

# Configuration validation function
def validate_configuration():
    """Validate all configuration and dependencies"""
    errors = []
    warnings = []
    
    print("\n🔧 CONFIGURATION VALIDATION")
    print("=" * 50)
    
    # Check required directories
    required_dirs = [
        "outputs",
        "outputs/tmp", 
        "music"
    ]
    
    script_dir = os.path.dirname(os.path.realpath(__file__))
    for dir_path in required_dirs:
        full_path = os.path.join(script_dir, dir_path)
        try:
            os.makedirs(full_path, exist_ok=True)
            print(f"✅ Directory: {dir_path}")
        except Exception as e:
            errors.append(f"Cannot create directory {dir_path}: {e}")
    
    # Check fonts
    if not FONT_PATHS:
        errors.append("No fonts available. Install Arial or Helvetica.")
    else:
        print(f"✅ Fonts: {len(FONT_PATHS)} available")
    
    # Check environment variables
    required_env_vars = ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"]
    for env_var in required_env_vars:
        if not os.getenv(env_var):
            warnings.append(f"Environment variable {env_var} not set - TTS quality will be lower")
        else:
            print(f"✅ Environment: {env_var}")
    
    # Check API keys
    if not os.getenv("PEXELS_API_KEY"):
        warnings.append("PEXELS_API_KEY not set - background images will be limited")
    else:
        print("✅ Pexels API: Available")
    
    # Check Python dependencies
    try:
        import moviepy
        print("✅ MoviePy: Available")
    except ImportError:
        errors.append("MoviePy not installed - run: pip install moviepy")
    
    try:
        import PIL
        print("✅ PIL: Available") 
    except ImportError:
        errors.append("PIL not installed - run: pip install Pillow")
    
    # Check critical configuration constants
    if not BASE_THEMES:
        errors.append("BASE_THEMES not defined - video theming will fail")
    else:
        print(f"✅ Themes: {len(BASE_THEMES)} available")
    
    if not STORY_THEMES:
        errors.append("STORY_THEMES not defined - story configuration missing")
    else:
        print(f"✅ Story Types: {len(STORY_THEMES)} configured")
    
    # Report results
    print("=" * 50)
    
    if warnings:
        print(f"⚠️  WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   - {warning}")
    
    if errors:
        print(f"❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"   - {error}")
        return False
    elif warnings:
        print("✅ Configuration validated with warnings")
        return True
    else:
        print("✅ Configuration fully validated")
        return True

# Run validation if this file is executed directly
if __name__ == "__main__":
    validate_configuration()
