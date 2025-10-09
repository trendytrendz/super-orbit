# main.py
import argparse
import os
import random
import time
import traceback

# Import our new modules
import config
import utils
import data_fetcher
import chart_generator
import content_creator
import video_renderer

# Conditional imports for optional features
try:
    from pexels_api import API
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False

def main():
    parser = argparse.ArgumentParser(description=f"Stock Video Briefing Generator v{config.__version__}")
    parser.add_argument("query", help="Company name or NSE ticker")
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='landscape', help="Video format")
    parser.add_argument("--out", help="Output MP4 path")
    args = parser.parse_args()

    utils.ensure_dirs()
    script_dir = utils.get_script_dir()
    
    if not config.FONT_PATHS:
        raise IOError("No valid font files found. Please check config.py.")
    
    theme = random.choice(config.BASE_THEMES)
    theme['font'] = random.choice(config.FONT_PATHS)
    
    icon_svg = {
        "positive": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="{theme["accent"]}" d="m280-400 200-200 200 200H280Z"/></svg>',
        "negative": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#F44336" d="M480-560 280-760h400L480-560Z"/></svg>',
        "uncertain": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>'
    }

    try:
        print(f"🎬 Starting video generation for '{args.query}' (v{config.__version__})")
        print(f"🎨 Using Theme: Accent={theme['accent']}, Font={os.path.basename(theme['font'])}")
        
        # --- 1. Data Fetching ---
        print("\n1. Resolving symbol...")
        nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(args.query)
        print(f"   -> Found: {display} (NSE: {nse_symbol})")

        print("\n2. Fetching & Scoring News...")
        all_news = (data_fetcher.fetch_yfinance_news(y_symbol) + 
                    data_fetcher.fetch_google_news(display, nse_symbol) +
                    data_fetcher.fetch_moneycontrol_news(display) +
                    data_fetcher.fetch_economic_times_news(display) +
                    data_fetcher.fetch_trendlyne_announcements(nse_symbol))
        
        scored_news = [{**item, 'score': data_fetcher.score_news_relevance(item['title'], display, item['source'])} for item in all_news]
        unique_news = []
        for news_item in sorted(scored_news, key=lambda x: x['score'], reverse=True):
            if not any(utils.seq_ratio(news_item['title'], unique['title']) > 0.85 for unique in unique_news):
                unique_news.append(news_item)
        
        news_items = unique_news[:config.MAX_NEWS_ITEMS]
        if not news_items: 
            print("   -> No relevant news found. Exiting.")
            return
        
        print(f"\n✅ Top {len(news_items)} headlines selected:")
        for i, item in enumerate(news_items):
            print(f"   {i+1}. {item['title']} (Source: {item['source']}, Score: {item['score']})")

        print("\n3. Fetching financial & price data...")
        df, df_index = data_fetcher.fetch_price_data(y_symbol)
        snap = data_fetcher.compute_price_snapshot(df)
        metrics = data_fetcher.fetch_financial_metrics(y_symbol)
        shareholding = data_fetcher.fetch_shareholding(nse_symbol)

        # --- 2. Chart Generation ---
        print("\n4. Generating charts...")
        chart_size = (1200, 600) if args.format == 'landscape' else (680, 500)
        financials_chart_path = chart_generator.make_financials_chart(y_symbol, size=chart_size, theme=theme)
        index_comp_path = chart_generator.make_index_comparison_chart(df, df_index, display, "Nifty 50", size=chart_size, theme=theme)
        
        # *** THIS IS THE CRITICAL ERROR HANDLING LOGIC ***
        # It ensures that if 'shareholding' is None, the chart function is never called and the path is None.
        shareholding_path = chart_generator.make_shareholding_chart(shareholding, size=chart_size, theme=theme) if shareholding else None
        
        # --- 3. Content Creation (Narration & Audio) ---
        script_parts = content_creator.build_narration(display, news_items, snap)
        audio_paths = content_creator.generate_segmented_voiceover(script_parts)

        # --- 4. Visual Asset Fetching ---
        print("\n5. Fetching visual assets...")
        assets = {'bg_images': []}
        assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
        
        # *** THIS LOGIC NOW CORRECTLY HANDLES A 'None' SHAREHOLDING_PATH ***
        num_bgs_needed = (2 + len(news_items) + 
                          (1 if metrics else 0) + 
                          (1 if shareholding_path else 0) + 
                          (1 if index_comp_path else 0) + 
                          (1 if financials_chart_path else 0))
                          
        if PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY"):
            print(f"   -> Fetching {num_bgs_needed} background images from Pexels...")
            try:
                api = API(os.getenv("PEXELS_API_KEY"))
                search_queries = [f"{display.split()[0]} abstract", "data visualization", "stock market", "business analytics", "corporate meeting"]
                random.shuffle(search_queries)
                for query in search_queries:
                    if len(assets['bg_images']) >= num_bgs_needed: break
                    api.search(query, page=random.randint(1, 5), results_per_page=10)
                    for photo in api.get_entries():
                        if hasattr(photo, 'large2x'):
                            img_url = photo.large2x
                            img_path = os.path.join(script_dir, "outputs", "tmp", f"bg_{len(assets['bg_images'])}.jpg")
                            response = utils.make_request_with_retries(img_url, timeout=60)
                            if response:
                                with open(img_path, 'wb') as f: f.write(response.content)
                                assets['bg_images'].append(img_path)
                                assets['bg_credit'] = "Photos by various artists on Pexels"
                                if len(assets['bg_images']) >= num_bgs_needed: break
                if not assets['bg_images']:
                     print("      -  WARNING: Pexels search returned no images. Continuing with solid color backgrounds.")
            except Exception as e:
                print(f"      -  WARNING: Pexels API failed: {e}. Continuing with solid color backgrounds.")
                assets['bg_images'] = []

        # --- 5. Video Rendering ---
        print("\n6. Rendering video...")
        out_path = args.out or os.path.join(script_dir, "outputs", f"{nse_symbol}_{args.format}_briefing.mp4")
        
        video_renderer.make_video(
            company=display, news_items=news_items, metrics=metrics, 
            price_df=df, df_index=df_index, shareholding_chart=shareholding_path, 
            index_comp_chart=index_comp_path, financials_chart=financials_chart_path, 
            price_info=snap, out_path=out_path, video_format=args.format, 
            assets=assets, theme=theme, script_parts=script_parts, audio_paths=audio_paths,
            icon_svg=icon_svg
        )

        # --- 6. Final Verification ---
        print("\n--- Independent File Verification ---")
        if os.path.exists(out_path):
            file_size = os.path.getsize(out_path) / 1024 / 1024
            print(f"✅✅✅ SUCCESS: Video created at '{out_path}' (Size: {file_size:.2f} MB)")
        else:
            print("❌❌❌ FAILURE: File NOT FOUND.")

    except Exception as e:
        print(f"\n❌ An error occurred in the main process: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
