# story_runners_refactored/custom_news_story.py
# v25.1.1 - Fixed Path Resolution

import json
import os
from typing import Dict, List, Any
from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
from .. import config, video_renderer, narration_builder, data_fetcher
from .. import audio_generator as audio_gen_module

class CustomNewsStory(BaseStory):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        self.audio_generator = audio_gen_module.audio_generator
        self.input_file = config_dict.get('input_file') # From main.py

    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        try:
            # --- PATH DEBUGGING & RESOLUTION ---
            if not self.input_file:
                print(f"❌ No input file provided in config.")
                return False

            # 1. Try exact path (Relative to CWD or Absolute)
            target_path = os.path.abspath(self.input_file)
            
            # 2. If not found, try relative to Project Root (from config)
            if not os.path.exists(target_path):
                target_path = config.ROOT_DIR / self.input_file

            # 3. Final Check
            if not os.path.exists(target_path):
                print(f"❌ Input file not found.")
                print(f"   - Searched: {target_path}")
                print(f"   - CWD: {os.getcwd()}")
                return False
            
            self.input_file = str(target_path) # Update to validated path
            print(f"🎬 Generating Custom News from: {self.input_file}")
            
            # --- END PATH DEBUGGING ---

            # 1. Load Data
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            company = data.get('company_name', 'Unknown')
            ticker = data.get('ticker', '')
            
            # 2. Fetch Assets (Logo/Backgrounds)
            assets = self.background_manager.fetch_contextual_backgrounds(
                company, "Financial news update", len(data.get('news_items', [])) + 2, video_format
            )
            if ticker:
                assets['logo'] = data_fetcher.fetch_company_logo(ticker)

            # 3. Build Slides
            slides = []
            # Intro
            slides.append({'type': 'intro', 'key': 'intro', 'text': f"Update:\n{company}", 'logo': True})
            
            # News Items
            for i, item in enumerate(data.get('news_items', [])):
                slides.append({
                    'type': 'news', 
                    'key': f'news_{i+1}', 
                    'text': item['title'], 
                    'icon': item.get('impact', 'neutral')
                })
            
            # CTA
            slides.append({'type': 'cta', 'key': 'cta'})

            # 4. Narration
            english_script = narration_builder.build_custom_news_script(data)
            audio_script = narration_builder.build_audio_script(english_script, self.lang)
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script, self.lang)

            # 5. Render
            video_renderer.make_video(
                slides, audio_paths, company, "custom_news", video_format, 
                out_path, assets, self.theme, self.icon_svg, self.lang
            )
            return True

        except Exception as e:
            print(f"❌ Custom News Error: {e}")
            import traceback; traceback.print_exc()
            return False
