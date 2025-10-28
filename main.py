import argparse
import os
import random
import time
import traceback
import multiprocessing
from PIL import Image
import logging

import config
import utils

try:
    from pexels_api import API
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False

def fetch_background_assets(num_bgs_needed, company_name, business_summary, video_format):
    assets = {}
    if not (PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY")):
        print("   -> Pexels API not configured. Skipping background image search.")
        return assets
    if num_bgs_needed <= 0: return assets
    print(f"\n   -> Fetching {num_bgs_needed} background images from Pexels...")
    try:
        api = API(os.getenv("PEXELS_API_KEY")); search_queries = utils.get_llm_search_terms(company_name, business_summary); fallback_queries = ["corporate", "stock", "finance", "abstract", "technology", company_name.split()[0]]
        if not search_queries: print("      - Using fallback keywords as primary search."); search_queries = fallback_queries
        else: search_queries.extend(fallback_queries)
        unique_queries = list(dict.fromkeys(search_queries)); print(f"      - Final search query priority: {unique_queries[:8]}...")
        image_paths = []; is_portrait = (video_format == 'portrait'); found_urls = set()
        images_per_keyword = 2 if len(unique_queries) > 4 else 3
        for query in unique_queries:
            if len(image_paths) >= num_bgs_needed: break
            print(f"      - Searching Pexels for: '{query}'"); photos_found_this_query = 0; api.search(query, page=random.randint(1, 5), results_per_page=40)
            for photo in api.get_entries():
                if len(image_paths) >= num_bgs_needed or photos_found_this_query >= images_per_keyword: break
                if photo.url in found_urls: continue
                correct_orientation = (photo.height > photo.width) if is_portrait else (photo.width > photo.height)
                if not correct_orientation: continue
                if hasattr(photo, 'large2x'):
                    img_url = photo.large2x; print(f"        - Downloading Pexels background: {os.path.basename(img_url)}")
                    img_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_pexels_{len(image_paths)}.jpg")
                    response = utils.make_request_with_retries(img_url, timeout=60)
                    if response:
                        with open(img_path, 'wb') as f: f.write(response.content)
                        try: Image.open(img_path).verify(); image_paths.append(img_path); found_urls.add(photo.url); photos_found_this_query += 1
                        except (IOError, SyntaxError): print(f"        -  WARNING: Downloaded file {img_path} is corrupt. Skipping.")
        assets['bg_images'] = image_paths; assets['bg_credit'] = "Photos by Pexels" if image_paths else None
        if not image_paths: print("      -  WARNING: Pexels search returned no suitable images after filtering.")
    except Exception as e: print(f"      -  WARNING: Pexels API failed: {e}. Continuing with solid color backgrounds.")
    return assets

def run_story_news(query, video_format, out_path, theme, icon_svg, lang='en'):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print(f"Running Story: News Reporter (Language: {lang})"); nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query); tt_data = data_fetcher.fetch_tickertape_data(nse_symbol); yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
    all_news = (data_fetcher.fetch_yfinance_news(y_symbol) + data_fetcher.fetch_google_news(display, nse_symbol) + data_fetcher.fetch_moneycontrol_news(display) + data_fetcher.fetch_economic_times_news(display) + data_fetcher.fetch_trendlyne_announcements(nse_symbol)); scored_news = [{**item, 'score': data_fetcher.score_news_relevance(item['title'], display, item['source'])} for item in all_news]; unique_news = []
    for item in sorted(scored_news, key=lambda x: x['score'], reverse=True):
        if not any(utils.seq_ratio(item['title'], un['title']) > 0.85 for un in unique_news): unique_news.append(item)
    news_items = unique_news[:config.MAX_NEWS_ITEMS]
    if not news_items: print("   -> No relevant news found. Cannot generate news video."); return
    print(f"\n✅ Top {len(news_items)} headlines selected:"); [print(f"   {i+1}. {item['title']} (Source: {item['source']})") for i, item in enumerate(news_items)]
    llm_narrations = {}; print("\n--- Generating News Analysis with Local LLM ---")
    for i, item in enumerate(news_items):
        prompt = f"""You are a financial analyst. Summarize the key takeaway of this headline in one short, impactful sentence for a video script: "{item['title']}"."""; analysis = utils.query_local_llm(prompt, max_words=45)
        if analysis: print(f"      - LLM Analysis for News {i+1}: {analysis}"); llm_narrations[f"news_{i+1}"] = analysis
    df, _ = data_fetcher.fetch_price_data(y_symbol); snap = data_fetcher.compute_price_snapshot(df)
    english_script_parts = content_creator.build_english_narration_news(display, news_items, snap, llm_narrations)
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang); audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500); price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nDaily Briefing", 'logo': True}];
    for i, item in enumerate(news_items): slides.append({'type': 'news', 'key': f'news_{i+1}', 'text': item['title'], 'icon': utils.classify_impact(item['title'])})
    slides.append({'type': 'chart', 'key': 'market', 'path': price_chart_path, 'blur_bg': True}); slides.append({'type': 'cta', 'key': 'cta'}); assets = fetch_background_assets(len(slides), display, tt_data.get('profile'), video_format); assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg, lang=lang)

def run_story_deepdive(query, video_format, out_path, theme, icon_svg, lang='en'):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print(f"Running Story: Stock 101 Deep Dive (Language: {lang})"); nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query); tt_data = data_fetcher.fetch_tickertape_data(nse_symbol); yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol); df, _ = data_fetcher.fetch_price_data(y_symbol); all_metrics = {**yfinance_details, **tt_data.get('metrics', {})}; details = {'name': display, 'summary': tt_data.get('profile'), 'ceo': yfinance_details.get('ceo'), 'peers': list(tt_data.get('peers', {}).keys()) if tt_data.get('peers') else []}; chart_size = (1200, 600) if video_format == 'landscape' else (680, 500); metrics_path = chart_generator.make_metrics_infographic(all_metrics, chart_size, theme) if all_metrics else None; financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme); shareholding_path = chart_generator.make_shareholding_chart(tt_data.get('shareholding'), chart_size, theme) if tt_data.get('shareholding') else None; price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme); sector_scale_path = chart_generator.make_sector_infographic(tt_data.get('sector'), all_metrics.get('Market Cap (Cr)'), chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nStock Deep Dive", 'logo': True}];
    if details.get("summary"): slides.append({'type': 'summary', 'key': 'profile', 'text': details['summary']})
    if sector_scale_path: slides.append({'type': 'chart', 'key': 'sector_scale', 'path': sector_scale_path, 'blur_bg': True})
    if details.get("ceo"): slides.append({'type': 'summary', 'key': 'management', 'text': f"Led by:\n{details['ceo']}", 'is_title': True})
    if details.get("peers"): competitors_text = "Key Competitors:\n\n" + "\n".join(f"- {p}" for p in details['peers'] if p != nse_symbol); slides.append({'type': 'summary', 'key': 'competitors', 'text': competitors_text})
    if metrics_path: slides.append({'type': 'chart', 'key': 'metrics', 'path': metrics_path, 'blur_bg': True})
    if financials_path: slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path, 'blur_bg': True})
    if shareholding_path: slides.append({'type': 'chart', 'key': 'shareholding', 'path': shareholding_path, 'blur_bg': True})
    if price_chart_path: slides.append({'type': 'chart', 'key': 'market', 'path': price_chart_path, 'blur_bg': True})
    slides.append({'type': 'cta', 'key': 'cta'}); assets = fetch_background_assets(len(slides), display, tt_data.get('profile'), video_format); assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    english_script_parts = content_creator.build_english_narration_deepdive(details, all_metrics, tt_data.get('shareholding'), peers_exist=bool(details.get("peers")))
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang); audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg, lang=lang)

def run_story_comparison(queries, video_format, out_path, theme, icon_svg, lang='en'):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print(f"Running Story: Stock vs. Stock (Language: {lang})"); all_stock_data = []
    for i, query in enumerate(queries):
        print(f"\n--- Fetching data for Stock {i+1}: {query} ---"); nse, y_symbol, display = data_fetcher.resolve_symbol(query); tt_data = data_fetcher.fetch_tickertape_data(nse); yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol); combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}; df, _ = data_fetcher.fetch_price_data(y_symbol); quarterly_financials = data_fetcher.fetch_quarterly_financials(y_symbol); stock_info = {"nse": nse, "display": display, "metrics": combined_metrics, "df": df, "logo": data_fetcher.fetch_company_logo(y_symbol), "quarterly_financials": quarterly_financials, "profile": tt_data.get('profile')}; all_stock_data.append(stock_info)
        if i < len(queries) - 1: print("\n--- Pausing briefly ---"); time.sleep(random.uniform(2, 4))
    print("\n--- Generating Comparison Charts ---"); chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    pe_data = {d['display']: d['metrics'].get("P/E Ratio") for d in all_stock_data}; pb_data = {d['display']: d['metrics'].get("P/B Ratio") for d in all_stock_data}; mcap_data = {d['display']: d['metrics'].get("Market Cap (Cr)") for d in all_stock_data}; q_rev_data = {d['display']: d['quarterly_financials'].get("Quarterly Revenue (Cr)") for d in all_stock_data}; q_profit_data = {d['display']: d['quarterly_financials'].get("Quarterly Profit (Cr)") for d in all_stock_data}; perf_data = {}
    for data in all_stock_data:
        try: low_52wk, last_price = data['metrics'].get("52-Wk Low"), data['df']['Close'].iloc[-1]; perf_data[data['display']] = ((last_price / low_52wk) - 1) * 100 if low_52wk is not None and low_52wk > 0 else None
        except (ValueError, TypeError, KeyError, IndexError): perf_data[data['display']] = None
    pe_chart_path = chart_generator.make_comparison_bar_chart("P/E Ratio", pe_data, chart_size, theme, out_png="outputs/tmp/pe_comp.png"); pb_chart_path = chart_generator.make_comparison_bar_chart("P/B Ratio", pb_data, chart_size, theme, out_png="outputs/tmp/pb_comp.png"); mcap_chart_path = chart_generator.make_comparison_bar_chart("Market Cap (Cr)", mcap_data, chart_size, theme, out_png="outputs/tmp/mcap_comp.png"); q_rev_chart_path = chart_generator.make_comparison_bar_chart("Latest Quarterly Revenue (Cr)", q_rev_data, chart_size, theme, out_png="outputs/tmp/q_rev_comp.png"); q_profit_chart_path = chart_generator.make_comparison_bar_chart("Latest Quarterly Profit (Cr)", q_profit_data, chart_size, theme, out_png="outputs/tmp/q_profit_comp.png"); perf_chart_path = chart_generator.make_comparison_bar_chart("Gain from 52-Wk Low (%)", perf_data, chart_size, theme, out_png="outputs/tmp/perf_comp.png"); price_dfs = [d['df'] for d in all_stock_data]; price_names = [d['display'] for d in all_stock_data]; price_chart_path = chart_generator.make_stock_vs_stock_price_chart(price_dfs, price_names, chart_size, theme)
    slides = [{'type': 'intro', 'key': 'intro', 'text': "\nvs.\n".join([d['display'] for d in all_stock_data]), 'logos': [d['logo'] for d in all_stock_data]}]
    if pe_chart_path: slides.append({'type': 'chart', 'key': 'pe_compare', 'path': pe_chart_path, 'blur_bg': True})
    if pb_chart_path: slides.append({'type': 'chart', 'key': 'pb_compare', 'path': pb_chart_path, 'blur_bg': True})
    if mcap_chart_path: slides.append({'type': 'chart', 'key': 'mcap_compare', 'path': mcap_chart_path, 'blur_bg': True})
    if q_rev_chart_path: slides.append({'type': 'chart', 'key': 'q_revenue_compare', 'path': q_rev_chart_path, 'blur_bg': True})
    if q_profit_chart_path: slides.append({'type': 'chart', 'key': 'q_profit_compare', 'path': q_profit_chart_path, 'blur_bg': True})
    if perf_chart_path: slides.append({'type': 'chart', 'key': 'perf_compare', 'path': perf_chart_path, 'blur_bg': True})
    if price_chart_path: slides.append({'type': 'chart', 'key': 'price_compare', 'path': price_chart_path, 'blur_bg': True})
    slides.append({'type': 'cta', 'key': 'cta'}); combined_summary = ". ".join([d['profile'] for d in all_stock_data if d.get('profile')]); comparison_name = " vs ".join([d['display'] for d in all_stock_data])
    assets = fetch_background_assets(len(slides), comparison_name, combined_summary, video_format)
    english_script_parts = content_creator.build_english_narration_comparison(all_stock_data)
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang); audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    video_renderer.make_video(slides, audio_paths, all_stock_data[0]['display'], "comparison", video_format, out_path, assets, theme, icon_svg, lang=lang)

def run_story_spotlight(query, video_format, out_path, theme, icon_svg, lang='en'):
    import data_fetcher, chart_generator, content_creator, video_renderer
    print(f"Running Story: Portfolio Spotlight (Language: {lang})"); nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query); tt_data = data_fetcher.fetch_tickertape_data(nse_symbol); yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol); combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}; narration_details = {'name': display, **yfinance_details}; print("\n--- Generating Spotlight Charts ---"); chart_size = (1200, 600) if video_format == 'landscape' else (680, 500); financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme); roe_path = chart_generator.make_single_metric_chart("Return on Equity", yfinance_details.get("returnOnEquity"), display, chart_size, theme) if yfinance_details.get("returnOnEquity") else None; shareholding_path = chart_generator.make_shareholding_chart(tt_data.get('shareholding'), chart_size, theme) if tt_data.get('shareholding') else None; valuation_path = chart_generator.make_single_metric_chart("P/E Ratio", combined_metrics.get("P/E Ratio"), display, chart_size, theme) if combined_metrics and "P/E Ratio" in combined_metrics else None; peer_chart_path = chart_generator.make_peer_comparison_chart(tt_data.get('peers'), display, chart_size, theme) if tt_data.get('peers') else None
    slides = [{'type': 'intro', 'key': 'intro', 'text': f"{display}\nInvestor Spotlight", 'logo': True}]; slides.append({'type': 'summary', 'key': 'profitability_intro', 'text': "Lens 1:\nProfitability", 'is_title': True})
    if financials_path: slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path, 'blur_bg': True})
    if roe_path: slides.append({'type': 'chart', 'key': 'roe', 'path': roe_path, 'blur_bg': True})
    if shareholding_path: slides.append({'type': 'summary', 'key': 'ownership_intro', 'text': "Lens 2:\nOwnership", 'is_title': True}); slides.append({'type': 'chart', 'key': 'ownership', 'path': shareholding_path, 'blur_bg': True})
    if valuation_path or peer_chart_path: slides.append({'type': 'summary', 'key': 'valuation_intro', 'text': "Lens 3:\nValuation", 'is_title': True});
    if valuation_path: slides.append({'type': 'chart', 'key': 'valuation', 'path': valuation_path, 'blur_bg': True})
    if peer_chart_path: slides.append({'type': 'chart', 'key': 'peers', 'path': peer_chart_path, 'blur_bg': True})
    slides.append({'type': 'summary', 'key': 'summary', 'text': "This analysis provides a structured way to evaluate a company, but is not financial advice."}); slides.append({'type': 'cta', 'key': 'cta'}); assets = fetch_background_assets(len(slides), display, tt_data.get('profile'), video_format); assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    dummy_audio_script = {"ownership_intro": ",", "valuation_intro": ",", "profitability_intro": ","}
    english_script_parts = content_creator.build_english_narration_spotlight(narration_details, combined_metrics, tt_data.get('shareholding'), peers_exist=bool(tt_data.get('peers'))); english_script_parts.update(dummy_audio_script); audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang); audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    video_renderer.make_video(slides, audio_paths, display, nse_symbol, video_format, out_path, assets, theme, icon_svg, lang=lang)

def main_app():
    parser = argparse.ArgumentParser(description=f"Stock Video Content Engine v{config.__version__}"); parser.add_argument("queries", nargs='+', help="One to four company names/tickers."); parser.add_argument("--type", choices=['news', 'deepdive', 'comparison', 'spotlight'], required=True, help="The type of video to generate."); parser.add_argument("--format", choices=['landscape', 'portrait'], default='portrait', help="Video format."); parser.add_argument("--lang", choices=config.LANGUAGES.keys(), default='en', help="Language for the voiceover."); parser.add_argument("--out", help="Output MP4 path"); args = parser.parse_args()
    utils.ensure_dirs(); theme = random.choice(config.BASE_THEMES)
    theme['font'] = random.choice(config.FONT_PATHS) if config.FONT_PATHS else None
    if not theme['font']: raise IOError(f"No valid font files found.")
    print(f"  -> Using font: {theme['font']}")
    icon_svg = { "positive": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="{theme["accent"]}" d="m280-400 200-200 200 200H280Z"/></svg>', "negative": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="#F44336" d="M480-560 280-760h400L480-560Z"/></svg>', "neutral": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>', "uncertain": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="#9E9E9E" d="M200-450h560v-60H200v60Z"/></svg>', "like": f'<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="{theme["accent"]}" d="M720-120H280v-520l280-280 50 50q7 7 11.5 19t4.5 23v14l-44 214h258q32 0 56 24t24 56v80q0 7-2 15t-4 15L794-168q-9 20-30 34t-44 14Zm-360-80h360l120-280v-80H480l54-260-174 174v446Zm0 80Z"/></svg>', "comment": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="#FFFFFF" d="M240-400h480v-80H240v80Zm0-120h480v-80H240v80Zm0-120h480v-80H240v80ZM80-80v-720q0-33 23.5-56.5T160-880h640q33 0 56.5 23.5T880-800v480q0 33-23.5 56.5T800-240H240L80-80Zm80-200h640v-480H160v525l40-45Z"/></svg>', "share": '<svg xmlns="http://www.w3.org/2000/svg" height="48" width="48" viewBox="0 -960 960 960"><path fill="#FFFFFF" d="M720-80q-50 0-85-35t-35-85q0-7 1-14.5t3-13.5L322-382q-18 13-40 21t-42 8q-50 0-85-35t-35-85q0-50 35-85t85-35q20 0 40 7.5t38 20.5l282-164q-2-6-2.5-12.5T600-720q0-50 35-85t85-35q50 0 85 35t35 85q0 50-35 85t-85 35q-20 0-38-7.5t-40-20.5L340-542q2 6 2.5 12.5t.5 13.5q0 7-1 14t-3 14l282 164q18-13 40-21t42-8q50 0 85 35t35 85q0 50-35 85t-85 35Zm0-640q17 0 28.5-11.5T760-760q0-17-11.5-28.5T720-800q-17 0-28.5 11.5T680-760q0-17 11.5 28.5T720-720ZM240-440q17 0 28.5-11.5T280-480q0-17-11.5-28.5T240-520q-17 0-28.5 11.5T200-480q0-17 11.5 28.5T240-440Zm480 280q17 0 28.5-11.5T760-200q0-17-11.5-28.5T720-240q-17 0-28.5 11.5T680-200q0-17 11.5 28.5T720-160Z"/></svg>' }
    try:
        out_path = args.out; story_map = {'news': run_story_news, 'deepdive': run_story_deepdive, 'comparison': run_story_comparison, 'spotlight': run_story_spotlight}
        if args.type == 'comparison':
            if not (2 <= len(args.queries) <= 4): parser.error("'comparison' type requires between 2 and 4 queries.")
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{'_vs_'.join(q.replace(' ', '_') for q in args.queries)}_{args.type}_{args.format}.mp4")
            story_map[args.type](args.queries, args.format, out_path, theme, icon_svg, lang=args.lang)
        else:
            if len(args.queries) != 1: parser.error(f"'{args.type}' type requires exactly one query.")
            out_path = out_path or os.path.join(utils.get_script_dir(), "outputs", f"{args.queries[0].replace(' ', '_')}_{args.type}_{args.format}.mp4")
            story_map[args.type](args.queries[0], args.format, out_path, theme, icon_svg, lang=args.lang)
        if out_path and os.path.exists(out_path): print(f"\n--- Independent File Verification ---\n✅✅✅ SUCCESS: Video created at '{out_path}' (Size: {os.path.getsize(out_path)/1024/1024:.2f} MB)")
        else: print("❌❌❌ FAILURE: Output file not found. An error likely occurred during rendering.")
    except Exception as e: print(f"\n❌ An error occurred during the main process setup: {e}"); traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s'); logging.getLogger('matplotlib').setLevel(logging.WARNING); logging.getLogger('yfinance').setLevel(logging.WARNING); logging.getLogger('PIL').setLevel(logging.WARNING); logging.getLogger('peewee').setLevel(logging.WARNING); logging.getLogger('urllib3').setLevel(logging.WARNING)
    try: multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError: pass
    main_app()
