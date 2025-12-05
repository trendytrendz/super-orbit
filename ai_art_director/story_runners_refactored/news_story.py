# story_runners_refactored/news_story.py
# v24.3.0 - Init Update

from typing import Dict, List, Any
from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
from .. import config, utils, content_creator, video_renderer, narration_builder, data_fetcher, chart_generator

# CRITICAL: Use content_creator audio generator
from .. import audio_generator as audio_gen_module

class NewsStory(BaseStory):
    def __init__(self, config_dict: Dict[str, Any]):
        # Pass config_dict to parent
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        # Use the shared audio generator
        self.audio_generator = audio_gen_module.audio_generator
    
    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        symbol = queries[0]
        try:
            if not self._validate_inputs([symbol]): return False
            print(f"🎬 Generating News Story: {symbol}")
            
            nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(symbol)
            company_data = self._fetch_company_data(nse_symbol, y_symbol, display)
            
            if not company_data: return False
            
            slides = self._build_slides(company_data, display, video_format)
            assets = self._fetch_assets(display, company_data, len(slides), video_format)
            
            english_script = narration_builder.build_english_narration_news(
                display, company_data['news_items'], company_data['price_snapshot']
            )
            
            # Build Audio Script
            audio_script = narration_builder.build_audio_script(english_script, self.lang)
            
            # Generate Audio
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script, self.lang)
            
            video_renderer.make_video(
                slides, audio_paths, display, "news", video_format, 
                out_path, assets, self.theme, self.icon_svg, self.lang
            )
            
            self._log_story_generation("news", symbol, True)
            return True
            
        except Exception as e:
            print(f"❌ News Error: {e}")
            self._log_story_generation("news", symbol, False)
            return False

    def _validate_inputs(self, queries): return bool(queries)

    def _fetch_company_data(self, nse_symbol, y_symbol, display):
        # (Logic remains same as before, condensed for brevity)
        all_news = (data_fetcher.fetch_yfinance_news(y_symbol) + 
                    data_fetcher.fetch_google_news(display, nse_symbol))
        # Score and filter
        scored = [{**i, 'score': data_fetcher.score_news_relevance(i['title'], display, i['source'])} for i in all_news]
        unique = []
        for i in sorted(scored, key=lambda x: x['score'], reverse=True):
            if not any(utils.seq_ratio(i['title'], u['title']) > 0.85 for u in unique): unique.append(i)
        
        df, _ = data_fetcher.fetch_price_data(y_symbol)
        return {
            'nse_symbol': nse_symbol, 'y_symbol': y_symbol, 'display': display,
            'news_items': unique[:config.MAX_NEWS_ITEMS],
            'price_snapshot': data_fetcher.compute_price_snapshot(df),
            'price_data': df, # Added this so candlestick works
            'tt_data': data_fetcher.fetch_tickertape_data(nse_symbol)
        }

    def _build_slides(self, company_data, display, video_format):
        slides = []
        theme = self.story_utils.get_story_theme('news')
        slides.append({'type': 'intro', 'key': 'intro', 'text': theme['intro_text'].format(company_name=display), 'logo': True})
        
        for i, item in enumerate(company_data['news_items']):
            slides.append({'type': 'news', 'key': f'news_{i+1}', 'text': item['title'], 'icon': utils.classify_impact(item['title'])})
            
        chart_size = config.get_chart_size(video_format)
        price_path = chart_generator.make_candlestick_chart(company_data['price_data'], company_data['nse_symbol'], chart_size, self.theme)
        if price_path: slides.append({'type': 'chart', 'key': 'market', 'path': price_path, 'blur_bg': True})
        
        slides.append({'type': 'cta', 'key': 'cta'})
        return slides

    def _fetch_assets(self, display, data, num, fmt):
        assets = self.background_manager.fetch_contextual_backgrounds(display, data.get('tt_data', {}).get('profile', ''), num, fmt)
        assets['logo'] = data_fetcher.fetch_company_logo(data['y_symbol'])
        return assets