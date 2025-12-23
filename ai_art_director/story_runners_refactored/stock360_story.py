# ai_art_director/story_runners_refactored/stock360_story.py
# v26.1.1 - Features Added + Rounding Fix

from typing import Dict, List, Any
import os
from .base_story import BaseStory
from .story_utils import StoryUtils
from .background_manager import BackgroundManager
from .. import config, video_renderer, narration_builder, data_fetcher, chart_generator, visual_elements
from .. import audio_generator as audio_gen_module

class Stock360Story(BaseStory):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.story_utils = StoryUtils()
        self.background_manager = BackgroundManager()
        self.audio_generator = audio_gen_module.audio_generator

    def run(self, queries: List[str], video_format: str, out_path: str) -> bool:
        symbol = queries[0]
        try:
            print(f"🎬 Stock 360° Upgrade: {symbol}")
            nse, y_sym, disp = data_fetcher.resolve_symbol(symbol)
            
            # 1. Fetch Data
            df, signals = data_fetcher.fetch_price_data_with_technicals(y_sym)
            if df is None: return False
            
            tt_data = data_fetcher.fetch_tickertape_data(nse) # TickerTape
            yf_det = data_fetcher.fetch_yfinance_supplemental_details(y_sym)
            fund_3yr = data_fetcher.fetch_3yr_fundamentals(y_sym) # 3Yr Data
            q_data = data_fetcher.fetch_quarterly_financials(y_sym)
            
            metrics = {**yf_det, **tt_data.get('metrics', {})}
            
            # 2. Build Slides
            slides = []
            
            # -- Slide 1: Railway Hook --
            rail_path = str(config.TMP_IMG_DIR / "railway_map.png")
            visual_elements.render_railway_map(df, disp, config.get_chart_size(video_format), self.theme, rail_path)
            slides.append({'type': 'chart', 'key': 'hook', 'path': rail_path, 'blur_bg': False, 
                           'script_text': f"Is {disp} on the right track? Let's check the 360 analysis."})
            
            # -- Slide 2: Fundamentals (ROCE + ROE) --
            # FIX: Rounding
            mcap = metrics.get('Market Cap (Cr)', 0)
            pe = metrics.get('P/E Ratio', 0)
            roe = fund_3yr.get('roe', 0)
            
            # Note: YFinance doesn't give ROCE easily, usually ROE. 
            # We display ROE & PE here.
            text_block = (
                f"M.Cap: {mcap:,.0f} Cr\n"
                f"P/E: {pe:.2f}\n"
                f"ROE: {roe:.2f}%"
            )
            
            slides.append({
                'type': 'sector', 'key': 'fundamentals',
                'text': text_block,
                'script_text': f"Valued at {mcap:,.0f} crores, it has an ROE of {roe:.2f} percent and P E of {pe:.2f}."
            })
            
            # -- Slide 3: 3-Year History (Sales/Profit) --
            # New Feature
            if len(fund_3yr['years']) >= 2:
                hist_path = str(config.TMP_IMG_DIR / "hist_3yr.png")
                # Use Comparison Chart logic to show Sales growth
                sales_data = {y: s for y, s in zip(fund_3yr['years'], fund_3yr['sales'])}
                chart_generator.make_comparison_bar_chart("Revenue (3Y)", sales_data, config.get_chart_size(video_format), self.theme, hist_path)
                
                slides.append({
                    'type': 'chart', 'key': 'history', 'path': hist_path, 'blur_bg': True,
                    'script_text': "Looking at the 3-year history, revenue has shown this trend."
                })

            # -- Slide 4: Quarterly (Cricket) --
            if q_data:
                cricket_path = str(config.TMP_IMG_DIR / "cricket_score.png")
                visual_elements.render_cricket_scorecard(q_data, disp, config.get_chart_size(video_format), self.theme, cricket_path)
                slides.append({'type': 'chart', 'key': 'quarterly', 'path': cricket_path, 'blur_bg': False,
                               'script_text': "Latest quarterly numbers show solid performance."})

            # -- Slide 5: Technicals (SMA + RSI Thermometer) --
            tech_path = chart_generator.make_candlestick_chart(df, nse, config.get_chart_size(video_format), self.theme)
            
            # Overlay RSI Thermometer on top? Or separate? 
            # Better strategy: Add RSI as a separate quick visual or narration focus.
            # Let's create an RSI Image and use it as the main image for a "Technicals Part 2" or composite it.
            
            rsi_val = signals['rsi']
            rsi_path = str(config.TMP_IMG_DIR / "rsi_gauge.png")
            visual_elements.render_rsi_thermometer(rsi_val, config.get_chart_size(video_format), self.theme, rsi_path)
            
            # Combined Logic: Show Candlestick, then RSI
            slides.append({
                'type': 'chart', 'key': 'technicals_price', 'path': tech_path, 'blur_bg': True,
                'script_text': f"Price is {signals['trend']} relative to moving averages."
            })
            
            slides.append({
                'type': 'chart', 'key': 'technicals_rsi', 'path': rsi_path, 'blur_bg': True,
                'script_text': f"RSI is at {rsi_val:.1f}, indicating momentum strength."
            })

            # -- Slide 6: CTA --
            slides.append({'type': 'cta', 'key': 'cta', 'script_text': "What's your target? Comment below."})

            # 3. Production
            audio_script = {s['key']: s['script_text'] for s in slides}
            audio_paths = self.audio_generator.generate_segmented_voiceover(audio_script, self.lang)
            assets = self.background_manager.fetch_contextual_backgrounds(disp, "Finance", len(slides), video_format)
            assets['logo'] = data_fetcher.fetch_company_logo(y_sym)
            
            video_renderer.make_video(slides, audio_paths, disp, "stock360", video_format, out_path, assets, self.theme, self.icon_svg, self.lang)
            return True
            
        except Exception as e:
            print(f"❌ Stock360 Error: {e}")
            import traceback; traceback.print_exc()
            return False