# main.py
import argparse
import os
import random
import time
import traceback
import multiprocessing

import config
import utils

try:
    from pexels_api import API
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False

# --- STORY SCRIPTS ---
def run_story_news(query, video_format, out_path, theme, icon_svg, assets):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: News Reporter")
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    all_news = (data_fetcher.fetch_yfinance_news(y_symbol) + data_fetcher.fetch_google_news(display, nse_symbol) + data_fetcher.fetch_moneycontrol_news(display) + data_fetcher.fetch_economic_times_news(display) + data_fetcher.fetch_trendlyne_announcements(nse_symbol))
    scored_news = [{**item, 'score': data_fetcher.score_news_relevance(item['title'], display, item['source'])} for item in all_news]
    unique_news = []; [unique_news.append(item) for item in sorted(scored_news, key=lambda x: x['score'], reverse=True) if not any(utils.seq_ratio(item['title'], un['title']) > 0.85 for un in unique_news)]
    news_items = unique_news[:config.MAX_NEWS_ITEMS]
    if not news_items: print("   -> No relevant news found. Cannot generate news video."); return
    print(f"\n✅ Top {len(news_items)} headlines selected:"); [print(f"   {i+1}. {item['title']} (Source: {item['source']})") for i, item in enumerate(news_items)]
    df, _ = data_fetcher.fetch_price_data(y_symbol); snap = data_fetcher.compute_price_snapshot(df)
    script_parts = content_creator.build_narration_news(display, news_items, snap)
    audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nDaily Briefing", 'logo': True}]
    for i, item in enumerate(news_items): slides.append({'type': 'news', 'key': f'news_{i+1}', 'text': item['title'], 'icon': utils.classify_impact(item['title'])})
    slides.append({'type': 'chart', 'key': 'market', 'path': price_chart_path}); slides.append({'type': 'cta', 'key': 'cta'})
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg)

def run_story_deepdive(query, video_format, out_path, theme, icon_svg, assets):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: Stock 101 Deep Dive")
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    metrics = data_fetcher.fetch_financial_metrics(y_symbol); shareholding = data_fetcher.fetch_shareholding(nse_symbol); df, _ = data_fetcher.fetch_price_data(y_symbol)
    script_parts = content_creator.build_narration_deepdive(display, metrics, shareholding); audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    metrics_path = chart_generator.make_metrics_infographic(metrics, chart_size, theme) if metrics else None
    financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme)
    shareholding_path = chart_generator.make_shareholding_chart(shareholding, chart_size, theme) if shareholding else None
    price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nStock Deep Dive", 'logo': True}]
    if metrics_path: slides.append({'type': 'chart', 'key': 'metrics', 'path': metrics_path})
    if financials_path: slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path})
    if shareholding_path: slides.append({'type': 'chart', 'key': 'shareholding', 'path': shareholding_path})
    if price_chart_path: slides.append({'type': 'chart', 'key': 'market', 'path': price_chart_path})
    slides.append({'type': 'cta', 'key': 'cta'})
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg)

def run_story_comparison(query_a, query_b, video_format, out_path, theme, icon_svg, assets):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: Stock vs. Stock")
    print(f"\n--- Fetching data for Primary Stock: {query_a} ---"); nse_a, y_a, display_a = data_fetcher.resolve_symbol(query_a); metrics_a = data_fetcher.fetch_financial_metrics(y_a); df_a, _ = data_fetcher.fetch_price_data(y_a)
    print("\n--- Pausing briefly to respect API limits ---"); time.sleep(random.uniform(2, 4))
    print(f"\n--- Fetching data for Competitor Stock: {query_b} ---"); nse_b, y_b, display_b = data_fetcher.resolve_symbol(query_b); metrics_b = data_fetcher.fetch_financial_metrics(y_b); df_b, _ = data_fetcher.fetch_price_data(y_b)
    script_parts = content_creator.build_narration_comparison(display_a, display_b, metrics_a, metrics_b); audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    print("\n--- Generating Comparison Charts ---"); chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    pe_chart_path, mcap_chart_path = None, None
    if metrics_a and metrics_b:
        pe_chart_path = chart_generator.make_comparison_bar_chart("P/E Ratio", metrics_a.get("P/E Ratio"), metrics_b.get("P/E Ratio"), display_a, display_b, chart_size, theme, out_png="outputs/tmp/pe_comp.png")
        mcap_chart_path = chart_generator.make_comparison_bar_chart("Market Cap (Cr)", metrics_a.get("Market Cap (Cr)"), metrics_b.get("Market Cap (Cr)"), display_a, display_b, chart_size, theme, out_png="outputs/tmp/mcap_comp.png")
    price_chart_path = chart_generator.make_stock_vs_stock_price_chart(df_a, df_b, display_a, display_b, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display_a}\nvs.\n{display_b}", 'logo': False}]
    if pe_chart_path: slides.append({'type': 'chart', 'key': 'pe_compare', 'path': pe_chart_path})
    if mcap_chart_path: slides.append({'type': 'chart', 'key': 'mcap_compare', 'path': mcap_chart_path})
    if price_chart_path: slides.append({'type': 'chart', 'key': 'price_compare', 'path': price_chart_path})
    slides.append({'type': 'cta', 'key': 'cta'})
    video_renderer.make_video(slides, audio_paths, display_a, f"{nse_a}_vs_{nse_b}", video_format, out_path, assets, theme, icon_svg)

def run_story_spotlight(query, video_format, out_path, theme, icon_svg, assets):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: Portfolio Spotlight")
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query); metrics = data_fetcher.fetch_financial_metrics(y_symbol); shareholding = data_fetcher.fetch_shareholding(nse_symbol)
    script_parts = content_creator.build_narration_spotlight(display, metrics, shareholding); audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    print("\n--- Generating Spotlight Charts ---"); chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme); valuation_path = None
    if metrics and "P/E Ratio" in metrics: valuation_path = chart_generator.make_single_metric_chart("P/E Ratio", metrics["P/E Ratio"], display, chart_size, theme)
    shareholding_path = chart_generator.make_shareholding_chart(shareholding, chart_size, theme) if shareholding else None
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nInvestor Spotlight", 'logo': True}]
    if financials_path: slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path})
    if valuation_path: slides.append({'type': 'chart', 'key': 'valuation', 'path': valuation_path})
    if shareholding_path: slides.append({'type': 'chart', 'key': 'ownership', 'path': shareholding_path})
    slides.append({'type': 'text', 'key': 'summary', 'text': "Summary"}); slides.append({'type': 'cta', 'key': 'cta'})
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg)

# --- MAIN ORCHESTRATOR ---
def main_app():
    parser = argparse.ArgumentParser(description=f"Stock Video Content Engine v{config.__version__}")
    parser.add_argument("queries", nargs='+', help="One or two company names/tickers. Use two for 'comparison' type.")
    parser.add_argument("--type", choices=['news', 'deepdive', 'comparison', 'spotlight'], required=True, help="The type of video to generate.")
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='portrait', help="Video format.")
    parser.add_argument("--out", help="Output MP4 path")
    args = parser.parse_args()

    utils.ensure_dirs()
    theme = random.choice(config.BASE_THEMES); theme['font'] = random.choice(config.FONT_PATHS) if config.FONT_PATHS else None
    if not theme['font']: raise IOError("No valid font files found.")
    icon_svg = { "positive": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="{theme["accent"]}" d="m280-400 200-200 200 200H280Z"/></svg>', "negative": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#F44336" d="M480-560 280-760h400L480-560Z"/></svg>', "uncertain": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>' }

    try:
        assets = {}
        if PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY"):
            num_bgs_needed = 5;
            if args.type == 'news': num_bgs_needed = config.MAX_NEWS_ITEMS + 3
            print(f"   -> Fetching {num_bgs_needed} background images from Pexels...")
            try:
                api = API(os.getenv("PEXELS_API_KEY")); search_term = args.queries[0].split()[0]
                search_queries = [f"{search_term} abstract", "data visualization", "stock market", "business analytics"]; random.shuffle(search_queries)
                is_portrait = (args.format == 'portrait'); bg_images = []
                for query in search_queries:
                    if len(bg_images) >= num_bgs_needed: break
                    api.search(query, page=random.randint(1, 5), results_per_page=40)
                    for photo in api.get_entries():
                        correct_orientation = (photo.height > photo.width) if is_portrait else (photo.width > photo.height)
                        if not correct_orientation: continue
                        if hasattr(photo, 'large2x'):
                            img_url = photo.large2x; img_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_{len(bg_images)}.jpg")
                            response = utils.make_request_with_retries(img_url, timeout=60)
                            if response:
                                with open(img_path, 'wb') as f: f.write(response.content)
                                bg_images.append(img_path)
                                if len(bg_images) >= num_bgs_needed: break
                assets['bg_images'] = bg_images; assets['bg_credit'] = "Photos by Pexels" if bg_images else None
                if not bg_images: print("      -  WARNING: Pexels search returned no suitable images after filtering.")
            except Exception as e: print(f"      -  WARNING: Pexels API failed: {e}. Continuing with solid color backgrounds.")
        
        out_path = args.out
        if args.type == 'news':
            if len(args.queries) != 1: parser.error("'news' type requires exactly one query.")
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0]}_{args.type}_{args.format}.mp4")
            run_story_news(args.queries[0], args.format, out_path, theme, icon_svg, assets)
        elif args.type == 'deepdive':
            if len(args.queries) != 1: parser.error("'deepdive' type requires exactly one query.")
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0]}_{args.type}_{args.format}.mp4")
            run_story_deepdive(args.queries[0], args.format, out_path, theme, icon_svg, assets)
        elif args.type == 'comparison':
            if len(args.queries) != 2: parser.error("'comparison' type requires exactly two queries.")
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0]}_vs_{args.queries[1]}_{args.format}.mp4")
            run_story_comparison(args.queries[0], args.queries[1], args.format, out_path, theme, icon_svg, assets)
        elif args.type == 'spotlight':
            if len(args.queries) != 1: parser.error("'spotlight' type requires exactly one query.")
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0]}_{args.type}_{args.format}.mp4")
            run_story_spotlight(args.queries[0], args.format, out_path, theme, icon_svg, assets)

        if out_path:
            print("\n--- Independent File Verification ---")
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
                print(f"✅✅✅ SUCCESS: Video created at '{out_path}' (Size: {os.path.getsize(out_path)/1024/1024:.2f} MB)")
            else:
                print("❌❌❌ FAILURE: Output file not found or is empty. An error likely occurred during rendering.")
    except Exception as e:
        print(f"\n❌ An error occurred in the main process: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass
    main_app()
