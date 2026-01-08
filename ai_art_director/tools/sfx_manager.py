import os
import requests
from ai_art_director.config import SFX_DIR

def download_sfx():
    os.makedirs(SFX_DIR, exist_ok=True)
    
    # Free sounds from credible sources (Placeholders)
    sounds = {
        "swoosh.mp3": "https://freesound.org/data/previews/614/614603_11086036-lq.mp3", # Example placeholder
        "pop.mp3": "https://freesound.org/data/previews/411/411642_5121236-lq.mp3",
        "news_intro.mp3": "https://freesound.org/data/previews/179/179854_1549729-lq.mp3"
    }
    
    print("🔊 Downloading SFX Assets...")
    for name, url in sounds.items():
        path = os.path.join(SFX_DIR, name)
        if not os.path.exists(path):
            try:
                # Mocking the download for safety as direct hotlinks can expire. 
                # In production, use local assets. We will create dummy files if download fails.
                try:
                    r = requests.get(url, timeout=5)
                    if r.status_code == 200:
                        with open(path, 'wb') as f: f.write(r.content)
                        print(f"   ✅ Downloaded {name}")
                        continue
                except: pass
                
                # Fallback: Create silent file to prevent crash
                print(f"   ⚠️ Creating placeholder for {name}")
                with open(path, 'wb') as f: f.write(b'\x00' * 1024)
            except Exception as e:
                print(f"   ❌ Error {name}: {e}")

if __name__ == "__main__":
    download_sfx()
