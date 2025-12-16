# ai_art_director/story_runners_refactored/comparison_story.py
# v25.8.0 - Validated Flow

import os
import time
import random
from typing import Dict, List
from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
from .. import config, video_renderer, narration_builder, data_fetcher, chart_generator
from .. import audio_generator as audio_gen_module

class ComparisonStory(BaseStory):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        self.audio_generator = audio_gen_module.audio_generator
    
    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        try:
            if not queries or len(queries) < 2: return False
            print(f"🎬 Generating Comparison: {' vs '.join(queries)}")
            
            # 1. Fetch
            all_data = []
            for q in queries:
                nse, y_sym, disp = data_fetcher.resolve_symbol(q)
                tt = data_fetcher.fetch_tickertape_data(nse)
                yf_det = data_fetcher.fetch_yfinance_supplemental_details(y_sym)
                df, _ = data_fetcher.fetch_price_data(y_sym)
                qf = data_fetcher.fetch_quarterly_financials(y_sym)
                
                all_data.append({
                    "display": disp, "y_symbol": y_sym, "logo": data_fetcher.fetch_company_logo(y_sym),
                    "metrics": {**yf_det, **tt.get('metrics', {})},
                    "price_data": df, "quarterly_financials": qf, "profile": tt.get('profile')
                })
                time.sleep(1)

            # 2. Charts (With unique paths)
            cz = config.get_chart_size(video_format)
            def _p(n): return str(config.TMP_IMG_DIR / f"{n}.png")
            
            # Extract data lists
            pe_d = {d['display']: d['metrics'].get("P/E Ratio") for d in all_data}
            mcap_d = {d['display']: d['metrics'].get("Market Cap (Cr)") for d in all_data}
            
            charts = {
                'pe_compare': chart_generator.make_comparison_bar_chart("P/E Ratio", pe_d, cz, self.theme, _p("pe_cmp")),
                'mcap_compare': chart_generator.make_comparison_bar_chart("Market Cap (Cr)", mcap_d, cz, self.theme, _p("mcap_cmp")),
                'price_compare': chart_generator.make_stock_vs_stock_price_chart([d['price_data'] for d in all_data], [d['display'] for d in all_data], cz, self.theme, _p("price_cmp"))
            }

            # 3. Slides
            slides = []
            slides.append({'type': 'intro', 'key': 'intro', 'text': "Head-to-Head", 'logos': [d['logo'] for d in all_data], 'names': [d['display'] for d in all_data]})
            
            if charts['pe_compare']: slides.append({'type': 'chart', 'key': 'pe_compare', 'path': charts['pe_compare'], 'blur_bg': True})
            if charts['mcap_compare']: slides.append({'type': 'chart', 'key': 'mcap_compare', 'path': charts['mcap_compare'], 'blur_bg': True})
            if charts['price_compare']: slides.append({'type': 'chart', 'key': 'price_compare', 'path': charts['price_compare'], 'blur_bg': True})
            
            slides.append({'type': 'cta', 'key': 'cta'})

            # 4. Narration & Audio
            eng_script = narration_builder.build_english_narration_comparison(all_data, slides)
            
            # Inject subtitles
            for s in slides:
                if s['key'] in eng_script: s['script_text'] = eng_script[s['key']]
                
            aud_script = narration_builder.build_audio_script(eng_script, self.lang)
            aud_paths = self.audio_generator.generate_segmented_voiceover(aud_script, self.lang)
            
            # 5. Render
            assets = self.background_manager.fetch_contextual_backgrounds(" vs ".join([d['display'] for d in all_data]), "", len(slides), video_format)
            assets['logos'] = [d['logo'] for d in all_data]
            
            video_renderer.make_video(slides, aud_paths, all_data[0]['display'], "comparison", video_format, out_path, assets, self.theme, self.icon_svg, self.lang)
            return True
        except Exception as e:
            print(f"❌ Comparison Error: {e}")
            import traceback; traceback.print_exc()
            return False