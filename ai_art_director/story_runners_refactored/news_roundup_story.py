# ai_art_director/story_runners_refactored/news_roundup_story.py
# v25.5.0 - Logging & Intro Headlines

import random
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
                
                # --- NEW: Fetch from ALL sources ---
                # 1. Yahoo
                n1 = data_fetcher.fetch_yfinance_news(y_sym)
                # 2. Google
                n2 = data_fetcher.fetch_google_news(disp, nse, days=3)
                # 3. MoneyControl
                n3 = data_fetcher.fetch_moneycontrol_news(disp)
                # 4. Economic Times
                n4 = data_fetcher.fetch_economic_times_news(disp)
                
                # Combine
                all_news = n1 + n2 + n3 + n4
                
                # --- NEW: Sorting Logic (Freshness First) ---
                # Sort by 'published' date descending (Newest first)
                all_news.sort(key=lambda x: x['published'], reverse=True)
                
                # Dedupe (Keep the newest version if duplicate titles exist)
                unique_news = []
                seen = set()
                for n in all_news:
                    if n['title'] not in seen:
                        unique_news.append(n)
                        seen.add(n['title'])
                
                # Filter Top Story
                top_news = unique_news[:2] 
                
                # LOGGING
                if top_news:
                    print(f"      ★ Selected Story 1 ({top_news[0]['source']}): {top_news[0]['title']}")
                    if len(top_news) > 1:
                        print(f"      ★ Selected Story 2 ({top_news[1]['source']}): {top_news[1]['title']}")
                else:
                    print(f"      ⚠️ No news found for {q}")

                # Fetch Logo
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
            
            # Extract headlines for Intro Card
            all_headlines = []
            for d in roundup_data:
                if d['news']:
                    all_headlines.append(d['news'][0]['title'])
                else:
                    all_headlines.append("No major updates today.")

            # Slide 1: Intro (Grid)
            slides.append({
                'type': 'intro',
                'key': 'intro',
                'text': "Market Roundup",
                'logos': all_logos,
                'names': all_names,
                'headlines': all_headlines # Passing Headlines for Intro Grid
            })
            
            # Slide 2..N: Glass Cards
            # Slide 2..N: Glass Cards (Nested Loop)
            # Strategy: Create 1 slide per news item
            
            slide_counter = 0
            for item in roundup_data:
                company_name = item['display']
                company_logo = item['logo']
                
                if item['news']:
                    # Iterate through available news (up to 2)
                    for news_item in item['news']:
                        headline = news_item['title']
                        source_name = news_item.get('source', 'News')
                        
                        slides.append({
                            'type': 'glass_news', 
                            'key': f'news_{slide_counter}',
                            'company': company_name,
                            'logo': company_logo,
                            'text': headline,
                            'source': source_name
                        })
                        slide_counter += 1
                else:
                    # Fallback if NO news found for a stock (Rare but possible)
                    slides.append({
                        'type': 'glass_news',
                        'key': f'news_{slide_counter}',
                        'company': company_name,
                        'logo': company_logo,
                        'text': "No major headlines today.",
                        'source': "Market Data"
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