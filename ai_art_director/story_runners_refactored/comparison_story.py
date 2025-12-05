# story_runners_refactored/comparison_story.py
# v24.3.3 - Fixed Chart Overwrite & Subtitles

import os
import time
import random
from typing import Dict, List, Any

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
            if not self._validate_comparison_inputs(queries): return False
            print(f"🎬 Generating Comparison Story: {' vs '.join(queries)}")
            
            # 1. Fetch Data
            all_stock_data = self._fetch_comparison_stock_data(queries)
            if not all_stock_data or len(all_stock_data) < 2:
                print("❌ Insufficient data for comparison")
                return False
            
            # 2. Generate Charts (Unique filenames handled inside helper)
            chart_size = self._get_chart_size(video_format)
            charts = self._generate_comparison_charts(all_stock_data, chart_size)
            
            # 3. Build Slides Structure
            slides = self._build_comparison_slides(all_stock_data, charts)
            
            # 4. Assets
            assets = self._prepare_comparison_assets(all_stock_data, slides, video_format)
            
            # 5. Script & Audio
            english_script_parts = narration_builder.build_english_narration_comparison(all_stock_data, slides)
            
            # --- FIX: Inject Script Text into Slides for Subtitles ---
            for slide in slides:
                key = slide['key']
                if key in english_script_parts:
                    slide['script_text'] = english_script_parts[key]
            # ---------------------------------------------------------

            audio_script_parts = narration_builder.build_audio_script(english_script_parts, lang=self.lang)
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script_parts, lang=self.lang)
            
            # 6. Render
            video_renderer.make_video(
                slides, audio_paths, all_stock_data[0]['display'], "comparison", 
                video_format, out_path, assets, self.theme, self.icon_svg, lang=self.lang
            )
            
            self._log_story_generation("comparison", " vs ".join(queries), True)
            return True
            
        except Exception as e:
            print(f"❌ Comparison Error: {e}")
            import traceback; traceback.print_exc()
            return False
    
    # ... _validate_comparison_inputs and _fetch_comparison_stock_data remain the same ...
    def _validate_comparison_inputs(self, queries: List[str]) -> bool:
        if not queries or len(queries) < 2 or len(queries) > 4:
            print("❌ Comparison requires 2-4 companies")
            return False
        return True

    def _fetch_comparison_stock_data(self, queries: List[str]) -> List[Dict[str, Any]]:
        all_stock_data = []
        for i, query in enumerate(queries):
            print(f"\n--- Fetching data for Stock {i+1}: {query} ---")
            try:
                nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
                tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
                yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
                combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}
                df, _ = data_fetcher.fetch_price_data(y_symbol)
                quarterly_financials = data_fetcher.fetch_quarterly_financials(y_symbol)
                
                stock_info = {
                    "nse_symbol": nse_symbol, "y_symbol": y_symbol, "display": display,
                    "metrics": combined_metrics, "price_data": df, "quarterly_financials": quarterly_financials,
                    "profile": tt_data.get('profile'), "logo": data_fetcher.fetch_company_logo(y_symbol),
                    "peers": list(tt_data.get('peers', {}).keys()) if tt_data.get('peers') else []
                }
                all_stock_data.append(stock_info)
                if i < len(queries) - 1: time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"❌ Failed to fetch data for {query}: {e}")
                continue
        return all_stock_data

    def _generate_comparison_charts(self, all_stock_data: List[Dict], chart_size: tuple) -> Dict[str, str]:
        """Generate comparison charts with UNIQUE filenames to prevent overwriting"""
        
        # Data Preparation
        pe_data = {d['display']: d['metrics'].get("P/E Ratio") for d in all_stock_data}
        pb_data = {d['display']: d['metrics'].get("P/B Ratio") for d in all_stock_data}
        mcap_data = {d['display']: d['metrics'].get("Market Cap (Cr)") for d in all_stock_data}
        q_rev_data = {d['display']: d['quarterly_financials'].get("Quarterly Revenue (Cr)") for d in all_stock_data}
        q_profit_data = {d['display']: d['quarterly_financials'].get("Quarterly Profit (Cr)") for d in all_stock_data}
        
        perf_data = {}
        for data in all_stock_data:
            try:
                low_52wk = data['metrics'].get("52-Wk Low")
                last_price = data['price_data']['Close'].iloc[-1]
                perf_data[data['display']] = ((last_price / low_52wk) - 1) * 100 if low_52wk and low_52wk > 0 else None
            except: perf_data[data['display']] = None

        # --- FIX: Pass unique output filenames ---
        def get_path(name): return str(config.TMP_IMG_DIR / f"{name}.png")

        charts = {
            'pe_compare': chart_generator.make_comparison_bar_chart("P/E Ratio", pe_data, chart_size, self.theme, out_png=get_path("pe_compare")),
            'pb_compare': chart_generator.make_comparison_bar_chart("P/B Ratio", pb_data, chart_size, self.theme, out_png=get_path("pb_compare")),
            'mcap_compare': chart_generator.make_comparison_bar_chart("Market Cap (Cr)", mcap_data, chart_size, self.theme, out_png=get_path("mcap_compare")),
            'q_revenue_compare': chart_generator.make_comparison_bar_chart("Latest Quarterly Revenue (Cr)", q_rev_data, chart_size, self.theme, out_png=get_path("q_revenue_compare")),
            'q_profit_compare': chart_generator.make_comparison_bar_chart("Latest Quarterly Profit (Cr)", q_profit_data, chart_size, self.theme, out_png=get_path("q_profit_compare")),
            'perf_compare': chart_generator.make_comparison_bar_chart("Gain from 52-Wk Low (%)", perf_data, chart_size, self.theme, out_png=get_path("perf_compare")),
        }
        
        price_dfs = [d['price_data'] for d in all_stock_data]
        price_names = [d['display'] for d in all_stock_data]
        charts['price_compare'] = chart_generator.make_stock_vs_stock_price_chart(
            price_dfs, price_names, chart_size, self.theme, out_png=get_path("price_compare")
        )
        
        return charts
    
    def _build_comparison_slides(self, all_stock_data: List[Dict], charts: Dict[str, str]) -> List[Dict]:
        slides = []
        
        
        # Intro
        logos = [d['logo'] for d in all_stock_data] # Pass all, even if None (to keep index alignment)
        display_names = [d['display'] for d in all_stock_data]
        
        slides.append({
            'type': 'intro', 
            'key': 'intro', 
            'text': "Head-to-Head Analysis", # Generic Title
            'logos': logos, 
            'names': display_names # <--- NEW: Pass names list for the Card Layout
        }) 
        # Charts
        chart_mappings = [
            ('pe_compare', 'pe_compare'), ('pb_compare', 'pb_compare'),
            ('mcap_compare', 'mcap_compare'), ('q_revenue_compare', 'q_revenue_compare'),
            ('q_profit_compare', 'q_profit_compare'), ('perf_compare', 'perf_compare'),
            ('price_compare', 'price_compare')
        ]
        
        for chart_key, slide_key in chart_mappings:
            if charts.get(chart_key) and os.path.exists(charts[chart_key]):
                slides.append({'type': 'chart', 'key': slide_key, 'path': charts[chart_key], 'blur_bg': True})
        
        slides.append({'type': 'cta', 'key': 'cta'})
        return slides

    def _prepare_comparison_assets(self, all_stock_data: List[Dict], slides: List[Dict], video_format: str) -> Dict:
        combined_summary = ". ".join([d['profile'] for d in all_stock_data if d.get('profile')])
        comparison_name = " vs ".join([d['display'] for d in all_stock_data])
        
        intro_keywords = ["versus abstract", "lines crossing", "competition graph", "head to head abstract"]
        intro_assets = self.background_manager.fetch_contextual_backgrounds(comparison_name, "", 1, video_format, specific_queries=intro_keywords)
        other_assets = self.background_manager.fetch_contextual_backgrounds(comparison_name, combined_summary, len(slides) - 1, video_format)
        
        assets = {**other_assets, **intro_assets}
        assets['logos'] = [d['logo'] for d in all_stock_data if d.get('logo')]
        return assets