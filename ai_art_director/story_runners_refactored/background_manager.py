import os
import random
import requests
from pathlib import Path
from .. import config

class BackgroundManager:
    def __init__(self):
        self.tmp_dir = str(config.TMP_IMG_DIR)
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.api_key = config.PEXELS_API_KEY
        self.has_valid_key = self.api_key and isinstance(self.api_key, str) and len(self.api_key) > 10

    def fetch_smart_media(self, query, media_type="video"):
        """
        Smart router: Tries to fetch Video first (Priority 1), falls back to Image.
        """
        if media_type == "video" and self.has_valid_key:
            vid_path = self.fetch_vertical_video(query)
            if vid_path: return vid_path
        
        # Fallback to image
        res = self.fetch_contextual_backgrounds("", "", 1, "portrait", [query])
        if res.get('bg_images'): return res['bg_images'][0]
        return None

    def fetch_vertical_video(self, query):
        """
        PRIORITY 1: Fetch Pexels Video (Vertical/Portrait).
        """
        print(f"      🎥 Searching Pexels Video for: '{query}'")
        try:
            headers = {'Authorization': self.api_key}
            url = "https://api.pexels.com/videos/search"
            params = {
                'query': query,
                'orientation': 'portrait',
                'per_page': 5, # Fetch a few to filter
                'size': 'medium' # Save bandwidth
            }
            
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code != 200: return None
            
            data = r.json()
            videos = data.get('videos', [])
            
            if not videos: return None
            
            # Pick a random video from top 5
            chosen_video = random.choice(videos)
            
            # Find the best MP4 file (prefer HD but not 4k, closest to 720/1080 width)
            best_file = None
            for vf in chosen_video['video_files']:
                # Prefer HD (width ~720-1080)
                if vf['file_type'] == 'video/mp4' and 500 < vf['width'] < 1200:
                    best_file = vf
                    break
            
            # Fallback to any mp4
            if not best_file:
                best_file = next((v for v in chosen_video['video_files'] if v['file_type'] == 'video/mp4'), None)
                
            if best_file:
                download_url = best_file['link']
                # Unique name
                fname = f"vid_{query.replace(' ','_')}_{chosen_video['id']}.mp4"
                save_path = os.path.join(self.tmp_dir, fname)
                
                # Check cache
                if os.path.exists(save_path): return save_path
                
                # Stream Download
                print(f"      ⬇️  Downloading Video ({best_file['width']}x{best_file['height']})...")
                with requests.get(download_url, stream=True) as r:
                    r.raise_for_status()
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return save_path
                
        except Exception as e:
            print(f"      ⚠️ Video Fetch Error: {e}")
        return None

    def fetch_contextual_backgrounds(self, company_name, summary, num_needed, video_format, specific_queries=None):
        base_keywords = ["finance", "technology", "abstract", "business", "cityscape", "network"]
        random.shuffle(base_keywords)
        keywords = (specific_queries or []) + base_keywords
        
        if self.has_valid_key:
            return {'bg_images': self._search_images_direct(keywords, num_needed, video_format)}
        return self._create_color_backgrounds(num_needed, video_format)

    def _search_images_direct(self, keywords, max_images, video_format):
        paths = []
        headers = {'Authorization': self.api_key}
        for q in keywords:
            if len(paths) >= max_images: break
            try:
                url = f"https://api.pexels.com/v1/search?query={q}&per_page=15&orientation={'portrait' if video_format=='portrait' else 'landscape'}"
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    photos = r.json().get('photos', [])
                    random.shuffle(photos)
                    for p in photos:
                        if len(paths) >= max_images: break
                        save_path = os.path.join(self.tmp_dir, f"bg_{q}_{p['id']}.jpg")
                        if self._download(p['src']['large2x'], save_path): paths.append(save_path)
            except: pass
        return paths

    def _download(self, url, path):
        try:
            with open(path, 'wb') as f: f.write(requests.get(url).content)
            return True
        except: return False

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
            random.shuffle(schemes) 
            
            for i in range(num_needed):
                colors = schemes[i % len(schemes)]
                
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