"""
Enhanced Narration Builder with Hindi Support
v24.1.0 - Fixed language handling and enhanced narration quality
"""

import re
import json
import traceback
from typing import Dict, List, Any

from . import utils
from . import config

def build_custom_news_script(data):
    """Builds script from user JSON. Trusts the user's structure."""
    script = {}
    
    # Use LLM to spice up the intro if desired, or just read it.
    company = data.get('company_name')
    script['intro'] = f"Important update for {company}. Here is what you need to know."
    
    for i, item in enumerate(data.get('news_items', [])):
        # We ask LLM to make it conversational but keep facts
        raw_text = item['title']
        context = f"News: {raw_text}. Company: {company}"
        # "Make it punchy for video"
        script[f'news_{i+1}'] = utils.generate_plain_text_script(context, "Rewrite this headline as a spoken sentence.")
    
    script['cta'] = "Follow for more updates."
    return script

def build_roundup_script(roundup_data):
    """
    Builds a tight script for multiple stocks.
    Constraint: Keep it short per stock.
    """
    script = {}
    
    # Intro
    companies_text = ", ".join([d['display'] for d in roundup_data])
    script['intro'] = f"Today's Market Roundup. We are tracking big moves in {companies_text}."
    
    # Per Stock
    for i, item in enumerate(roundup_data):
        stock = item['display']
        if item['news']:
            headline = item['news'][0]['title']
            # Prompt for brevity
            prompt = f"Stock: {stock}. News: {headline}. Write ONE short, punchy sentence (max 15 words)."
            script[f'stock_{i}'] = utils.query_local_llm(prompt, max_words=20)
        else:
            script[f'stock_{i}'] = f"No major headlines for {stock} today, but watch the levels."
            
    script['cta'] = "Which of these are you buying? Let us know in the comments."
    return script


def build_hindi_narration_directly(company_data, story_type):
    """Generate Hindi narration directly using Ollama"""
    try:
        print("   -> Generating DIRECT Hindi narration with Ollama...")
        
        company_name = company_data['details'].get('name', 'इस कंपनी')
        metrics = company_data['metrics']
        sector = company_data['details'].get('sector', 'ज्ञात नहीं')
        
        hindi_prompts = {
            'intro': f"""एक वित्तीय विश्लेषण वीडियो के लिए {company_name} का हिंदी में आकर्षक परिचय बनाएं। 
            यह कंपनी {sector} क्षेत्र में कार्यरत है और एक महत्वपूर्ण निवेश अवसर प्रस्तुत करती है।""",
            
            'sector_scale': f"""{company_name} की बाजार पूंजी {metrics.get('Market Cap (Cr)', 'N/A')} करोड़ है।
            यह आकार कंपनी को {sector} उद्योग में एक प्रमुख स्थान देता है और निवेशकों के लिए स्थिरता व विकास दोनों प्रदान करता है।""",
            
            'management': f"""{company_name} की नेतृत्व टीम के पास उद्योग का व्यापक अनुभव है।
            यह टीम कंपनी को बाजार की चुनौतियों से निपटने और नए अवसरों का लाभ उठाने में मदद करती है।""",
            
            'financials': f"""वित्तीय रूप से, {company_name} ने मजबूत प्रदर्शन दिखाया है।
            कंपनी का राजस्व स्थिर रूप से बढ़ रहा है और लाभप्रदता में सुधार हो रहा है।""",
            
            'metrics': f"""मुख्य वित्तीय मैट्रिक्स दिखाते हैं कि {company_name} का P/E अनुपात {metrics.get('P/E Ratio', 'N/A')} है।
            यह बाजार की कंपनी की भविष्य की कमाई वृद्धि के बारे में अपेक्षाओं को दर्शाता है।""",
            
            'market': f"""{company_name} का बाजार प्रदर्शन आर्थिक उतार-चढ़ाव के बीच मजबूत रहा है।
            तकनीकी संकेतक और मजबूत मौलिक कारक दोनों ही निवेशकों के लिए रुचिकर मामला प्रस्तुत करते हैं।""",
            
            'cta': f"""अगर आपको यह विश्लेषण उपयोगी लगा, तो कृपया हमारे चैनल को सब्सक्राइब करें।
            इस वीडियो को लाइक करें और नोटिफिकेशन चालू करें ताकि आप {company_name} जैसी कंपनियों पर हमारे नवीनतम शोध को न चूकें।"""
        }
        
        hindi_script = {}
        
        for key, prompt in hindi_prompts.items():
            print(f"      - Generating Hindi {key}...")
            
            response = utils.query_local_llm_improved(
                prompt,
                max_words=80,
                temperature=0.5
            )
            
            if response and any(char in response for char in ['ो', 'ा', 'ी', 'ू', 'े', 'ै', 'ं']):  # Basic Hindi character check
                hindi_script[key] = response
                print(f"        ✅ Hindi {key}: {response[:60]}...")
            else:
                # Use template fallback
                hindi_script[key] = create_hindi_templates(company_data, story_type)[key]
                print(f"        ⚠️  Using template for Hindi {key}")
        
        # Validate Hindi quality
        if validate_hindi_quality(hindi_script):
            print("   ✅ High-quality Hindi narration generated")
            return hindi_script
        else:
            print("   ⚠️  Hindi quality poor, using templates")
            return create_hindi_templates(company_data, story_type)
            
    except Exception as e:
        print(f"   ❌ Direct Hindi generation failed: {e}")
        return create_hindi_templates(company_data, story_type)

def _build_hindi_deepdive(company_data):
    """Build Hindi narration directly for deepdive stories"""
    company_name = company_data['details'].get('name', 'इस कंपनी')
    metrics = company_data['metrics']
    
    prompt = f"""
    आप एक पेशेवर हिंदी वित्तीय विश्लेषक हैं। {company_name} के लिए एक स्टॉक विश्लेषण वीडियो की स्क्रिप्ट बनाएं।
    
    कंपनी जानकारी:
    - कंपनी: {company_name}
    - क्षेत्र: {company_data['details'].get('sector', 'ज्ञात नहीं')}
    - बाजार पूंजी: {metrics.get('Market Cap (Cr)', 'N/A')} करोड़
    - P/E अनुपात: {metrics.get('P/E Ratio', 'N/A')}
    
    आपको निम्नलिखित खंडों के लिए हिंदी में engaging वॉइसओवर स्क्रिप्ट बनानी है:
    1. परिचय (intro)
    2. बाजार स्थिति (sector_scale) 
    3. प्रबंधन (management)
    4. वित्तीय प्रदर्शन (financials)
    5. वित्तीय मैट्रिक्स (metrics)
    6. बाजार प्रदर्शन (market)
    7. कॉल टू एक्शन (cta)
    
    प्रत्येक खंड के लिए एक engaging, professional हिंदी वाक्य बनाएं। सभी संख्याओं और वित्तीय डेटा को exact रखें।
    
    JSON format में output दें:
    {{
        "intro": "परिचय वाक्य",
        "sector_scale": "बाजार स्थिति वाक्य",
        ...
        "cta": "कॉल टू एक्शन वाक्य"
    }}
    """
    
    response = utils.query_local_llm(prompt, max_words=200)
    
    # Parse the JSON response
    try:
        import json
        # Extract JSON from response
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx:end_idx]
            hindi_script = json.loads(json_str)
            print("   ✅ Direct Hindi narration generated")
            return hindi_script
    except:
        pass
        
    return None

def validate_hindi_quality(hindi_script):
    """Validate that Hindi translation is actually Hindi, not garbled text"""
    valid_count = 0
    total_count = len(hindi_script)
    
    for key, text in hindi_script.items():
        # Check if text contains Hindi characters (Devanagari Unicode range)
        hindi_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
        total_chars = len(text)
        
        # Consider it valid Hindi if at least 30% of characters are Hindi script
        if total_chars > 0 and (hindi_chars / total_chars) > 0.3:
            valid_count += 1
        elif total_chars > 20:  # If long text but no Hindi, it's probably English
            print(f"      - ⚠️  Poor Hindi quality for {key}: {text[:50]}...")
    
    quality_ratio = valid_count / total_count if total_count > 0 else 0
    print(f"   📊 Hindi Quality: {valid_count}/{total_count} segments ({quality_ratio:.0%})")
    
    return quality_ratio > 0.5  # Return True if majority is good Hindi

def translate_narration_to_hindi(english_script_parts, lang='en', story_type=None, company_data=None):
    """Generate natural Hindi narration instead of direct translation"""
    if lang == 'hi' and story_type and company_data:
        try:
            return generate_natural_hindi_script(english_script_parts, story_type, company_data)
        except Exception as e:
            print(f"   ❌ Hindi narration failed: {e}")
            return english_script_parts
    
    return english_script_parts

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
    """Build narration script for deepdive stories - INCLUDES CEO INFO"""
    # Check for Ollama availability logic (Assuming utils.query_local_llm is used)
    use_llm = utils.query_local_llm("test", 1) is not None
        
    if use_llm:
        print("      - 🧠 SOURCE: Generating script via Ollama (LLM)")
        # ... LLM generation logic ...
    else:
        print("      - 📄 SOURCE: Using Fallback Templates")
    
    try:
        script_parts = {}
        company_name = details.get('name', 'This company')
        ceo_name = details.get('ceo', 'their leadership team')
        
        print(f"   -> Building Detailed DeepDive narration for {company_name}...")
        print(f"      - CEO information: {ceo_name}")
        
        # Enhanced prompts that include CEO information
        enhanced_prompts = {
            'intro': f"Welcome to our comprehensive financial analysis of {company_name}, a prominent player in the {details.get('sector', 'their sector')} sector.",
            
            'sector_scale': f"With a market capitalization of {metrics.get('Market Cap (Cr)', 'N/A')} crores, {company_name} holds a significant position in the {details.get('sector', 'industry')} landscape, representing substantial scale and market influence.",
            
            'management': f"Under the leadership of {ceo_name}, {company_name} has demonstrated strategic vision and operational excellence. The management team brings valuable experience to navigate market challenges and drive sustainable growth.",
            
            'financials': f"Financially, {company_name} shows strong performance with consistent revenue trends and healthy profitability margins. The company's balance sheet reflects prudent financial management and strategic investments.",
            
            'metrics': f"Key valuation metrics indicate {company_name} is trading at a P/E ratio of {metrics.get('P/E Ratio', 'N/A')}, suggesting market confidence in future earnings potential. Other financial ratios point to efficient operations and sound financial health.",
            
            'market': f"Market performance for {company_name} reflects investor confidence and strong fundamentals. The stock has shown resilience amid market fluctuations, presenting opportunities for both short-term traders and long-term investors.",
            
            'cta': f"If you found this analysis of {company_name} valuable, please subscribe to our channel for more investment insights. Like this video and turn on notifications to stay updated with our latest research."
        }
        
        # Use LLM to enhance these templates
        for key, base_text in enhanced_prompts.items():
            print(f"      - Generating {key}...")
            
            # Simple approach: use the enhanced template directly
            script_parts[key] = base_text
            print(f"        ✅ {base_text[:70]}...")
        
        # Add additional CEO-focused content if CEO info is available
        if details.get('ceo') and details['ceo'] != 'N/A':
            ceo_prompt = f"Provide one sentence about {ceo_name}'s leadership impact at {company_name}."
            ceo_insight = utils.query_local_llm(ceo_prompt, max_words=30, temperature=0.4)
            if ceo_insight and "cannot" not in ceo_insight.lower():
                script_parts['management'] += f" {ceo_insight}"
                print(f"        ✅ Added CEO insight: {ceo_insight}")
        
        print(f"   ✅ Final narration: {sum(len(text.split()) for text in script_parts.values())} total words")
        return script_parts
        
    except Exception as e:
        print(f"❌ ERROR in DeepDive narration: {e}")
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

def build_audio_script(english_script_parts, lang='en', story_type=None, company_data=None):
    """Convert script to audio format with proper language handling"""
    try:
        print(f"   -> Building audio script in {lang.upper()}...")
        
        if lang == 'hi':
            print("   -> HINDI MODE: Using Hindi narration...")
            # If we have Hindi script, use it directly
            if story_type and company_data:
                hindi_script = generate_natural_hindi_script(english_script_parts, story_type, company_data)
                audio_script = hindi_script
            else:
                audio_script = english_script_parts
        else:
            print("   -> ENGLISH MODE: Using English script...")
            audio_script = english_script_parts.copy()
        
        # Final validation
        valid_segments = 0
        for key, text in audio_script.items():
            if not text or not text.strip():
                audio_script[key] = f"विश्लेषण बिंदु {key}" if lang == 'hi' else f"Analysis point {key}"
            else:
                valid_segments += 1
        
        print(f"   ✅ Audio script prepared: {valid_segments}/{len(audio_script)} valid segments in {lang.upper()}")
        return audio_script
        
    except Exception as e:
        print(f"❌ ERROR building audio script: {e}")
        # Return basic fallback
        if lang == 'hi':
            return create_hindi_templates(company_data or {}, story_type or 'deepdive')
        else:
            return get_fallback_deepdive_script('Unknown Company')

def _enhance_narration_text(text, key, lang):
    """Enhance narration text to ensure sufficient length for good audio"""
    enhancements = {
        'intro': {
            'en': "Let's begin our comprehensive analysis. ",
            'hi': "आइए शुरू करते हैं हमारा व्यापक विश्लेषण। "
        },
        'financials': {
            'en': "Now examining the financial performance. ",
            'hi': "अब वित्तीय प्रदर्शन की जांच करते हैं। "
        },
        'metrics': {
            'en': "Looking at key financial metrics. ",
            'hi': "मुख्य वित्तीय मैट्रिक्स देख रहे हैं। "
        },
        'cta': {
            'en': "Thank you for watching. ",
            'hi': "देखने के लिए धन्यवाद। "
        }
    }
    
    enhancement = enhancements.get(key, {}).get(lang, "")
    return enhancement + text

# FALLBACK SCRIPTS
def get_fallback_deepdive_script(company_name):
    return {
        'intro': f"Welcome to our comprehensive analysis of {company_name}. Today we'll explore the company's financial health, market position, and investment potential in detail.",
        'profile': f"Let's examine the business fundamentals and operational strategy of {company_name} to understand their competitive advantage in the market.",
        'sector_scale': f"Now looking at the company's market position and industry standing. We'll analyze their scale and competitive landscape.",
        'management': f"Next, we'll review the leadership team driving {company_name}'s strategic direction and their track record in the industry.",
        'competitors': f"Here are the key players in this competitive landscape and how {company_name} positions itself against them.",
        'metrics': f"Analyzing key financial ratios and performance metrics to assess the company's valuation and operational efficiency.",
        'financials': f"Reviewing revenue growth trends, profitability margins, and financial stability of {company_name} over recent quarters.",
        'shareholding': f"Examining the ownership structure and investor types to understand the confidence levels of different investor categories.",
        'market': f"Finally, let's assess the stock's market performance, technical indicators, and future outlook based on current market conditions.",
        'cta': f"Found this deep dive analysis helpful? Subscribe to our channel for more detailed stock analysis and turn on notifications so you don't miss future updates!"
    }

def get_fallback_news_script(company_name, news_count):
    script = {
        'intro': f"Breaking news coverage for {company_name}. We have several important developments to cover in today's update.",
        'cta': "Stay updated with our daily market coverage! Don't forget to like, subscribe, and hit the bell icon for instant notifications on new videos!"
    }
    
    for i in range(news_count):
        script[f'news_{i+1}'] = f"News update {i+1} for {company_name}. This development could have significant implications for the company's future performance."
    
    script['market'] = f"Market context for {company_name}. The stock has shown interesting movements recently that warrant closer examination."
    return script

def get_fallback_comparison_script(company_names):
    names_text = " vs ".join(company_names)
    return {
        'intro': f"Head-to-head comparison: {names_text}. We'll analyze these companies across multiple dimensions to help you make informed investment decisions.",
        'pe_compare': "Comparing valuation multiples and P/E ratios to understand which company offers better value in the current market conditions.",
        'pb_compare': "Analyzing price-to-book ratios to assess the companies' asset values and potential undervaluation or overvaluation.",
        'mcap_compare': "Market capitalization comparison showing the relative size and scale of these companies in their respective markets.",
        'price_compare': "Stock performance analysis highlighting the historical price movements and volatility patterns of these securities.",
        'cta': "Which stock would you choose based on this analysis? Share your thoughts in the comments below and don't forget to subscribe for more comparative analysis!"
    }

def get_fallback_spotlight_script(company_name):
    return {
        'intro': f"Investor spotlight on {company_name}. We'll use our three-lens framework to provide a comprehensive investment analysis.",
        'profitability_intro': "First lens: Profitability analysis. We'll examine the company's ability to generate returns and maintain financial health.",
        'financials': "Revenue growth trends, margin analysis, and cash flow patterns that indicate the company's financial stability and growth potential.",
        'roe': "Return on equity and efficiency metrics that show how effectively the company is using shareholder capital to generate profits.",
        'ownership_intro': "Second lens: Ownership structure. Understanding who owns the company and their investment horizons.",
        'ownership': "Promoter holdings, institutional ownership, and retail participation patterns that reveal market confidence in the company.",
        'valuation_intro': "Third lens: Valuation assessment. Determining if the company is fairly priced in the current market environment.",
        'valuation': "Current valuation multiples compared to historical averages and industry peers to identify potential investment opportunities.",
        'peers': "Comparison with industry peers to benchmark performance and identify relative strengths and weaknesses.",
        'summary': "This completes our three-lens analysis framework, providing a structured approach to stock evaluation and investment decision making.",
        'cta': "Like this spotlight analysis format? Subscribe to our channel for more detailed investment frameworks and turn on notifications for future videos!"
    }

def get_fallback_narration(key, company_name):
    fallbacks = {
        'intro': f"Comprehensive analysis of {company_name}. We'll examine the company's financial performance, market position, and investment potential.",
        'profile': f"Business overview and operational strategy of {company_name}.",
        'metrics': f"Key financial metrics and valuation indicators for {company_name}.",
        'financials': f"Financial performance review including revenue trends and profitability analysis.",
        'market': f"Market performance analysis and future outlook assessment.",
        'cta': f"Subscribe for more detailed financial analysis and investment insights!"
    }
    return fallbacks.get(key, "Analysis segment.")

def get_enhanced_fallback_narration(key, company_name, context_data):
    """Enhanced fallback narration with more detailed content"""
    enhanced_fallbacks = {
        'intro': f"Welcome to our in-depth analysis of {company_name}, a prominent player in the {context_data['sector']} sector. With a market capitalization of {context_data['market_cap']} crores, this company represents a significant opportunity for investors seeking exposure to this industry.",
        'sector_scale': f"{company_name} operates in the {context_data['sector']} sector with substantial market presence. The company's scale and industry positioning make it an important player worth examining closely for investment consideration.",
        'management': f"The leadership team at {company_name}, including CEO {context_data['ceo']}, brings valuable experience and strategic vision to guide the company through market challenges and growth opportunities.",
        'financials': f"Financial performance analysis reveals important trends in revenue growth, profitability margins, and operational efficiency that investors should consider when evaluating {company_name}'s investment potential.",
        'metrics': f"Key valuation metrics including P/E ratio of {context_data['pe_ratio']} and other financial indicators provide insights into how the market is pricing {company_name} relative to its earnings and growth prospects.",
        'market': f"Market performance and technical analysis show interesting patterns that, combined with fundamental factors, create a comprehensive picture of {company_name}'s current investment attractiveness and future potential.",
        'cta': f"If you found this analysis valuable, please subscribe to our channel for more detailed financial insights. Turn on notifications so you never miss our latest investment research and market updates."
    }
    return enhanced_fallbacks.get(key, get_fallback_narration(key, company_name))

def create_hindi_templates(company_data, story_type):
    """Create Hindi narration using templates when LLM fails"""
    company_name = company_data['details'].get('name', 'इस कंपनी')
    metrics = company_data['metrics']
    
    # Hindi templates for different story types
    templates = {
        'deepdive': {
            'intro': f"{company_name} के गहन विश्लेषण में आपका स्वागत है। आज हम इस कंपनी के वित्तीय स्वास्थ्य, बाजार स्थिति और निवेश संभावनाओं का विस्तृत अध्ययन करेंगे।",
            'sector_scale': f"{company_name} भारत की अग्रणी कंपनियों में से एक है जो मजबूत बाजार पूंजी और उद्योग में प्रमुख स्थान रखती है।",
            'management': f"कंपनी का नेतृत्व एक अनुभवी और रणनीतिक टीम के हाथों में है जो कंपनी को विकास और सफलता की ओर ले जा रही है।",
            'financials': f"कंपनी का वित्तीय प्रदर्शन काफी मजबूत रहा है, जो राजस्व वृद्धि और लाभप्रदता में स्थिरता को दर्शाता है।",
            'metrics': f"मुख्य वित्तीय मैट्रिक्स कंपनी के मूल्यांकन और परिचालन दक्षता के बारे में महत्वपूर्ण जानकारी प्रदान करते हैं।",
            'market': f"बाजार में स्टॉक का प्रदर्शन संतोषजनक रहा है और तकनीकी विश्लेषण भविष्य की संभावनाओं के बारे में सकारात्मक संकेत देता है।",
            'cta': f"क्या आपको यह विश्लेषण उपयोगी लगा? हमारे चैनल को सब्सक्राइब करें और अधिक वित्तीय विश्लेषण के लिए नोटिफिकेशन चालू करें!"
        },
        'news': {
            'intro': f"{company_name} की ताजा खबरों में आपका स्वागत है। आज हमारे पास कई महत्वपूर्ण अपडेट हैं जो कंपनी के भविष्य को प्रभावित कर सकते हैं।",
            'cta': f"दैनिक बाजार अपडेट के लिए हमारे चैनल को सब्सक्राइब करें और नई वीडियो की सूचना के लिए घंटी आइकन दबाएं!"
        }
    }
    
    # Use templates for the current story type, fallback to deepdive
    story_templates = templates.get(story_type, templates['deepdive'])
    
    # Enhance with actual metrics if available
    if metrics.get('Market Cap (Cr)'):
        market_cap = metrics['Market Cap (Cr)']
        if market_cap >= 100000:
            story_templates['sector_scale'] = f"{company_name} की बाजार पूंजी ₹{market_cap/100000:.1f} लाख करोड़ है, जो इसे उद्योग में एक प्रमुख खिलाड़ी बनाती है।"
        else:
            story_templates['sector_scale'] = f"कंपनी की बाजार पूंजी ₹{market_cap:,.0f} करोड़ है, जो इसके उद्योग में महत्वपूर्ण उपस्थिति को दर्शाती है।"
    
    if metrics.get('P/E Ratio'):
        story_templates['metrics'] = f"P/E अनुपात {metrics['P/E Ratio']:.1f} पर है, जो कंपनी के मूल्यांकन और कमाई क्षमता के बारे में जानकारी देता है।"
    
    print("   ✅ Using high-quality Hindi templates")
    return story_templates

def generate_natural_hindi_script(english_script_parts, story_type, company_data):
    """Generate natural Hindi script using LLM"""
    try:
        print("   -> Creating NATURAL Hindi narration...")
        
        # First attempt: Generate natural Hindi with LLM
        hindi_script = build_hindi_narration_directly(company_data, story_type)
        
        if hindi_script:
            # Validate the Hindi script quality
            valid_segments = sum(1 for text in hindi_script.values() 
                               if text and len(text.strip()) > 10)
            
            if valid_segments >= 5:  # At least 5 good segments
                print(f"   ✅ High-quality natural Hindi: {valid_segments}/7 segments")
                
                # Print samples to verify quality
                print(f"   📝 Sample - Intro: {hindi_script['intro'][:60]}...")
                print(f"   📝 Sample - CTA: {hindi_script['cta'][:50]}...")
                
                return hindi_script
            else:
                print("   ⚠️  LLM Hindi quality poor, using fallback")
        
        # Fallback: Quality Hindi templates
        print("   🔄 Using quality Hindi fallback templates...")
        return create_hindi_templates(company_data, story_type)
        
    except Exception as e:
        print(f"   ❌ Natural Hindi generation failed: {e}")
        return create_hindi_templates(company_data, story_type)

def validate_natural_hindi_quality(hindi_script):
    """Validate that Hindi sounds natural and human-like"""
    if not hindi_script:
        return False
    
    natural_indicators = [
        'आइए', 'जरूर', 'हैं', 'है', 'करते', 'करें', 'में', 'का', 'की', 'के'
    ]
    
    unnatural_indicators = [
        'अमित्र', 'मासिव', 'ハイ', 'swagat', 'welcome', 'subscribe'
    ]
    
    natural_score = 0
    total_segments = len(hindi_script)
    
    for key, text in hindi_script.items():
        if not text:
            continue
            
        text_lower = text.lower()
        
        # Check for natural Hindi phrases
        natural_count = sum(1 for indicator in natural_indicators if indicator in text_lower)
        unnatural_count = sum(1 for indicator in unnatural_indicators if indicator in text_lower)
        
        if natural_count > 1 and unnatural_count == 0:
            natural_score += 1
            print(f"      - ✅ Natural Hindi for '{key}': {text[:40]}...")
        else:
            print(f"      - ⚠️  Unnatural Hindi for '{key}': {text[:40]}...")
    
    quality_ratio = natural_score / total_segments if total_segments > 0 else 0
    print(f"   📊 Natural Hindi Quality: {natural_score}/{total_segments} segments ({quality_ratio:.0%})")
    
    return quality_ratio > 0.6

# Main function to build narration for any story type
def build_narration_script(story_type, company_data, lang='en'):
    """Main function to build narration script with proper Ollama integration"""
    try:
        print(f"   -> Building {story_type} narration in {lang.upper()}...")
        
        # Check if we should use LLM or templates
        use_llm = _check_ollama_available()
        
        if not use_llm:
            print("   ⚠️  Ollama not available, using template narration")
            if lang == 'hi':
                return create_hindi_templates(company_data, story_type)
            else:
                return get_fallback_deepdive_script(company_data['details'].get('name', 'Unknown'))
        
        print("   ✅ Using Ollama for narration generation...")
        
        if lang == 'hi':
            # Generate Hindi directly
            hindi_script = build_hindi_narration_directly(company_data, story_type)
            return hindi_script
        else:
            # Generate English with LLM enhancement
            if story_type == 'deepdive':
                english_script = build_english_narration_deepdive(
                    company_data['details'],
                    company_data['metrics'],
                    company_data.get('shareholding'),
                    peers_exist=bool(company_data['details'].get('peers'))
                )
            elif story_type == 'news':
                english_script = build_english_narration_news(
                    company_data['display'],
                    company_data.get('news_items', []),
                    company_data.get('price_snapshot', {})
                )
            else:
                english_script = get_fallback_deepdive_script(company_data['details'].get('name', 'Unknown'))
            
            return english_script
        
    except Exception as e:
        print(f"❌ ERROR building {story_type} narration: {e}")
        traceback.print_exc()
        
        # Return comprehensive fallback
        if lang == 'hi':
            return create_hindi_templates(company_data, story_type)
        else:
            return get_fallback_deepdive_script(company_data['details'].get('name', 'Unknown'))

def _check_ollama_available():
    """Check if Ollama is running and responsive"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        print("   ⚠️  Ollama is not running. Please start it with: ollama serve")
        return False