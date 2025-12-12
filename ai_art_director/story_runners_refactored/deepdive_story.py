# story_runners_refactored/deepdive_story.py
# v24.2.9 - Guaranteed Argument Match

import os
from typing import Dict, List, Any

from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager

from .. import config
from .. import utils
from .. import data_fetcher, chart_generator, narration_builder, video_renderer
from ..audio_generator import AudioGenerator

class DeepDiveStory(BaseStory):
    """Generates a detailed, multi-segment video analysis."""

    def __init__(self, config_dict: Dict[str, Any]):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
         # --- DIAGNOSTIC PROBE ---
        from .. import content_creator
        from .. import audio_generator
        print(f"   🕵️  DeepDive Probe:")
        print(f"       - content_creator file: {content_creator.__file__}")
        print(f"       - audio_generator file: {audio_generator.__file__}")
        
        # Force use of audio_generator (since that's what you kept)
        self.audio_generator = audio_generator.audio_generator
        print(f"       - Active Generator: {self.audio_generator}")
        # ------------------------
        
        print("   -> DeepDiveStory instance created.")
        print("   -> DeepDiveStory instance created.")

    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        if not self._validate_inputs(queries): return False
        symbol = queries[0]
        print(f"\n🚀 Running DeepDive Story for: {symbol}")

        try:
            # 1. Data
            print("   [1/6] Fetching company data...")
            company_data = self._fetch_company_data(symbol)
            if not company_data: return False

            # 2. Script (FIRST)
            print("   [2/6] Building script...")
            english_script_parts = narration_builder.build_english_narration_deepdive(
                company_data['details'], company_data['metrics'], 
                company_data.get('shareholding'), bool(company_data['details'].get("peers"))
            )
            audio_script_parts = narration_builder.build_audio_script(
                english_script_parts, self.lang, "deepdive", company_data
            )

            # 3. Audio
            print("   [3/6] Generating audio voiceovers...")
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script_parts, self.lang)

            # 4. Visual Structure
            print("   [4/6] Building visual structure...")
            # Pass script for subtitles
            slides = self._build_slides_structure(company_data, video_format, audio_script_parts)

            # 5. Assets
            print("   [5/6] Fetching background assets...")
            assets = self._fetch_story_assets(company_data, len(slides), video_format)

            # 6. Render
            print("   [6/6] Rendering final video...")
            video_renderer.make_video(
                slides, audio_paths, company_data['display'], "deepdive", 
                video_format, out_path, assets, self.theme, self.icon_svg, self.lang
            )
            
            self.audio_generator.cleanup_audio_cache()
            self._log_story_generation("deepdive", symbol, True)
            return True

        except Exception as e:
            print(f"❌ DeepDive Error: {e}")
            import traceback
            traceback.print_exc()
            self._log_story_generation("deepdive", symbol, False, str(e))
            return False

    def _fetch_company_data(self, symbol: str) -> Dict[str, Any]:
        try:
            nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(symbol)
            tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
            yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
            quarterly_financials = data_fetcher.fetch_quarterly_financials(y_symbol)
            price_data, _ = data_fetcher.fetch_price_data(y_symbol)
            logo = data_fetcher.fetch_company_logo(y_symbol)

            # Logic: Try TickerTape sector first, if missing, use Yahoo Finance sector
            sector = tt_data.get('sector')
            if not sector:
                sector = yfinance_details.get('sector', 'N/A')

            combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}
            details = {
                'name': display,
                'summary': tt_data.get('profile'),
                'ceo': yfinance_details.get('ceo'),
                'peers': list(tt_data.get('peers', {}).keys()) if tt_data.get('peers') else [],
                #'sector': tt_data.get('sector')
                'sector': sector, # <--- UPDATED
            }
            
            return {
                'nse_symbol': nse_symbol, 'y_symbol': y_symbol, 'display': display,
                'details': details, 'metrics': combined_metrics,
                'quarterly_financials': quarterly_financials, 'price_data': price_data,
                'shareholding': tt_data.get('shareholding'), 'logo': logo
            }
        except Exception as e:
            print(f"❌ Data Fetch Error: {e}")
            return None

    def _validate_inputs(self, queries: List[str]) -> bool:
        return bool(queries and len(queries) == 1)

    def _build_slides_structure(self, company_data: Dict, video_format: str, audio_script_parts: Dict) -> List[Dict]:
        slides = []
        display_name = self.story_utils.clean_company_name(company_data['display'])
        details = company_data['details']
        
        def get_script(key): return audio_script_parts.get(key, "")

        # 1. Intro
        slides.append({
            'type': 'intro', 'key': 'intro', 'text': display_name, 'logo': True,
            'script_text': get_script('intro')
        })
        
        # 2. Sector
        if company_data['metrics'].get('Market Cap (Cr)'):
            mcap = company_data['metrics']['Market Cap (Cr)']
            formatted_mcap = f"Rs. {mcap:,.0f} Cr"
            slides.append({
                'type': 'sector', 'key': 'sector_scale', 
                'text': f"Market Cap\n{formatted_mcap}\n\nSector\n{details.get('sector', 'N/A')}",
                'is_title': True, 'script_text': get_script('sector_scale')
            })
        
        # 3. Management
        if details.get('ceo'):
            slides.append({
                'type': 'management', 'key': 'management',
                'text': f"Leadership\n\n{details['ceo']}\n(CEO)",
                'is_title': True, 'script_text': get_script('management')
            })
            
        # 4. Financials
        chart_size = config.get_chart_size(video_format)
        fin_path = chart_generator.make_financials_chart(company_data['y_symbol'], chart_size, self.theme)
        if fin_path:
            slides.append({
                'type': 'chart', 'key': 'financials', 'path': fin_path, 'blur_bg': True,
                'script_text': get_script('financials')
            })
            
        # 5. Metrics
        if company_data['metrics']:
            met_path = chart_generator.make_metrics_infographic(company_data['metrics'], chart_size, self.theme)
            if met_path:
                slides.append({
                    'type': 'chart', 'key': 'metrics', 'path': met_path, 'blur_bg': True,
                    'script_text': get_script('metrics')
                })

        # 6. Market
        price_path = chart_generator.make_candlestick_chart(company_data['price_data'], company_data['nse_symbol'], chart_size, self.theme)
        if price_path:
            slides.append({
                'type': 'chart', 'key': 'market', 'path': price_path, 'blur_bg': True,
                'script_text': get_script('market')
            })
        
        # 7. CTA
        slides.append({
            'type': 'cta', 'key': 'cta', 'script_text': get_script('cta')
        })
        
        print(f"      - Built {len(slides)} slides.")
        return slides

    def _fetch_story_assets(self, company_data: Dict, num_slides: int, video_format: str) -> Dict:
        """Fetches background images and company logo."""
        
        # CRITICAL FIX: Argument name 'summary' (was 'business_summary')
        assets = self.background_manager.fetch_contextual_backgrounds(
            company_name=company_data['display'],
            summary=company_data['details'].get('summary', ''),
            num_needed=num_slides,
            video_format=video_format
        )
        assets['logo'] = company_data.get('logo')
        return assets