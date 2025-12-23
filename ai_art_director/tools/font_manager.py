#/tools/font_manager.py
import os
import requests
from ai_art_director.config import ASSETS_DIR

def download_fonts():
    font_dir = os.path.join(ASSETS_DIR, "fonts")
    os.makedirs(font_dir, exist_ok=True)
    
    # Modern Google Fonts (Direct TTF links)
    fonts = {
        "Oswald-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald-Bold.ttf",
        "Montserrat-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf",
        "Montserrat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Regular.ttf",
        "Lato-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Bold.ttf",
        "Merriweather-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Bold.ttf",
        "BebasNeue-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf"
    }
    
    print(f"⬇️  Downloading Modern Fonts to {font_dir}...")
    
    for name, url in fonts.items():
        path = os.path.join(font_dir, name)
        if not os.path.exists(path):
            try:
                print(f"   - Fetching {name}...")
                r = requests.get(url)
                if r.status_code == 200:
                    with open(path, 'wb') as f: f.write(r.content)
            except Exception as e:
                print(f"   ❌ Failed {name}: {e}")
        else:
            print(f"   - {name} exists.")

if __name__ == "__main__":
    download_fonts()
