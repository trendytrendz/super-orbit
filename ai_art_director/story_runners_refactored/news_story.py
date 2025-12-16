# ai_art_director/story_runners_refactored/news_story.py
# v25.8.0 - Logic Fix & Validation

from typing import Dict, List, Any
from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
from .. import config, utils, video_renderer, narration_builder, data_fetcher, chart_generator
from .. import audio_generator as audio_gen_module

class NewsStory(BaseStory):
    def __init__(self, config_dict: Dict[str, Any]):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        self.audio_generator = audio_gen_module.audio_generator

    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        symbol = queries[0]
        try:
            if not queries: return False
            print(f"🎬 Generating News Story: {symbol}")
            
            # 1. Fetch
            nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(symbol)
            company_data = self._fetch_company_data(nse_symbol, y_symbol, display)
            if not company_data: return False
            
            # 2. Slides
            slides = self._build_slides(company_data, display, video_format)
            
            # 3. Assets
            assets = self._fetch_assets(display, company_data, len(slides), video_format)
            
            # 4. Narration
            english_script = narration_builder.build_english_narration_news(
                display, company_data['news_items'], company_data.get('price_snapshot', {})
            )
            audio_script = narration_builder.build_audio_script(english_script, self.lang)
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script, self.lang)
            
            # 5. Render
            video_renderer.make_video(
                slides, audio_paths, display, "news", video_format, 
                out_path, assets, self.theme, self.icon_svg, self.lang
            )
            
            self._log_story_generation("news", symbol, True)
            return True
            
        except Exception as e:
            print(f"❌ News Error: {e}")
            import traceback; traceback.print_exc()
            return False

    def _fetch_company_data(self, nse_symbol, y_symbol, display):
        # Fetch from sources
        n1 = data_fetcher.fetch_yfinance_news(y_symbol)
        n2 = data_fetcher.fetch_google_news(display, nse_symbol)
        
        all_news = n1 + n2
        
        # Score
        scored = []
        for i in all_news:
            # Using data_fetcher.score_news_relevance
            score = data_fetcher.score_news_relevance(i['title'], display, i['source'])
            scored.append({**i, 'score': score})
            
        # Sort & Dedupe (Using utils.seq_ratio)
        unique = []
        for i in sorted(scored, key=lambda x: x['score'], reverse=True):
            if not any(utils.seq_ratio(i['title'], u['title']) > 0.85 for u in unique):
                unique.append(i)
        
        df, _ = data_fetcher.fetch_price_data(y_symbol)
        
        return {
            'nse_symbol': nse_symbol, 'y_symbol': y_symbol, 'display': display,
            'news_items': unique[:config.MAX_NEWS_ITEMS],
            'price_snapshot': data_fetcher.compute_price_snapshot(df),
            'price_data': df,
            'tt_data': data_fetcher.fetch_tickertape_data(nse_symbol)
        }

    def _build_slides(self, company_data, display, video_format):
        slides = []
        theme = config.STORY_THEMES.get('news', {})
        
        # Intro
        intro_text = theme.get('intro_text', "Latest News: {company_name}").format(company_name=display)
        slides.append({'type': 'intro', 'key': 'intro', 'text': intro_text, 'logo': True})
        
        # News items
        for i, item in enumerate(company_data['news_items']):
            # Using utils.classify_impact
            impact = utils.classify_impact(item['title'])
            slides.append({
                'type': 'news', 
                'key': f'news_{i+1}', 
                'text': item['title'], 
                'icon': impact,
                'source': item.get('source')
            })
            
        # Chart
        chart_size = config.get_chart_size(video_format)
        price_path = chart_generator.make_candlestick_chart(company_data['price_data'], company_data['nse_symbol'], chart_size, self.theme)
        if price_path:
            slides.append({'type': 'chart', 'key': 'market', 'path': price_path, 'blur_bg': True})
            
        slides.append({'type': 'cta', 'key': 'cta'})
        return slides

    def _fetch_assets(self, display, data, num, fmt):
        assets = self.background_manager.fetch_contextual_backgrounds(
            display, data.get('tt_data', {}).get('profile', ''), num, fmt
        )
        assets['logo'] = data_fetcher.fetch_company_logo(data['y_symbol'])
        return assets