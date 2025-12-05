# story_runners_refactored/spotlight_story.py
# v24.3.2 - Fixed Audio Pipeline & Imports

import os
from typing import Dict, List, Any

from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
# FIX: Removed content_creator
from .. import config, video_renderer, narration_builder, data_fetcher, chart_generator
from .. import audio_generator as audio_gen_module

class SpotlightStory(BaseStory):
    """Spotlight story implementation - Three-lens portfolio analysis"""
    
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        # FIX: Correctly initialize the v24 audio generator
        self.audio_generator = audio_gen_module.audio_generator
    
    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        """Generate Spotlight story"""
        # Handle list input from main.py
        symbol = queries[0] if isinstance(queries, list) else queries
        
        try:
            if not self._validate_inputs(symbol):
                return False
            
            print(f"🎬 Generating Spotlight Story: {symbol}")
            
            # Fetch data
            nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(symbol)
            company_data = self._fetch_company_data(nse_symbol, y_symbol, display)
            
            if not company_data:
                print(f"❌ Failed to fetch data for {symbol}")
                return False
            
            # Generate charts for three lenses
            chart_size = self._get_chart_size(video_format)
            charts = self._generate_spotlight_charts(company_data, chart_size)
            
            # Build three-lens slides
            slides = self._build_spotlight_slides(company_data, charts, display)
            
            # Fetch assets with spotlight keywords
            assets = self._fetch_spotlight_assets(display, company_data, len(slides), video_format)
            
            # Build narration with lens introductions
            english_script_parts = narration_builder.build_english_narration_spotlight(
                company_data['details'], 
                company_data['metrics'], 
                company_data.get('shareholding'), 
                peers_exist=bool(company_data['details'].get("peers"))
            )
            
            # Add lens introduction placeholders
            lens_intros = {
                "profitability_intro": "Profitability analysis",
                "ownership_intro": "Ownership structure", 
                "valuation_intro": "Valuation assessment"
            }
            english_script_parts.update(lens_intros)
            
            # Generate audio
            audio_script_parts = narration_builder.build_audio_script(english_script_parts, lang=self.lang)
            
            # FIX: Use self.audio_generator (Female Voice Config)
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script_parts, lang=self.lang)
            
            # Generate video
            video_renderer.make_video(
                slides, audio_paths, display, "spotlight", video_format, 
                out_path, assets, self.theme, self.icon_svg, lang=self.lang
            )
            
            self._log_story_generation("spotlight", symbol, True)
            return True
            
        except Exception as e:
            print(f"❌ Spotlight story generation failed: {e}")
            import traceback
            traceback.print_exc()
            self._log_story_generation("spotlight", symbol, False)
            return False
    
    def _validate_inputs(self, query): return bool(query)
    
    def _fetch_company_data(self, nse_symbol: str, y_symbol: str, display: str) -> Dict[str, Any]:
        """Fetch all company data needed for Spotlight"""
        
        tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
        yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
        combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}
        
        details = {
            'name': display,
            'summary': tt_data.get('profile'),
            'ceo': yfinance_details.get('ceo'),
            'peers': list(tt_data.get('peers', {}).keys()) if tt_data.get('peers') else [],
            'sector': tt_data.get('sector'),
            'shareholding': tt_data.get('shareholding')
        }
        
        return {
            'nse_symbol': nse_symbol,
            'y_symbol': y_symbol,
            'display': display,
            'details': details,
            'metrics': combined_metrics,
            'tt_data': tt_data
        }
    
    def _generate_spotlight_charts(self, company_data: Dict, chart_size: tuple) -> Dict[str, str]:
        """Generate charts for three-lens analysis"""
        
        charts = {}
        
        # Financials chart (Profitability Lens)
        charts['financials'] = chart_generator.make_financials_chart(
            company_data['y_symbol'], chart_size, self.theme
        )
        
        # ROE chart if available (Profitability Lens)
        if company_data['metrics'].get("returnOnEquity"):
            charts['roe'] = chart_generator.make_single_metric_chart(
                "Return on Equity", 
                company_data['metrics'].get("returnOnEquity"),
                company_data['display'], 
                chart_size, 
                self.theme
            )
        
        # Shareholding chart (Ownership Lens)
        if company_data['details'].get('shareholding'):
            charts['shareholding'] = chart_generator.make_shareholding_chart(
                company_data['details']['shareholding'], chart_size, self.theme
            )
        
        # Valuation charts (Valuation Lens)
        if company_data['metrics'] and "P/E Ratio" in company_data['metrics']:
            charts['valuation'] = chart_generator.make_single_metric_chart(
                "P/E Ratio", 
                company_data['metrics'].get("P/E Ratio"),
                company_data['display'], 
                chart_size, 
                self.theme
            )
        
        # Peer comparison (Valuation Lens)
        if company_data['details'].get('peers'):
            charts['peers'] = chart_generator.make_peer_comparison_chart(
                company_data['tt_data'].get('peers'), 
                company_data['display'], 
                chart_size, 
                self.theme
            )
        
        return charts

    def _build_spotlight_slides(self, company_data: Dict, charts: Dict, display: str) -> List[Dict]:
        """Build three-lens slides for Spotlight story"""
        slides = []
        story_theme = self.story_utils.get_story_theme('spotlight')
        
        # Intro slide
        slides.append({
            'type': 'intro', 
            'key': 'intro', 
            'text': story_theme['intro_text'].format(company_name=display), 
            'logo': True
        })
        
        # Profitability Lens
        slides.append({
            'type': 'summary', 
            'key': 'profitability_intro', 
            'text': "Lens 1:\nProfitability", 
            'is_title': True
        })
        
        if charts.get('financials'):
            slides.append({
                'type': 'chart', 'key': 'financials', 'path': charts['financials'], 'blur_bg': True
            })
        
        if charts.get('roe'):
            slides.append({
                'type': 'chart', 'key': 'roe', 'path': charts['roe'], 'blur_bg': True
            })
        
        # Ownership Lens
        if charts.get('shareholding'):
            slides.append({
                'type': 'summary', 'key': 'ownership_intro', 'text': "Lens 2:\nOwnership", 'is_title': True
            })
            slides.append({
                'type': 'chart', 'key': 'ownership', 'path': charts['shareholding'], 'blur_bg': True
            })
        
        # Valuation Lens
        if charts.get('valuation') or charts.get('peers'):
            slides.append({
                'type': 'summary', 'key': 'valuation_intro', 'text': "Lens 3:\nValuation", 'is_title': True
            })
        
        if charts.get('valuation'):
            slides.append({
                'type': 'chart', 'key': 'valuation', 'path': charts['valuation'], 'blur_bg': True
            })
        
        if charts.get('peers'):
            slides.append({
                'type': 'chart', 'key': 'peers', 'path': charts['peers'], 'blur_bg': True
            })
        
        # Summary and CTA
        slides.extend([
            {'type': 'summary', 'key': 'summary', 'text': "This analysis provides a structured way to evaluate a company, but is not financial advice."},
            {'type': 'cta', 'key': 'cta'}
        ])
        
        return slides
    
    def _fetch_spotlight_assets(self, display: str, company_data: Dict, num_slides: int, video_format: str) -> Dict:
        """Fetch assets for Spotlight story"""
        spotlight_keywords = ["spotlight", "highlight", "focus", "lens", "magnifying glass", "analysis", "portfolio analysis"]
        
        assets = self.background_manager.fetch_contextual_backgrounds(
            display,
            company_data['details'].get('summary', ''),
            num_slides,
            video_format,
            specific_queries=spotlight_keywords
        )
        
        assets['logo'] = data_fetcher.fetch_company_logo(company_data['y_symbol'])
        return assets