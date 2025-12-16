# ai_art_director/story_runners_refactored/news_roundup_story.py
# v25.6.0 - Fixed Date Passing

import random
import requests
import os
from typing import Dict, List, Any
from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
from .. import config, video_renderer, narration_builder, data_fetcher
from .. import audio_generator as audio_gen_module
from .. import utils

class NewsRoundupStory(BaseStory):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        self.audio_generator = audio_gen_module.audio_generator

    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        if len(queries) < 2 or len(queries) > 5:
            print("❌ News Roundup requires 2 to 5 stocks.")
            return False
            
        print(f"🎬 Generating News Roundup for: {queries}")
        
        try:
            roundup_data = []
            
            # 1. Fetch Data
            for q in queries:
                print(f"   -> Fetching news for {q}...")
                nse, y_sym, disp = data_fetcher.resolve_symbol(q)
                
                # Fetch from ALL sources
                n1 = data_fetcher.fetch_yfinance_news(y_sym)
                n2 = data_fetcher.fetch_google_news(disp, nse, days=3)
                n3 = data_fetcher.fetch_moneycontrol_news(disp)
                n4 = data_fetcher.fetch_economic_times_news(disp)
                
                # Combine & Sort (Newest First)
                all_news = n1 + n2 + n3 + n4
                all_news.sort(key=lambda x: x['published'], reverse=True)
                
                # Dedupe
                unique_news = []
                seen = set()
                for n in all_news:
                    if n['title'] not in seen:
                        unique_news.append(n)
                        seen.add(n['title'])
                
                # LLM Ranking (Judge)
                top_news = data_fetcher.rank_news_with_llm(unique_news, disp)
                
                if top_news:
                    print(f"      ★ Selected Story 1: {top_news[0]['title']}")
                else:
                    print(f"      ⚠️ No news found for {q}")

                logo = data_fetcher.fetch_company_logo(y_sym)
                
                roundup_data.append({
                    "display": disp,
                    "news": top_news,
                    "logo": logo
                })
            
            # 2. Build Slides
            slides = []
            all_logos = [d['logo'] for d in roundup_data]
            all_names = [d['display'] for d in roundup_data]
            
            # Intro Headlines
            all_headlines = []
            for d in roundup_data:
                if d['news']: all_headlines.append(d['news'][0]['title'])
                else: all_headlines.append("No major updates.")

            # Slide 1: Intro (Grid)
            slides.append({
                'type': 'intro',
                'key': 'intro',
                'text': "Market Roundup",
                'logos': all_logos,
                'names': all_names,
                'headlines': all_headlines
            })
            
            # Slide 2..N: Glass Cards
            slide_counter = 0
            for item in roundup_data:
                company_name = item['display']
                company_logo = item['logo']
                
                if item['news']:
                    for news_item in item['news']:
                        headline = news_item['title']
                        source_name = news_item.get('source', 'News')
                        image_url = news_item.get('image')
                        pub_date = news_item.get('published') # <--- CRITICAL DATA POINT
                        
                        # Download Image
                        local_image_path = None
                        if image_url:
                            try:
                                ext = 'jpg' if '.jpg' in image_url else 'png'
                                fname = f"news_thumb_{slide_counter}_{random.randint(100,999)}.{ext}"
                                local_path = config.TMP_IMG_DIR / fname
                                
                                # Basic headers to avoid 403
                                headers = {'User-Agent': 'Mozilla/5.0'}
                                r = requests.get(image_url, headers=headers, timeout=5)
                                if r.status_code == 200:
                                    with open(local_path, 'wb') as f: f.write(r.content)
                                    local_image_path = str(local_path)
                                    print(f"      - 🖼️ Downloaded News Image: {fname}")
                            except Exception as e:
                                print(f"      - ⚠️ Failed to download news image: {e}")

                        slides.append({
                            'type': 'glass_news', 
                            'key': f'news_{slide_counter}',
                            'company': company_name,
                            'logo': company_logo,
                            'text': headline,
                            'source': source_name,
                            'news_image_path': local_image_path,
                            'published': pub_date # <--- CRITICAL PASS TO RENDERER
                        })
                        slide_counter += 1
                else:
                    # Fallback
                    slides.append({
                        'type': 'glass_news',
                        'key': f'news_{slide_counter}',
                        'company': company_name,
                        'logo': company_logo,
                        'text': "No major headlines today.",
                        'source': "Market Data",
                        'published': utils.now_ist() # Default to today
                    })
                    slide_counter += 1
            
            # Slide Last: CTA
            slides.append({'type': 'cta', 'key': 'cta'})
            
            # 3. Assets
            assets = self.background_manager.fetch_contextual_backgrounds(
                "Stock Market", "Financial News", len(slides), video_format
            )
            assets['logos'] = all_logos
            
            # 4. Narration
            english_script = narration_builder.build_roundup_script(roundup_data)
            audio_script = narration_builder.build_audio_script(english_script, self.lang)
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script, self.lang)
            
            # 5. Render
            video_renderer.make_video(
                slides, audio_paths, "Market Roundup", "news_roundup", video_format, 
                out_path, assets, self.theme, self.icon_svg, self.lang
            )
            return True

        except Exception as e:
            print(f"❌ Roundup Error: {e}")
            import traceback; traceback.print_exc()
            return False