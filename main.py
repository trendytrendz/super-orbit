# main.py
import argparse
import os
import random
import time
import traceback
import multiprocessing
from PIL import Image

import config
import utils

try:
    from pexels_api import API
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False

# --- PEXELS HELPER FUNCTION ---
def fetch_pexels_bgs(num_bgs_needed, search_term, video_format):
    assets = {}
    if not (PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY")):
        return assets
    print(f"\n   -> Fetching {num_bgs_needed} background images from Pexels...")
    try:
        api = API(os.getenv("PEXELS_API_KEY")); clean_search_term = search_term.split()[0]
        search_queries = [f"{clean_search_term} abstract", "data visualization", "stock market", "business analytics"]; random.shuffle(search_queries)
        is_portrait = (video_format == 'portrait'); bg_image_paths = []; found_urls = set()
        for query in search_queries:
            if len(bg_image_paths) >= num_bgs_needed: break
            api.search(query, page=random.randint(1, 5), results_per_page=80)
            for photo in api.get_entries():
                if len(bg_image_paths) >= num_bgs_needed: break
                if photo.url in found_urls: continue
                correct_orientation = (photo.height > photo.width) if is_portrait else (photo.width > photo.height)
                if not correct_orientation: continue
                if hasattr(photo, 'large2x'):
                    img_url = photo.large2x; print(f"      - Downloading background: {os.path.basename(img_url)}")
                    img_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_{len(bg_image_paths)}.jpg")
                    response = utils.make_request_with_retries(img_url, timeout=60)
                    if response:
                        with open(img_path, 'wb') as f: f.write(response.content)
                        try: Image.open(img_path).verify(); bg_image_paths.append(img_path); found_urls.add(photo.url)
                        except (IOError, SyntaxError): print(f"      -  WARNING: Downloaded file {img_path} is corrupt. Skipping.")
        assets['bg_images'] = bg_image_paths; assets['bg_credit'] = "Photos by Pexels" if bg_image_paths else None
        if not bg_image_paths: print("      -  WARNING: Pexels search returned no suitable images after filtering.")
    except Exception as e: print(f"      -  WARNING: Pexels API failed: {e}. Continuing with solid color backgrounds.")
    return assets

# --- STORY SCRIPTS ---
def run_story_news(query, video_format, out_path, theme, icon_svg):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: News Reporter")
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    all_news = (data_fetcher.fetch_yfinance_news(y_symbol) + data_fetcher.fetch_google_news(display, nse_symbol) + data_fetcher.fetch_moneycontrol_news(display) + data_fetcher.fetch_economic_times_news(display) + data_fetcher.fetch_trendlyne_announcements(nse_symbol))
    scored_news = [{**item, 'score': data_fetcher.score_news_relevance(item['title'], display, item['source'])} for item in all_news]
    unique_news = []; [unique_news.append(item) for item in sorted(scored_news, key=lambda x: x['score'], reverse=True) if not any(utils.seq_ratio(item['title'], un['title']) > 0.85 for un in unique_news)]
    news_items = unique_news[:config.MAX_NEWS_ITEMS]
    if not news_items: print("   -> No relevant news found. Cannot generate news video."); return
    print(f"\n✅ Top {len(news_items)} headlines selected:"); [print(f"   {i+1}. {item['title']} (Source: {item['source']})") for i, item in enumerate(news_items)]
    llm_narrations = {}
    print("\n--- Generating News Analysis with Local LLM ---")
    for i, item in enumerate(news_items):
        prompt = f"""You are a financial analyst creating a script for a short video. Your tone is simple, informative, and neutral. Given the following news headline for the company '{display}': "{item['title']}"
        1. Briefly explain what this headline means in simple terms.
        2. Explain the potential positive impact OR potential negative impact this could have on the company.
        3. Generate a concise, 2-3 sentence narration for a video script based on this analysis. Do not give financial advice. Do not repeat the headline.
        Your narration:"""
        analysis = utils.query_local_llm(prompt)
        if analysis:
            print(f"      - LLM Analysis for News {i+1}: {analysis}")
            llm_narrations[f"news_{i+1}"] = analysis
    df, _ = data_fetcher.fetch_price_data(y_symbol); snap = data_fetcher.compute_price_snapshot(df)
    script_parts = content_creator.build_narration_news(display, news_items, snap)
    if llm_narrations: script_parts.update(llm_narrations); print("   -> Successfully replaced headlines with LLM-generated analysis.")
    audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nDaily Briefing", 'logo': True}]
    for i, item in enumerate(news_items): slides.append({'type': 'news', 'key': f'news_{i+1}', 'text': item['title'], 'icon': utils.classify_impact(item['title'])})
    slides.append({'type': 'chart', 'key': 'market', 'path': price_chart_path, 'blur_bg': True}); slides.append({'type': 'cta', 'key': 'cta'})
    assets = fetch_pexels_bgs(len(slides), display, video_format); assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg)

def run_story_deepdive(query, video_format, out_path, theme, icon_svg):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: Stock 101 Deep Dive")
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
    yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
    df, _ = data_fetcher.fetch_price_data(y_symbol)
    all_metrics = {**tt_data['metrics'], **{k: v for k, v in yfinance_details.items() if k in ['52-Wk High', '52-Wk Low']}}
    details = {'name': display, 'summary': tt_data['profile'], 'ceo': yfinance_details['ceo'], 'peers': list(tt_data['peers'].keys()) if tt_data['peers'] else []}
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    metrics_path = chart_generator.make_metrics_infographic(all_metrics, chart_size, theme) if all_metrics else None
    financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme)
    shareholding_path = chart_generator.make_shareholding_chart(tt_data['shareholding'], chart_size, theme) if tt_data['shareholding'] else None
    price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nStock Deep Dive", 'logo': True}]
    if details.get("summary"): slides.append({'type': 'summary', 'key': 'profile', 'text': details['summary']})
    if details.get("ceo"): slides.append({'type': 'summary', 'key': 'management', 'text': f"Led by:\n{details['ceo']}", 'is_title': True})
    if details.get("peers"):
        competitors_text = "Key Competitors:\n\n" + "\n".join(f"- {p}" for p in details['peers'] if p != nse_symbol)
        slides.append({'type': 'summary', 'key': 'competitors', 'text': competitors_text})
    if metrics_path: slides.append({'type': 'chart', 'key': 'metrics', 'path': metrics_path, 'blur_bg': True})
    if financials_path: slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path, 'blur_bg': True})
    if shareholding_path: slides.append({'type': 'chart', 'key': 'shareholding', 'path': shareholding_path, 'blur_bg': True})
    if price_chart_path: slides.append({'type': 'chart', 'key': 'market', 'path': price_chart_path, 'blur_bg': True})
    slides.append({'type': 'cta', 'key': 'cta'})
    assets = fetch_pexels_bgs(len(slides), display, video_format); assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    script_parts = content_creator.build_narration_deepdive(details, all_metrics, tt_data['shareholding'], peers_exist=bool(details.get("peers")))
    audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg)

def run_story_comparison(query_a, query_b, video_format, out_path, theme, icon_svg):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: Stock vs. Stock"); print(f"\n--- Fetching data for Primary Stock: {query_a} ---")
    nse_a, y_a, display_a = data_fetcher.resolve_symbol(query_a); tt_data_a = data_fetcher.fetch_tickertape_data(nse_a); df_a, _ = data_fetcher.fetch_price_data(y_a)
    print("\n--- Pausing briefly ---"); time.sleep(random.uniform(2, 4))
    print(f"\n--- Fetching data for Competitor Stock: {query_b} ---"); nse_b, y_b, display_b = data_fetcher.resolve_symbol(query_b); tt_data_b = data_fetcher.fetch_tickertape_data(nse_b); df_b, _ = data_fetcher.fetch_price_data(y_b)
    print("\n--- Generating Comparison Charts ---"); chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    pe_chart_path = chart_generator.make_comparison_bar_chart("P/E Ratio", tt_data_a['metrics'].get("P/E Ratio"), tt_data_b['metrics'].get("P/E Ratio"), display_a, display_b, chart_size, theme, out_png="outputs/tmp/pe_comp.png")
    mcap_chart_path = chart_generator.make_comparison_bar_chart("Market Cap (Cr)", tt_data_a['metrics'].get("Market Cap (Cr)"), tt_data_b['metrics'].get("Market Cap (Cr)"), display_a, display_b, chart_size, theme, out_png="outputs/tmp/mcap_comp.png")
    price_chart_path = chart_generator.make_stock_vs_stock_price_chart(df_a, df_b, display_a, display_b, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display_a}\nvs.\n{display_b}", 'logo': False}]
    if pe_chart_path: slides.append({'type': 'chart', 'key': 'pe_compare', 'path': pe_chart_path, 'blur_bg': True})
    if mcap_chart_path: slides.append({'type': 'chart', 'key': 'mcap_compare', 'path': mcap_chart_path, 'blur_bg': True})
    if price_chart_path: slides.append({'type': 'chart', 'key': 'price_compare', 'path': price_chart_path, 'blur_bg': True})
    slides.append({'type': 'cta', 'key': 'cta'})
    assets = fetch_pexels_bgs(len(slides), display_a, video_format)
    script_parts = content_creator.build_narration_comparison(display_a, display_b, tt_data_a['metrics'], tt_data_b['metrics'])
    audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    video_renderer.make_video(slides, audio_paths, display_a, f"{nse_a}_vs_{nse_b}", video_format, out_path, assets, theme, icon_svg)

def run_story_spotlight(query, video_format, out_path, theme, icon_svg):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print("Running Story: Portfolio Spotlight")
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query); tt_data = data_fetcher.fetch_tickertape_data(nse_symbol); yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
    narration_details = {'name': display, **yfinance_details}
    print("\n--- Generating Spotlight Charts ---"); chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme)
    roe_path = chart_generator.make_single_metric_chart("Return on Equity", yfinance_details.get("returnOnEquity"), display, chart_size, theme) if yfinance_details.get("returnOnEquity") else None
    shareholding_path = chart_generator.make_shareholding_chart(tt_data['shareholding'], chart_size, theme) if tt_data['shareholding'] else None
    valuation_path = chart_generator.make_single_metric_chart("P/E Ratio", tt_data['metrics'].get("P/E Ratio"), display, chart_size, theme) if tt_data['metrics'] and "P/E Ratio" in tt_data['metrics'] else None
    peer_chart_path = chart_generator.make_peer_comparison_chart(tt_data['peers'], display, chart_size, theme) if tt_data['peers'] else None
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nInvestor Spotlight", 'logo': True}]
    slides.append({'type': 'summary', 'key': 'profitability_intro', 'text': "Lens 1:\nProfitability", 'is_title': True})
    if financials_path: slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path, 'blur_bg': True})
    if roe_path: slides.append({'type': 'chart', 'key': 'roe', 'path': roe_path, 'blur_bg': True})
    if shareholding_path:
        slides.append({'type': 'summary', 'key': 'ownership_intro', 'text': "Lens 2:\nOwnership", 'is_title': True})
        slides.append({'type': 'chart', 'key': 'ownership', 'path': shareholding_path, 'blur_bg': True})
    if valuation_path or peer_chart_path:
        slides.append({'type': 'summary', 'key': 'valuation_intro', 'text': "Lens 3:\nValuation", 'is_title': True})
        if valuation_path: slides.append({'type': 'chart', 'key': 'valuation', 'path': valuation_path, 'blur_bg': True})
        if peer_chart_path: slides.append({'type': 'chart', 'key': 'peers', 'path': peer_chart_path, 'blur_bg': True})
    slides.append({'type': 'summary', 'key': 'summary', 'text': "This analysis provides a structured way to evaluate a company, but is not financial advice."}); slides.append({'type': 'cta', 'key': 'cta'})
    assets = fetch_pexels_bgs(len(slides), display, video_format)
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    dummy_audio_script = {"ownership_intro": ". . .", "valuation_intro": ". . .", "profitability_intro": ". . ."}
    script_parts = content_creator.build_narration_spotlight(narration_details, tt_data['metrics'], tt_data['shareholding'], peers_exist=bool(tt_data['peers']))
    script_parts.update(dummy_audio_script)
    audio_paths = content_creator.generate_segmented_voiceover(script_parts)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg)

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
    
    icon_svg = {
        "positive": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="{theme["accent"]}" d="m280-400 200-200 200 200H280Z"/></svg>',
        "negative": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#F44336" d="M480-560 280-760h400L480-560Z"/></svg>',
        "uncertain": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>',
        "like": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="{theme["accent"]}" d="M720-120H280v-520l280-280 50 50q7 7 11.5 19t4.5 23v14l-44 214h258q32 0 56 24t24 56v80q0 7-2 15t-4 15L794-168q-9 20-30 34t-44 14Zm-360-80h360l120-280v-80H480l54-260-174 174v446Zm0 80Z"/></svg>',
        "comment": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M240-400h480v-80H240v80Zm0-120h480v-80H240v80Zm0-120h480v-80H240v80ZM80-80v-720q0-33 23.5-56.5T160-880h640q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H240L80-80Zm80-200h640v-480H160v525l40-45Z"/></svg>',
        "share": '<svg xmlns="http://www.w3.org/2000/svg" height="48" viewBox="0 -960 960 960" width="48"><path fill="#FFFFFF" d="M720-80q-50 0-85-35t-35-85q0-7 1-14.5t3-13.5L322-382q-18 13-40 21t-42 8q-50 0-85-35t-35-85q0-50 35-85t85-35q20 0 40 7.5t38 20.5l282-164q-2-6-2.5-12.5T600-720q0-50 35-85t85-35q50 0 85 35t35 85q0 50-35 85t-85 35q-20 0-38-7.5t-40-20.5L340-542q2 6 2.5 12.5t.5 13.5q0 7-1 14t-3 14l282 164q18-13 40-21t42-8q50 0 85 35t35 85q0 50-35 85t-85 35Zm0-640q17 0 28.5-11.5T760-760q0-17-11.5-28.5T720-800q-17 0-28.5 11.5T680-760q0-17 11.5 28.5T720-720ZM240-440q17 0 28.5-11.5T280-480q0-17-11.5-28.5T240-520q-17 0-28.5 11.5T200-480q0-17 11.5 28.5T240-440Zm480 280q17 0 28.5-11.5T760-200q0-17-11.5-28.5T720-240q-17 0-28.5 11.5T680-200q0-17 11.5 28.5T720-160Z"/></svg>'
    }

    try:
        out_path = args.out
        story_map = {'news': run_story_news, 'deepdive': run_story_deepdive, 'comparison': run_story_comparison, 'spotlight': run_story_spotlight}
        query_map = {'news': 1, 'deepdive': 1, 'comparison': 2, 'spotlight': 1}
        story_func = story_map.get(args.type)
        num_queries = query_map.get(args.type)
        if len(args.queries) != num_queries:
            parser.error(f"'{args.type}' type requires exactly {num_queries} quer{'y' if num_queries == 1 else 'ies'}.")
        if args.type == 'comparison':
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0]}_vs_{args.queries[1]}_{args.type}_{args.format}.mp4")
            story_func(args.queries[0], args.queries[1], args.format, out_path, theme, icon_svg)
        else:
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0]}_{args.type}_{args.format}.mp4")
            story_func(args.queries[0], args.format, out_path, theme, icon_svg)
        if out_path and os.path.exists(out_path):
            print("\n--- Independent File Verification ---")
            if os.path.getsize(out_path) > 1024: print(f"✅✅✅ SUCCESS: Video created at '{out_path}' (Size: {os.path.getsize(out_path)/1024/1024:.2f} MB)")
            else: print("⚠️ WARNING: Output file is very small. It might be corrupt.")
        elif args.type in story_map:
            print("❌❌❌ FAILURE: Output file not found. An error likely occurred during rendering.")
    except Exception as e:
        print(f"\n❌ An error occurred during the main process setup: {e}"); traceback.print_exc()

if __name__ == "__main__":
    try: multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError: pass
    main_app()
