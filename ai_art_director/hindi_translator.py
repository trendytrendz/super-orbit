# hindi_translator.py

"""
Specialist Hindi Narration Engine
v24.1.0

- Implements a highly detailed, persona-driven LLM prompt for generating
  natural, detailed, and professional Hindi narration.
- Provides a robust, template-based fallback for guaranteed results.
"""
import re
import json
import utils

def generate_natural_hindi_narration(english_script_parts: dict, company_data: dict, story_type: str) -> dict | None:
    # (Implementation from our previous discussion)
    print("   -> 🧠 Activating Specialist Hindi Narration Engine...")
    try:
        prompt = _build_enhanced_hindi_prompt(company_data, story_type)
        response = utils.query_local_llm(prompt, max_words=350, temperature=0.4)
        if response:
            return _parse_and_validate_llm_response(response)
    except Exception as e:
        print(f"   - ❌ An error occurred during Hindi generation: {e}")
    return None

def create_quality_hindi_fallback(english_script_parts: dict, company_data: dict) -> dict:
    print("   -> 🛡️  Using High-Quality Hindi Template Fallback.")
    company_name = company_data['details'].get('name', 'इस कंपनी')
    metrics = company_data['metrics']
    templates = {
        'intro': f"आइए आज हम {company_name} का विस्तृत विश्लेषण करते हैं।",
        'sector_scale': f"{company_name} भारत की अग्रणी कंपनियों में से एक है।",
        'management': "कंपनी का नेतृत्व एक अनुभवी टीम के हाथों में है।",
        'financials': "कंपनी का वित्तीय प्रदर्शन काफी मजबूत रहा है।",
        'metrics': "इसके मुख्य वित्तीय मैट्रिक्स उम्मीदों के अनुरूप हैं।",
        'market': "बाजार में स्टॉक का प्रदर्शन संतोषजनक रहा है।",
        'cta': "ऐसे ही विश्लेषण के लिए हमारे चैनल को सब्सक्राइब जरूर करें!"
    }
    if mcap := metrics.get('Market Cap (Cr)'):
        if mcap >= 100000:
            templates['sector_scale'] = f"{company_name} की बाजार पूंजी ₹{mcap/100000:.1f} लाख करोड़ है।"
        else:
            templates['sector_scale'] = f"कंपनी की बाजार पूंजी ₹{mcap:,.0f} करोड़ है।"
    return templates

def _build_enhanced_hindi_prompt(company_data: dict, story_type: str) -> str:
    # (The powerful, detailed prompt from our previous discussion)
    details = company_data.get('details', {})
    metrics = company_data.get('metrics', {})
    context = f"- कंपनी (Company): {details.get('name', 'N/A')}\n- क्षेत्र (Sector): {details.get('sector', 'N/A')}\n- बाजार पूंजी (Market Cap): {metrics.get('Market Cap (Cr)', 'N/A')} करोड़\n- P/E अनुपात (P/E Ratio): {metrics.get('P/E Ratio', 'N/A')}"
    return f"""**YOUR PERSONA:** आप भारत के एक शीर्ष व्यापार समाचार चैनल के वरिष्ठ वित्तीय विश्लेषक हैं। आपका काम जटिल वित्तीय जानकारी को आम दर्शकों के लिए सरल, आकर्षक और स्वाभाविक हिंदी में प्रस्तुत करना है।\n**YOUR TASK:** नीचे दी गई कंपनी की जानकारी का उपयोग करके, एक स्टॉक विश्लेषण वीडियो के लिए 7-भाग वाली वॉइसओवर स्क्रिप्ट लिखें।\n**COMPANY CONTEXT:**\n{context}\n**CRITICAL INSTRUCTIONS:**\n1.  **Be Detailed & Use Data:** आपको दिए गए वित्तीय आंकड़ों का वाक्यों में सटीक रूप से उपयोग करना है।\n2.  **Natural & Conversational Tone:** ऐसी भाषा का प्रयोग करें जो एक टीवी एंकर बोलता है।\n3.  **Engaging Style:** वाक्यों को आकर्षक बनाएं।\n4.  **Output Format:** आपका आउटपुट केवल एक JSON ऑब्जेक्ट होना चाहिए।\n**GOOD vs. BAD EXAMPLES:**\n- **BAD (generic):** "कंपनी का P/E अनुपात अच्छा है।"\n- **GOOD (detailed & natural):** "अगर हम मूल्यांकन की बात करें, तो कंपनी का P/E अनुपात {metrics.get('P/E Ratio', 'N/A')} के स्तर पर चल रहा है।"\nकृपया निम्नलिखित 7 भागों के लिए स्क्रिप्ट बनाएं और इसे JSON प्रारूप में प्रदान करें:\n{{ "intro": "...", "sector_scale": "...", "management": "...", "financials": "...", "metrics": "...", "market": "...", "cta": "..."}}"""

def _parse_and_validate_llm_response(response: str) -> dict | None:
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            hindi_script = json.loads(json_match.group())
            required_keys = ['intro', 'sector_scale', 'management', 'financials', 'metrics', 'market', 'cta']
            if all(key in hindi_script and hindi_script[key] for key in required_keys):
                print("   - ✅ Successfully parsed detailed Hindi script from LLM.")
                return hindi_script
    except Exception as e:
        print(f"   - ❌ Failed to parse Hindi JSON from LLM: {e}")
    return None

def translate_script_to_hindi(english_script_parts):
    """Placeholder function - real implementation would use LLM translation"""
    print("   -> ⚠️  Using placeholder Hindi translation")
    
    # Simple placeholder translations
    hindi_templates = {
        'intro': 'वित्तीय विश्लेषण में आपका स्वागत है।',
        'sector_scale': 'बाजार स्थिति और क्षेत्र विश्लेषण।',
        'management': 'प्रबंधन टीम और नेतृत्व विश्लेषण।',
        'financials': 'वित्तीय प्रदर्शन समीक्षा।',
        'metrics': 'मुख्य वित्तीय मैट्रिक्स विश्लेषण।',
        'market': 'बाजार प्रदर्शन और भविष्य की संभावनाएं।',
        'cta': 'सब्सक्राइब करें और नोटिफिकेशन चालू करें!'
    }
    
    # Return Hindi versions for each key that exists in English script
    hindi_script = {}
    for key in english_script_parts.keys():
        hindi_script[key] = hindi_templates.get(key, 'विश्लेषण बिंदु')
    
    return hindi_script

