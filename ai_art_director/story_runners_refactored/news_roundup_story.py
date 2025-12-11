# story_runners_refactored/news_roundup_story.py
# v25.1.0 - Multi-Stock Rapid Fire

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
            
            # 1. Fetch Data for all stocks
            for q in queries:
                print(f"   -> Fetching news for {q}...")
                nse, y_sym, disp = data_fetcher.resolve_symbol(q)
                
                # Fetch News & Price
                news = data_fetcher.fetch_yfinance_news(y_sym) + data_fetcher.fetch_google_news(disp, nse, days=3)
                
                # Sort by freshness and relevance
                # Simple dedupe
                unique_news = []
                seen_titles = set()
                for n in news:
                    if n['title'] not in seen_titles:
                        unique_news.append(n)
                        seen_titles.add(n['title'])
                
                # Take top 2 most recent/relevant
                top_news = unique_news[:2]
                
                # Logo
                logo = data_fetcher.fetch_company_logo(y_sym)
                
                roundup_data.append({
                    "display": disp,
                    "news": top_news,
                    "logo": logo
                })
            
            # 2. Build Slides
            slides = []
            
            # Slide 1: Agenda (Grid of Companies) - Reuse Comparison Intro Logic!
            all_logos = [d['logo'] for d in roundup_data]
            all_names = [d['display'] for d in roundup_data]
            
            slides.append({
                'type': 'intro', # Will use the Card Grid we built!
                'key': 'intro',
                'text': "Market Roundup",
                'logos': all_logos,
                'names': all_names
            })
            
            # Slide 2..N: News Items
            # Strategy: 1 Slide per Stock containing the best headline
            for i, item in enumerate(roundup_data):
                if item['news']:
                    headline = item['news'][0]['title']
                    slides.append({
                        'type': 'news',
                        'key': f'stock_{i}',
                        'text': f"{item['display']}\n\n{headline}", # Stack Name + News
                        'icon': utils.classify_impact(headline)
                    })
            
            # Slide Last: CTA
            slides.append({'type': 'cta', 'key': 'cta'})
            
            # 3. Assets
            # We need general "Stock Market" backgrounds
            assets = self.background_manager.fetch_contextual_backgrounds(
                "Stock Market", "Financial News", len(slides), video_format
            )
            # Pass logos for the intro slide
            assets['logos'] = all_logos
            
            # 4. Narration (The Constraints Part)
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
