import os
import requests
import sys
import platform
from ai_art_director.config import ROOT_DIR, ASSETS_DIR, MUSIC_DIR, OUTPUT_DIR, TMP_DIR, CUSTOM_INPUT_DIR
from ai_art_director.tools import asset_factory

REQUIRED_DIRS = [ASSETS_DIR, os.path.join(ASSETS_DIR, "fonts"), os.path.join(ASSETS_DIR, "themes"), CUSTOM_INPUT_DIR, MUSIC_DIR, OUTPUT_DIR, TMP_DIR, os.path.join(TMP_DIR, "voiceovers"), os.path.join(TMP_DIR, "images")]
FONTS_TO_FETCH = {
    "Oswald-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/oswald/static/Oswald-Bold.ttf",
    "Montserrat-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/static/Montserrat-Bold.ttf",
    "Montserrat-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/static/Montserrat-Regular.ttf",
    "Lato-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/Lato-Bold.ttf",
    "Merriweather-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/merriweather/Merriweather-Bold.ttf",
    "BebasNeue-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    "NotoSansDevanagari-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari-Bold.ttf"
}
SAMPLE_MUSIC_URL = "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Tours/Enthusiast/Tours_-_01_-_Enthusiast.mp3"

def check_system_environment():
    os_name = platform.system()
    print(f"🖥️  System Check: Running on {os_name}")

def create_folders():
    for d in REQUIRED_DIRS:
        if not os.path.exists(d):
            try: os.makedirs(d, exist_ok=True)
            except: pass

def download_resource(url, path, description):
    if os.path.exists(path) and os.path.getsize(path) > 1000: return 
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            with open(path, 'wb') as f: f.write(r.content)
            print(f"   ✅ Installed: {description}")
    except: pass

def ensure_assets():
    print("🎨 Checking Critical Assets...")
    font_dir = os.path.join(ASSETS_DIR, "fonts")
    for filename, url in FONTS_TO_FETCH.items():
        download_resource(url, os.path.join(font_dir, filename), filename)

    music_path = os.path.join(MUSIC_DIR, "market_beat.mp3")
    if not os.path.exists(MUSIC_DIR) or not os.listdir(MUSIC_DIR):
        download_resource(SAMPLE_MUSIC_URL, music_path, "Sample Background Music")

    # FORCE RUN ASSET FACTORY
    print("   ⚙️  Running Asset Factory...")
    try:
        asset_factory.draw_breaking_bar()
        asset_factory.draw_market_dashboard()
        asset_factory.draw_glass_stack()
        asset_factory.draw_neo_brutalist()
        asset_factory.draw_split_deck()
        asset_factory.draw_vertical_ticker()
        asset_factory.draw_others()
        print("   ✅ Visual Templates Generated.")
    except Exception as e:
        print(f"   ❌ Asset Factory Failed: {e}")

def run_checks():
    check_system_environment()
    create_folders()
    ensure_assets()

if __name__ == "__main__":
    run_checks()