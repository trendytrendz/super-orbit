# narration_builder.py
# v20.2.7 - Fixed market cap formatting and guaranteed financials narration

import utils
import config

def build_english_narration_news(company_name, news_items, price_snapshot):
    """Build narration script for news stories"""
    try:
        script_parts = {}
        
        # Intro
        context = f"Company: {company_name}. Recent price: {price_snapshot.get('last_price', 'N/A')}"
        script_parts['intro'] = utils.generate_plain_text_script(
            context, 
            "Create an engaging opening line for a financial news video about this company"
        )
        
        # News items
        for i, item in enumerate(news_items):
            context = f"News headline: {item['title']}. Source: {item['source']}. Company: {company_name}"
            script_parts[f'news_{i+1}'] = utils.generate_plain_text_script(
                context,
                f"Summarize this news in one engaging sentence for a voiceover"
            )
        
        # Market context
        market_context = f"Company: {company_name}. Current price: {price_snapshot.get('last_price', 'N/A')}. Change: {price_snapshot.get('change_percent', 'N/A')}%"
        script_parts['market'] = utils.generate_plain_text_script(
            market_context,
            "Provide a brief market context for this stock"
        )
        
        # CTA
        script_parts['cta'] = "Don't forget to like and subscribe for daily market updates!"
        
        return script_parts
        
    except Exception as e:
        print(f"❌ ERROR in news narration: {e}")
        return get_fallback_news_script(company_name, len(news_items))

def build_english_narration_deepdive(details, metrics, shareholding, peers_exist):
    """Build narration script for deepdive stories - FIXED MARKET CAP FORMATTING"""
    try:
        script_parts = {}
        company_name = details.get('name', 'This company')
        
        print(f"   -> Building DeepDive narration for {company_name}...")
        
        # Intro
        context = f"Company: {company_name}. Sector: {details.get('sector', 'Unknown')}"
        script_parts['intro'] = utils.generate_plain_text_script(
            context,
            "Create an engaging opening for a stock deepdive video"
        ) or f"Welcome to our deep dive analysis of {company_name}."
        
        # Company profile
        if details.get('summary'):
            context = f"Company profile: {details['summary'][:200]}..."
            script_parts['profile'] = utils.generate_plain_text_script(
                context,
                "Summarize what this company does in one engaging sentence"
            ) or f"{company_name} operates in the {details.get('sector', '')} sector."
        
        # Sector and scale - FIXED: Better market cap formatting
        sector = details.get('sector')
        market_cap_raw = metrics.get('Market Cap (Cr)')
        
        if sector or market_cap_raw:
            # Format market cap for better readability
            market_cap_display = ""
            if market_cap_raw:
                if market_cap_raw >= 100000:  # 1 lakh crores = 1 trillion
                    market_cap_display = f"₹{market_cap_raw/100000:.1f} trillion"
                elif market_cap_raw >= 1000:  # 1 thousand crores
                    market_cap_display = f"₹{market_cap_raw/1000:.1f} thousand crores"  
                else:
                    market_cap_display = f"₹{market_cap_raw:,.0f} crores"
                    
                context = f"Sector: {sector}. Market Cap: {market_cap_display}"
                print(f"      - Market Cap Context: {context}")
            else:
                context = f"Sector: {sector}"
                
            script_parts['sector_scale'] = utils.generate_plain_text_script(
                context,
                "Comment on the company's sector and market size using the exact market cap numbers provided"
            ) or f"{company_name} operates in the {sector} sector with a market cap of {market_cap_display if market_cap_raw else 'significant size'}."
        
        # Management
        if details.get('ceo'):
            context = f"CEO: {details['ceo']}. Company: {company_name}"
            script_parts['management'] = utils.generate_plain_text_script(
                context,
                "Mention the company leadership"
            ) or f"The company is led by {details['ceo']}."
        
        # Competitors
        if details.get('peers'):
            peers_text = ", ".join(details['peers'][:3])
            context = f"Main competitors: {peers_text}"
            script_parts['competitors'] = utils.generate_plain_text_script(
                context,
                "Mention key competitors"
            ) or f"Key competitors include {peers_text}."
        
        # FIXED: Better metric handling with guaranteed financials narration
        # Always generate financials narration if we have any financial data
        has_financial_data = any(metrics.get(key) for key in ['Revenue', 'Profit', 'Net Income', 'Total Revenue', 'Operating Income'])
        
        if has_financial_data:
            context = f"Financial performance of {company_name}"
            script_parts['financials'] = utils.generate_plain_text_script(
                context,
                "Comment on the company's financial performance and growth trends"
            ) or f"Now let's examine the financial performance of {company_name}."
        else:
            # Even if no data, create a placeholder
            script_parts['financials'] = f"Now let's look at the financial performance of {company_name}."
        
        # Other metrics
        key_metrics = {
            'metrics': ['P/E Ratio', 'P/B Ratio', 'ROE', 'Debt to Equity'],
            'shareholding': ['Promoter Holding', 'FII Holding', 'DII Holding'] if shareholding else []
        }
        
        for chart_type, metric_list in key_metrics.items():
            available_metrics = {metric: metrics.get(metric) for metric in metric_list if metrics.get(metric) is not None}
            if available_metrics:
                context = f"Key metrics for {company_name}: {', '.join([f'{k}: {v}' for k, v in available_metrics.items()])}"
                script_parts[chart_type] = utils.generate_plain_text_script(
                    context,
                    f"Comment on these {chart_type} metrics"
                ) or f"Now let's look at the {chart_type}."
        
        # Market performance
        script_parts['market'] = utils.generate_plain_text_script(
            f"Company: {company_name}",
            "Provide closing thoughts on this stock analysis"
        ) or f"That concludes our analysis of {company_name}."
        
        # CTA
        script_parts['cta'] = "Like this deep dive? Subscribe for more stock analysis!"
        
        # DEBUG: Print all generated narration keys
        print(f"   ✅ Narration keys generated: {list(script_parts.keys())}")
        
        return script_parts
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in DeepDive narration: {e}")
        import traceback
        traceback.print_exc()
        return get_fallback_deepdive_script(details.get('name', 'Unknown Company'))

def build_english_narration_comparison(stocks_data, slides):
    """Build narration script for comparison stories"""
    try:
        script_parts = {}
        stock_names = [stock['display'] for stock in stocks_data]
        
        # Intro
        context = f"Comparing companies: {' vs '.join(stock_names)}"
        script_parts['intro'] = utils.generate_plain_text_script(
            context,
            "Create an engaging opening for a stock comparison video"
        )
        
        # Chart narrations
        for slide in slides:
            if slide['type'] == 'chart':
                key = slide['key']
                metric_name = key.replace('_compare', '').replace('_', ' ').title()
                context = f"Comparing {metric_name} for {', '.join(stock_names)}"
                script_parts[key] = utils.generate_plain_text_script(
                    context,
                    f"Comment on the {metric_name} comparison between these companies"
                )
        
        # CTA
        script_parts['cta'] = "Which stock do you prefer? Vote in the comments!"
        
        return script_parts
        
    except Exception as e:
        print(f"❌ ERROR in comparison narration: {e}")
        return get_fallback_comparison_script([s['display'] for s in stocks_data])

def build_english_narration_spotlight(details, metrics, shareholding, peers_exist):
    """Build narration script for spotlight stories"""
    try:
        script_parts = {}
        company_name = details.get('name', 'This company')
        
        # Intro
        context = f"Company: {company_name}. Focus: Profitability, Ownership, Valuation"
        script_parts['intro'] = utils.generate_plain_text_script(
            context,
            "Create an engaging opening for an investor spotlight video"
        )
        
        # Lens sections
        lenses = {
            'profitability_intro': "Analyzing profitability metrics",
            'ownership_intro': "Examining ownership patterns", 
            'valuation_intro': "Evaluating valuation metrics"
        }
        
        for key, instruction in lenses.items():
            script_parts[key] = utils.generate_plain_text_script(
                f"Company: {company_name}. Analysis focus: {instruction}",
                f"Introduce the {instruction.split()[-1]} analysis section"
            )
        
        # Chart narrations - FIXED: Ensure financials has narration
        chart_mappings = {
            'financials': "financial performance and growth",
            'roe': "return on equity and efficiency",
            'ownership': "shareholding pattern and investor types",
            'valuation': "current valuation multiples", 
            'peers': "comparison with industry peers"
        }
        
        for chart_key, description in chart_mappings.items():
            # Always generate financials narration
            if chart_key == 'financials':
                context = f"Financial analysis of {company_name}"
                script_parts[chart_key] = utils.generate_plain_text_script(
                    context,
                    "Comment on the company's financial performance"
                ) or f"Let's examine the {description} of {company_name}."
            else:
                script_parts[chart_key] = utils.generate_plain_text_script(
                    f"Company: {company_name}. Analysis: {description}",
                    f"Comment on the {description}"
                )
        
        # Summary and CTA
        script_parts['summary'] = "This analysis provides a structured framework for stock evaluation."
        script_parts['cta'] = "Want more spotlights? Like and subscribe!"
        
        return script_parts
        
    except Exception as e:
        print(f"❌ ERROR in spotlight narration: {e}")
        return get_fallback_spotlight_script(details.get('name', 'Unknown Company'))

def build_audio_script(english_script_parts, lang='en'):
    """Convert English script to audio script format"""
    try:
        audio_script = {}
        
        for key, text in english_script_parts.items():
            if text and text.strip():
                if lang == 'hi':
                    audio_script[key] = text
                else:
                    audio_script[key] = text
            else:
                print(f"⚠️  Empty script for key: {key}, using fallback")
                audio_script[key] = f"Analysis point {key}"
        
        return audio_script
        
    except Exception as e:
        print(f"❌ ERROR building audio script: {e}")
        return {'intro': 'Welcome to our stock analysis.', 'cta': 'Thanks for watching!'}

# FALLBACK SCRIPTS
def get_fallback_deepdive_script(company_name):
    return {
        'intro': f"Welcome to our comprehensive analysis of {company_name}.",
        'profile': f"Let's examine the business fundamentals of {company_name}.",
        'sector_scale': "Now looking at the company's market position.",
        'management': "Next, the leadership team driving this company.",
        'competitors': "Here are the key players in this competitive landscape.",
        'metrics': "Analyzing key financial ratios and performance metrics.",
        'financials': "Reviewing revenue growth and profitability trends.",
        'shareholding': "Examining the ownership structure and investor types.",
        'market': "Finally, the stock's market performance and outlook.",
        'cta': "Found this analysis helpful? Subscribe for more deep dives!"
    }

def get_fallback_news_script(company_name, news_count):
    script = {
        'intro': f"Breaking news coverage for {company_name}.",
        'cta': "Stay updated with our daily market coverage!"
    }
    
    for i in range(news_count):
        script[f'news_{i+1}'] = f"News update {i+1} for {company_name}."
    
    script['market'] = f"Market context for {company_name}."
    return script

def get_fallback_comparison_script(company_names):
    names_text = " vs ".join(company_names)
    return {
        'intro': f"Head-to-head comparison: {names_text}.",
        'pe_compare': "Comparing valuation multiples.",
        'pb_compare': "Analyzing price-to-book ratios.", 
        'mcap_compare': "Market capitalization comparison.",
        'price_compare': "Stock performance analysis.",
        'cta': "Which stock would you choose? Comment below!"
    }

def get_fallback_spotlight_script(company_name):
    return {
        'intro': f"Investor spotlight on {company_name}.",
        'profitability_intro': "First lens: Profitability analysis.",
        'financials': "Revenue growth and margin trends.",
        'roe': "Return on equity and efficiency metrics.",
        'ownership_intro': "Second lens: Ownership structure.",
        'ownership': "Promoter and institutional holdings.",
        'valuation_intro': "Third lens: Valuation assessment.",
        'valuation': "Current valuation multiples.",
        'peers': "Comparison with industry peers.",
        'summary': "This completes our three-lens analysis framework.",
        'cta': "Like this format? Subscribe for more spotlights!"
    }

def get_fallback_narration(key, company_name):
    fallbacks = {
        'intro': f"Analysis of {company_name}.",
        'profile': f"Business overview of {company_name}.",
        'metrics': "Key financial metrics.",
        'financials': "Financial performance review.",
        'market': "Market performance analysis.",
        'cta': "Subscribe for more analysis!"
    }
    return fallbacks.get(key, "Analysis segment.")
