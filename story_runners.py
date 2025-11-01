# story_runners.py
# v20.2.7 - Refactored with modular functions and financials audio fix

import os
import random
import time
import traceback
from PIL import Image
import cv2

import config
import utils

try:
    from pexels_api import API
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False

# ==================== BACKGROUND ASSETS MANAGEMENT ====================

def fetch_background_assets(num_bgs_needed, company_name, business_summary, video_format, specific_queries=None):
    """Fetch professional background images from Pexels API"""
    assets = {}
    
    if not (PEXELS_AVAILABLE and os.getenv("PEXELS_API_KEY")):
        print("\n   -> ⚠️ WARNING: Pexels API key not found. Skipping background image search.")
        return assets
    
    if num_bgs_needed <= 0:
        return assets
    
    print(f"\n   -> Fetching {num_bgs_needed} professional background images from Pexels...")
    
    try:
        api = API(os.getenv("PEXELS_API_KEY"))
        search_queries = specific_queries if specific_queries else utils.get_llm_search_terms(company_name, business_summary)
        fallback_queries = ["abstract", "technology background", "finance infographic", "corporate building", "office interior", "architectural lines"]
        
        if not search_queries:
            search_queries = fallback_queries
        else:
            search_queries.extend(fallback_queries)

        negative_keywords = "-people,-face,-portrait,-flower,-crowd,-person,-model,-woman,-man,-hand"
        unique_queries = list(dict.fromkeys(search_queries))
        print(f"      - Final search query priority: {unique_queries[:8]}...")
        
        image_paths, found_urls = [], set()
        is_portrait = (video_format == 'portrait')
        
        # Sequential loop to ensure all keywords are tried
        for query in unique_queries:
            if len(image_paths) >= num_bgs_needed:
                break
            
            page = random.randint(1, 5)
            search_term = f"{query} {negative_keywords}"
            print(f"      - Searching Pexels page {page} for: '{search_term}'")
            
            try:
                api.search(search_term, page=page, results_per_page=80)
            except Exception as api_error:
                print(f"      - ❌ PEXELS API ERROR: {api_error}")
                continue
            
            if not api.get_entries():
                continue

            for photo in api.get_entries():
                if len(image_paths) >= num_bgs_needed:
                    break
                if photo.url in found_urls:
                    continue
                
                correct_orientation = (photo.height > photo.width) if is_portrait else (photo.width > photo.height)
                if not correct_orientation:
                    continue
                
                img_url = getattr(photo, 'large2x', photo.large)
                img_path = os.path.join(utils.get_script_dir(), "outputs", "tmp", f"bg_pexels_{len(image_paths)}.jpg")
                response = utils.make_request_with_retries(img_url, timeout=60)
                
                if response:
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    try:
                        Image.open(img_path).verify()
                        print(f"        - ✅ Found potential background: {os.path.basename(img_url)}")
                        image_paths.append(img_path)
                        found_urls.add(photo.url)
                    except (IOError, SyntaxError):
                        print(f"        - WARNING: Corrupt file {img_path}. Skipping.")
        
        assets_key = 'specific_bg_image' if specific_queries and num_bgs_needed == 1 else 'bg_images'
        assets[assets_key] = image_paths
        assets['bg_credit'] = "Photos by Pexels" if image_paths else None
        print(f"   -> Found {len(image_paths)}/{num_bgs_needed} suitable background images.")
        
    except Exception as e:
        print(f"      - WARNING: Unexpected error during background fetching: {e}")
        traceback.print_exc()
    
    return assets

# ==================== DEEPDIVE STORY FUNCTIONS ====================

def _generate_deepdive_charts(details, all_metrics, nse_symbol, y_symbol, df, chart_size, theme):
    """Generate all charts for deepdive story"""
    import chart_generator
    import data_fetcher
    
    charts = {
        'metrics': chart_generator.make_metrics_infographic(all_metrics, chart_size, theme) if all_metrics else None,
        'financials': chart_generator.make_financials_chart(y_symbol, chart_size, theme),
        'shareholding': chart_generator.make_shareholding_chart(details.get('shareholding'), chart_size, theme) if details.get('shareholding') else None,
        'price': chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme),
        'sector_scale': None
    }
    
    # Generate sector scale chart if we have sector or market cap data
    if details.get('sector') or all_metrics.get('Market Cap (Cr)'):
        print(f"   -> Generating sector infographic for {details.get('sector', 'unknown sector')}")
        charts['sector_scale'] = chart_generator.make_sector_infographic(
            details.get('sector'), 
            all_metrics.get('Market Cap (Cr)'), 
            chart_size, 
            theme
        )
        if charts['sector_scale'] and os.path.exists(charts['sector_scale']):
            print(f"   ✅ Sector scale chart created: {os.path.basename(charts['sector_scale'])}")
        else:
            print(f"   ❌ Sector scale chart generation failed")
    
    return charts

def _format_market_cap_display(market_cap):
    """Format market cap for better display"""
    if not market_cap:
        return None
        
    if market_cap >= 100000:  # 1 lakh crores = 1 trillion
        return f"₹{market_cap/100000:.1f} trillion"
    elif market_cap >= 1000:  # 1 thousand crores
        return f"₹{market_cap/1000:.1f} thousand crores"  
    else:
        return f"₹{market_cap:,.0f} crores"

def _build_deepdive_slides(display, details, all_metrics, charts):
    """Build slides for deepdive story with guaranteed financials slide"""
    story_theme = config.STORY_THEMES['deepdive']
    slides = [
        {'type': 'intro', 'key': 'intro', 'text': story_theme['intro_text'].format(company_name=display), 'logo': True}
    ]
    
    # Company profile
    if details.get("summary"):
        slides.append({'type': 'summary', 'key': 'profile', 'text': details['summary']})
    
    # Sector scale - with fallback
    if charts['sector_scale'] and os.path.exists(charts['sector_scale']):
        slides.append({'type': 'chart', 'key': 'sector_scale', 'path': charts['sector_scale'], 'blur_bg': False})
    elif details.get('sector') or all_metrics.get('Market Cap (Cr)'):
        sector_text = f"Sector: {details.get('sector', 'N/A')}"
        market_cap_display = _format_market_cap_display(all_metrics.get('Market Cap (Cr)'))
        if market_cap_display:
            sector_text += f"\nMarket Cap: {market_cap_display}"
        slides.append({'type': 'summary', 'key': 'sector_scale', 'text': sector_text})
    
    # Management
    if details.get("ceo"):
        slides.append({'type': 'summary', 'key': 'management', 'text': f"Led by:\n{details['ceo']}", 'is_title': True})
    
    # Competitors
    if details.get("peers"):
        competitors_text = "Key Competitors:\n\n" + "\n".join(f"- {p}" for p in details['peers'])
        slides.append({'type': 'summary', 'key': 'competitors', 'text': competitors_text})
    
    # FIXED: Ensure financials slide is always added
    if charts['financials'] and os.path.exists(charts['financials']):
        slides.append({'type': 'chart', 'key': 'financials', 'path': charts['financials'], 'blur_bg': True})
    else:
        # Fallback financials summary slide
        financials_text = "Financial Performance\n\nRevenue and profit trends"
        slides.append({'type': 'summary', 'key': 'financials', 'text': financials_text})
    
    # Other charts
    if charts['metrics'] and os.path.exists(charts['metrics']):
        slides.append({'type': 'chart', 'key': 'metrics', 'path': charts['metrics'], 'blur_bg': True})
    
    if charts['shareholding'] and os.path.exists(charts['shareholding']):
        slides.append({'type': 'chart', 'key': 'shareholding', 'path': charts['shareholding'], 'blur_bg': True})
    
    if charts['price'] and os.path.exists(charts['price']):
        slides.append({'type': 'chart', 'key': 'market', 'path': charts['price'], 'blur_bg': True})
    
    slides.append({'type': 'cta', 'key': 'cta'})
    
    return slides

def _ensure_financials_narration(english_script_parts, company_name):
    """Ensure financials narration exists, add fallback if missing"""
    if 'financials' not in english_script_parts:
        print("   ⚠️  WARNING: No financials narration generated, adding fallback")
        english_script_parts['financials'] = "Now let's examine the company's financial performance and revenue trends."
    return english_script_parts

def run_story_deepdive(query, video_format, out_path, theme, icon_svg, lang='en'):
    """Run deepdive story pipeline with enhanced error handling"""
    import data_fetcher
    import chart_generator
    import content_creator
    import video_renderer
    
    print(f"Running Story: Stock 101 Deep Dive (Language: {lang})")
    
    # Resolve symbol and fetch data
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
    yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
    df, _ = data_fetcher.fetch_price_data(y_symbol)
    all_metrics = {**yfinance_details, **tt_data.get('metrics', {})}
    
    details = {
        'name': display, 
        'summary': tt_data.get('profile'), 
        'ceo': yfinance_details.get('ceo'), 
        'peers': list(tt_data.get('peers', {}).keys()) if tt_data.get('peers') else [], 
        'sector': tt_data.get('sector'),
        'shareholding': tt_data.get('shareholding')
    }
    
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    
    # Generate all charts
    charts = _generate_deepdive_charts(details, all_metrics, nse_symbol, y_symbol, df, chart_size, theme)
    
    # Build slides with guaranteed financials
    slides = _build_deepdive_slides(display, details, all_metrics, charts)
    
    # DEBUG: Print slide keys for verification
    slide_keys = [slide['key'] for slide in slides]
    print(f"   ✅ Slides to be generated: {slide_keys}")
    
    # Fetch assets
    assets = fetch_background_assets(len(slides), display, tt_data.get('profile'), video_format)
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    
    # Build narration with financials guarantee
    english_script_parts = content_creator.build_english_narration_deepdive(
        details, all_metrics, tt_data.get('shareholding'), peers_exist=bool(details.get("peers"))
    )
    english_script_parts = _ensure_financials_narration(english_script_parts, display)
    
    # Generate audio and video
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang)
    audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    
    video_renderer.make_video(slides, audio_paths, display, "deepdive", video_format, out_path, assets, theme, icon_svg, lang=lang)

# ==================== NEWS STORY FUNCTIONS ====================

def run_story_news(query, video_format, out_path, theme, icon_svg, lang='en'):
    """Run news story pipeline"""
    import data_fetcher
    import chart_generator
    import content_creator
    import video_renderer
    
    print(f"Running Story: News Reporter (Language: {lang})")
    
    # Resolve symbol and fetch data
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
    
    # Fetch and score news
    all_news = (
        data_fetcher.fetch_yfinance_news(y_symbol) + 
        data_fetcher.fetch_google_news(display, nse_symbol) + 
        data_fetcher.fetch_moneycontrol_news(display) + 
        data_fetcher.fetch_economic_times_news(display) + 
        data_fetcher.fetch_trendlyne_announcements(nse_symbol)
    )
    
    scored_news = [
        {**item, 'score': data_fetcher.score_news_relevance(item['title'], display, item['source'])} 
        for item in all_news
    ]
    
    unique_news = []
    for item in sorted(scored_news, key=lambda x: x['score'], reverse=True):
        if not any(utils.seq_ratio(item['title'], un['title']) > 0.85 for un in unique_news):
            unique_news.append(item)
    
    news_items = unique_news[:config.MAX_NEWS_ITEMS]
    
    if not news_items:
        print("   -> No relevant news found. Cannot generate news video.")
        return
    
    print(f"\n✅ Top {len(news_items)} headlines selected:")
    for i, item in enumerate(news_items):
        print(f"   {i+1}. {item['title']} (Source: {item['source']})")
    
    # Fetch price data and snapshot
    df, _ = data_fetcher.fetch_price_data(y_symbol)
    snap = data_fetcher.compute_price_snapshot(df)
    
    # Build narration and generate audio
    english_script_parts = content_creator.build_english_narration_news(display, news_items, snap)
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang)
    audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    
    # Generate charts and build slides
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    price_chart_path = chart_generator.make_candlestick_chart(df, nse_symbol, chart_size, theme)
    
    story_theme = config.STORY_THEMES['news']
    slides = [
        {'type': 'intro', 'key': 'intro', 'text': story_theme['intro_text'].format(company_name=display), 'logo': True}
    ]
    
    for i, item in enumerate(news_items):
        slides.append({
            'type': 'news', 
            'key': f'news_{i+1}', 
            'text': item['title'], 
            'icon': utils.classify_impact(item['title'])
        })
    
    slides.extend([
        {'type': 'chart', 'key': 'market', 'path': price_chart_path, 'blur_bg': True},
        {'type': 'cta', 'key': 'cta'}
    ])
    
    # Fetch assets and render video
    assets = fetch_background_assets(len(slides), display, tt_data.get('profile'), video_format)
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    
    video_renderer.make_video(slides, audio_paths, display, "news", video_format, out_path, assets, theme, icon_svg, lang=lang)

# ==================== COMPARISON STORY FUNCTIONS ====================

def _fetch_comparison_stock_data(queries):
    """Fetch data for multiple companies for comparison"""
    import data_fetcher
    
    all_stock_data = []
    
    for i, q in enumerate(queries):
        print(f"\n--- Fetching data for Stock {i+1}: {q} ---")
        nse, y_symbol, display = data_fetcher.resolve_symbol(q)
        tt_data = data_fetcher.fetch_tickertape_data(nse)
        yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
        combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}
        df, _ = data_fetcher.fetch_price_data(y_symbol)
        quarterly_financials = data_fetcher.fetch_quarterly_financials(y_symbol)
        
        stock_info = {
            "nse": nse,
            "display": display,
            "metrics": combined_metrics,
            "df": df,
            "logo": data_fetcher.fetch_company_logo(y_symbol),
            "quarterly_financials": quarterly_financials,
            "profile": tt_data.get('profile')
        }
        all_stock_data.append(stock_info)
        
        if i < len(queries) - 1:
            time.sleep(random.uniform(2, 4))
    
    return all_stock_data

def _generate_comparison_charts(all_stock_data, chart_size, theme):
    """Generate comparison charts for multiple companies"""
    import chart_generator
    
    # Prepare comparison data
    pe_data = {d['display']: d['metrics'].get("P/E Ratio") for d in all_stock_data}
    pb_data = {d['display']: d['metrics'].get("P/B Ratio") for d in all_stock_data}
    mcap_data = {d['display']: d['metrics'].get("Market Cap (Cr)") for d in all_stock_data}
    q_rev_data = {d['display']: d['quarterly_financials'].get("Quarterly Revenue (Cr)") for d in all_stock_data}
    q_profit_data = {d['display']: d['quarterly_financials'].get("Quarterly Profit (Cr)") for d in all_stock_data}
    
    perf_data = {}
    for data in all_stock_data:
        try:
            low_52wk, last_price = data['metrics'].get("52-Wk Low"), data['df']['Close'].iloc[-1]
            perf_data[data['display']] = ((last_price / low_52wk) - 1) * 100 if low_52wk is not None and low_52wk > 0 else None
        except (ValueError, TypeError, KeyError, IndexError):
            perf_data[data['display']] = None
    
    # Generate comparison charts
    charts = {
        'pe': chart_generator.make_comparison_bar_chart("P/E Ratio", pe_data, chart_size, theme, out_png="outputs/tmp/pe_comp.png"),
        'pb': chart_generator.make_comparison_bar_chart("P/B Ratio", pb_data, chart_size, theme, out_png="outputs/tmp/pb_comp.png"),
        'mcap': chart_generator.make_comparison_bar_chart("Market Cap (Cr)", mcap_data, chart_size, theme, out_png="outputs/tmp/mcap_comp.png"),
        'q_rev': chart_generator.make_comparison_bar_chart("Latest Quarterly Revenue (Cr)", q_rev_data, chart_size, theme, out_png="outputs/tmp/q_rev_comp.png"),
        'q_profit': chart_generator.make_comparison_bar_chart("Latest Quarterly Profit (Cr)", q_profit_data, chart_size, theme, out_png="outputs/tmp/q_profit_comp.png"),
        'perf': chart_generator.make_comparison_bar_chart("Gain from 52-Wk Low (%)", perf_data, chart_size, theme, out_png="outputs/tmp/perf_comp.png"),
        'price': None
    }
    
    price_dfs = [d['df'] for d in all_stock_data]
    price_names = [d['display'] for d in all_stock_data]
    charts['price'] = chart_generator.make_stock_vs_stock_price_chart(price_dfs, price_names, chart_size, theme)
    
    return charts

def run_story_comparison(query, video_format, out_path, theme, icon_svg, lang='en'):
    """Run comparison story pipeline"""
    import data_fetcher
    import chart_generator
    import content_creator
    import video_renderer
    
    print(f"Running Story: Stock vs. Stock (Language: {lang})")
    
    # Fetch data for all companies
    all_stock_data = _fetch_comparison_stock_data(query)
    
    print("\n--- Generating Comparison Charts ---")
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    
    # Generate comparison charts
    charts = _generate_comparison_charts(all_stock_data, chart_size, theme)
    
    # Build slides
    story_theme = config.STORY_THEMES['comparison']
    slides = [{
        'type': 'intro', 
        'key': 'intro', 
        'text': "\nvs.\n".join([d['display'] for d in all_stock_data]), 
        'logos': [d['logo'] for d in all_stock_data]
    }]
    
    # Add comparison charts
    chart_mappings = [
        ('pe', 'pe_compare'),
        ('pb', 'pb_compare'),
        ('mcap', 'mcap_compare'),
        ('q_rev', 'q_revenue_compare'),
        ('q_profit', 'q_profit_compare'),
        ('perf', 'perf_compare'),
        ('price', 'price_compare')
    ]
    
    for chart_key, slide_key in chart_mappings:
        if charts[chart_key]:
            slides.append({'type': 'chart', 'key': slide_key, 'path': charts[chart_key], 'blur_bg': True})
    
    slides.append({'type': 'cta', 'key': 'cta'})
    
    # Prepare assets
    combined_summary = ". ".join([d['profile'] for d in all_stock_data if d.get('profile')])
    comparison_name = " vs ".join([d['display'] for d in all_stock_data])
    
    intro_keywords = ["versus abstract", "lines crossing", "competition graph", "head to head abstract", "geometric battle"]
    intro_assets = fetch_background_assets(1, comparison_name, "", video_format, specific_queries=intro_keywords)
    other_assets = fetch_background_assets(len(slides) - 1, comparison_name, combined_summary, video_format)
    assets = {**other_assets, **intro_assets}
    
    # Build narration and generate video
    english_script_parts = content_creator.build_english_narration_comparison(all_stock_data, slides)
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang)
    audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    
    video_renderer.make_video(slides, audio_paths, all_stock_data[0]['display'], "comparison", video_format, out_path, assets, theme, icon_svg, lang=lang)

# ==================== SPOTLIGHT STORY FUNCTIONS ====================

def run_story_spotlight(query, video_format, out_path, theme, icon_svg, lang='en'):
    """Run spotlight story pipeline"""
    import data_fetcher
    import chart_generator
    import content_creator
    import video_renderer
    
    print(f"Running Story: Portfolio Spotlight (Language: {lang})")
    
    # Fetch data
    nse_symbol, y_symbol, display = data_fetcher.resolve_symbol(query)
    tt_data = data_fetcher.fetch_tickertape_data(nse_symbol)
    yfinance_details = data_fetcher.fetch_yfinance_supplemental_details(y_symbol)
    combined_metrics = {**yfinance_details, **tt_data.get('metrics', {})}
    narration_details = {'name': display, **yfinance_details}
    
    print("\n--- Generating Spotlight Charts ---")
    chart_size = (1200, 600) if video_format == 'landscape' else (680, 500)
    
    # Generate charts
    financials_path = chart_generator.make_financials_chart(y_symbol, chart_size, theme)
    roe_path = chart_generator.make_single_metric_chart("Return on Equity", yfinance_details.get("returnOnEquity"), display, chart_size, theme) if yfinance_details.get("returnOnEquity") else None
    shareholding_path = chart_generator.make_shareholding_chart(tt_data.get('shareholding'), chart_size, theme) if tt_data.get('shareholding') else None
    valuation_path = chart_generator.make_single_metric_chart("P/E Ratio", combined_metrics.get("P/E Ratio"), display, chart_size, theme) if combined_metrics and "P/E Ratio" in combined_metrics else None
    peer_chart_path = chart_generator.make_peer_comparison_chart(tt_data.get('peers'), display, chart_size, theme) if tt_data.get('peers') else None
    
    # Build slides
    story_theme = config.STORY_THEMES['spotlight']
    slides = [
        {'type': 'intro', 'key': 'intro', 'text': story_theme['intro_text'].format(company_name=display), 'logo': True}
    ]
    
    # Profitability lens
    slides.append({'type': 'summary', 'key': 'profitability_intro', 'text': "Lens 1:\nProfitability", 'is_title': True})
    if financials_path:
        slides.append({'type': 'chart', 'key': 'financials', 'path': financials_path, 'blur_bg': True})
    if roe_path:
        slides.append({'type': 'chart', 'key': 'roe', 'path': roe_path, 'blur_bg': True})
    
    # Ownership lens
    if shareholding_path:
        slides.append({'type': 'summary', 'key': 'ownership_intro', 'text': "Lens 2:\nOwnership", 'is_title': True})
        slides.append({'type': 'chart', 'key': 'ownership', 'path': shareholding_path, 'blur_bg': True})
    
    # Valuation lens
    if valuation_path or peer_chart_path:
        slides.append({'type': 'summary', 'key': 'valuation_intro', 'text': "Lens 3:\nValuation", 'is_title': True})
    if valuation_path:
        slides.append({'type': 'chart', 'key': 'valuation', 'path': valuation_path, 'blur_bg': True})
    if peer_chart_path:
        slides.append({'type': 'chart', 'key': 'peers', 'path': peer_chart_path, 'blur_bg': True})
    
    slides.extend([
        {'type': 'summary', 'key': 'summary', 'text': "This analysis provides a structured way to evaluate a company, but is not financial advice."},
        {'type': 'cta', 'key': 'cta'}
    ])
    
    # Fetch assets
    spotlight_keywords = ["spotlight", "highlight", "focus", "lens", "magnifying glass", "analysis"]
    assets = fetch_background_assets(len(slides), display, tt_data.get('profile'), video_format, specific_queries=spotlight_keywords)
    assets['logo'] = data_fetcher.fetch_company_logo(y_symbol)
    
    # Build narration with lens introductions
    dummy_audio_script = {
        "ownership_intro": ",",
        "valuation_intro": ",", 
        "profitability_intro": ","
    }
    english_script_parts = content_creator.build_english_narration_spotlight(
        narration_details, combined_metrics, tt_data.get('shareholding'), peers_exist=bool(tt_data.get('peers'))
    )
    english_script_parts.update(dummy_audio_script)
    
    audio_script_parts = content_creator.build_audio_script(english_script_parts, lang=lang)
    audio_paths = content_creator.generate_segmented_voiceover(audio_script_parts, lang=lang)
    
    video_renderer.make_video(slides, audio_paths, display, "spotlight", video_format, out_path, assets, theme, icon_svg, lang=lang)
