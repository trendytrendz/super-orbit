# story_runners_refactored/background_manager.py
# v24.2.25 - Absolute Path Fix & Direct API

import os
import random
import requests
from pathlib import Path
from .. import config

class BackgroundManager:
    def __init__(self):
        # CRITICAL FIX: Use the absolute path from config
        self.tmp_dir = str(config.TMP_IMG_DIR)
        
        # Ensure the directory exists
        os.makedirs(self.tmp_dir, exist_ok=True)
        
        self.api_key = config.PEXELS_API_KEY
        
        # Check validity
        self.has_valid_key = self.api_key and isinstance(self.api_key, str) and len(self.api_key) > 10

    def fetch_contextual_backgrounds(self, company_name, summary, num_needed, video_format, specific_queries=None):
        """
        Fetches backgrounds using direct HTTP requests to Pexels.
        Saves files to the absolute config.TMP_IMG_DIR.
        """
        # 1. Define Keywords
        keywords = [
            "finance", "technology", "abstract", "business", 
            "cityscape", "network", "stock market", "skyscraper"
        ]
        
        if specific_queries:
            keywords = specific_queries + keywords

        # 2. Attempt Fetch
        if self.has_valid_key:
            print(f"\n   -> Fetching {num_needed} backgrounds (Absolute Path)...")
            images = self._search_images_direct(keywords, num_needed, video_format)
            
            if images and len(images) >= 1:
                # If we didn't get enough, fill the rest with gradients
                if len(images) < num_needed:
                    needed = num_needed - len(images)
                    print(f"   -> Filling {needed} missing slots with gradients.")
                    gradients = self._create_color_backgrounds(needed, video_format)
                    images.extend(gradients['bg_images'])
                    
                return {'bg_images': images, 'bg_credit': "Photos by Pexels"}
        else:
            print("   -> ⚠️ Pexels API Key missing/invalid. Skipping API.")
        
        # 3. Fallback to Gradients
        return self._create_color_backgrounds(num_needed, video_format)

    def _search_images_direct(self, keywords, max_images, video_format):
        paths = []
        orientation = 'portrait' if video_format == 'portrait' else 'landscape'
        headers = {'Authorization': self.api_key}
        
        for q in keywords:
            if len(paths) >= max_images: break
            
            try:
                print(f"      - 🔎 Searching: '{q}'")
                url = "https://api.pexels.com/v1/search"
                params = {
                    'query': q,
                    'per_page': 15,
                    'orientation': orientation,
                    'size': 'large'
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 401:
                    print("      - ❌ Pexels Unauthorized (Check API Key)")
                    self.has_valid_key = False 
                    break
                
                if response.status_code != 200:
                    print(f"      - ⚠️ API Status: {response.status_code}")
                    continue
                    
                data = response.json()
                photos = data.get('photos', [])
                
                if not photos: continue
                
                for photo in photos:
                    if len(paths) >= max_images: break
                    
                    img_url = photo['src']['large2x']
                    
                    # CRITICAL FIX: Construct Absolute Path
                    clean_q = "".join(x for x in q if x.isalnum())
                    filename = f"bg_{len(paths)}_{clean_q}.jpg"
                    save_path = os.path.join(self.tmp_dir, filename)
                    
                    # Avoid re-downloading if exists
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 1024:
                        paths.append(save_path)
                        continue

                    if self._download(img_url, save_path):
                        paths.append(save_path)
                                
            except Exception as e:
                print(f"      - ⚠️ Search Error for '{q}': {e}") 
                continue
                
        return paths

    def _download(self, url, path):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(path, 'wb') as f: f.write(r.content)
                return True
        except: pass
        return False

    def _create_color_backgrounds(self, num_needed, video_format):
        print(f"   -> 🎨 Creating {num_needed} gradient backgrounds.")
        try:
            from PIL import Image, ImageDraw
            w, h = (720, 1280) if video_format == 'portrait' else (1280, 720)
            paths = []
            
            schemes = [
                ("#0F2027", "#203A43", "#2C5364"), # Deep Space
                ("#141E30", "#243B55", "#243B55"), # Royal Blue
                ("#000000", "#0f9b0f", "#000000"), # Matrix
                ("#232526", "#414345", "#414345"), # Midnight
                ("#1A2980", "#26D0CE", "#26D0CE")  # Aqua
            ]
            
            for i in range(num_needed):
                colors = schemes[i % len(schemes)]
                
                # CRITICAL FIX: Construct Absolute Path
                filename = f"fallback_{i}_{random.randint(0,9999)}.jpg"
                p = os.path.join(self.tmp_dir, filename)
                
                img = Image.new("RGB", (w, h), colors[0])
                draw = ImageDraw.Draw(img)
                
                c_start = tuple(int(colors[0].lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
                c_end = tuple(int(colors[1].lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
                
                for y in range(h):
                    r = int(c_start[0] + (c_end[0] - c_start[0]) * y / h)
                    g = int(c_start[1] + (c_end[1] - c_start[1]) * y / h)
                    b = int(c_start[2] + (c_end[2] - c_start[2]) * y / h)
                    draw.line([(0, y), (w, y)], fill=(r, g, b))
                    
                img.save(p)
                paths.append(p)
                
            return {'bg_images': paths, 'bg_credit': None}
        except Exception as e:
            print(f"   -> ❌ Gradient error: {e}")
            return {'bg_images': [], 'bg_credit': None}