import os
import subprocess
import sys
import whisper
from concurrent.futures import ProcessPoolExecutor, as_completed
import string

import utils

def translate_text_to_hindi(text):
    """Translates a given English text to Hindi using the local LLM."""
    if not text: return ""
    print(f"      - Translating to Hindi: '{text[:40]}...'")
    prompt = f"Translate the following English text to Hindi. Provide only the Hindi translation, nothing else.\n\nEnglish: {text}\n\nHindi:"
    translation = utils.query_local_llm(prompt, max_words=150)
    return translation or text

def build_audio_script(base_script, lang='en'):
    """Translates the script for audio generation if the language is not English."""
    if lang == 'hi':
        print("  -> Translating script to Hindi for voiceover...")
        translated_parts = {}
        for key, text in base_script.items():
            translated_parts[key] = translate_text_to_hindi(text)
        return translated_parts
    return base_script

def build_english_narration_news(company, news_items, price_info, llm_narrations):
    print("  -> Building English narration for 'News' video.")
    script_parts = {
        "intro": f"Here is your daily briefing on {company}. ...",
        "market": f"On the market, the stock was last {'gaining' if price_info['d_pct'] >= 0 else 'down'} about {abs(price_info['d_pct']):.1f} percent. ...",
        "cta": "For more daily stock updates, like this video and subscribe. Comment which stock you'd like to see next."
    }
    for i, item in enumerate(news_items):
        script_parts[f"news_{i+1}"] = llm_narrations.get(f"news_{i+1}", item['title']) + ". ..."
    return script_parts

def build_english_narration_deepdive(details, metrics, shareholding, peers_exist):
    print("  -> Building English narration for 'Deep Dive' video.")
    script_parts = {}; company = details.get("name", "the company")
    script_parts["intro"] = f"What is {company}? Let's do a complete deep dive into its business, management, financials, and market position. ..."
    if details.get("summary"): script_parts["profile"] = f"First, what do they do? {details['summary']} ..."
    if details.get("ceo"): script_parts["management"] = f"The company is led by {details['ceo']}. Strong leadership is a key factor in a business's success. ..."
    if peers_exist: script_parts["competitors"] = "In the competitive landscape, its main rivals include some of the top names in the industry. ..."
    if metrics: script_parts["metrics"] = "Now for a closer look at the numbers. These are some of the key financial ratios that investors watch. ..."
    script_parts["financials"] = "Examining their historical performance, this chart shows the trend in revenue and net income over the past few years. ..."
    if shareholding and 'Promoter' in shareholding: script_parts["shareholding"] = f"As for ownership, promoters hold about {shareholding.get('Promoter', 0):.1f} percent of the shares. ..."
    script_parts["market"] = "Finally, its one-year price chart shows the stock's journey, giving us context on its recent performance in the market. ..."
    script_parts["cta"] = "If you found this complete breakdown helpful, like and subscribe for more deep dives."
    return script_parts

def build_english_narration_comparison(all_data):
    print("  -> Building English narration for 'Comparison' video.")
    script_parts = {}; names = [d['display'] for d in all_data]
    intro_text = f"{names[0]} versus {names[1]}." if len(names) == 2 else f"A battle between {len(names)} top companies: {', '.join(names[:-1])}, and {names[-1]}."
    script_parts["intro"] = f"{intro_text} Let's compare them side-by-side. ..."
    pe_narrations = [f"{d['display']} at {d['metrics'].get('P/E Ratio'):.2f}" for d in all_data if d['metrics'].get("P/E Ratio") is not None]
    if pe_narrations: script_parts["pe_compare"] = f"First, for Price to Earnings, we have {', '.join(pe_narrations)}. A lower P/E can suggest better value. ..."
    pb_narrations = [f"{d['display']} at {d['metrics'].get('P/B Ratio'):.2f}" for d in all_data if d['metrics'].get("P/B Ratio") is not None]
    if pb_narrations: script_parts["pb_compare"] = f"Next, the Price to Book ratio shows {', '.join(pb_narrations)}. ..."
    mcap_narrations = [f"{d['display']} with a market cap of {d['metrics'].get('Market Cap (Cr)'):,.0f} crore rupees" for d in all_data if d['metrics'].get("Market Cap (Cr)") is not None]
    if mcap_narrations: script_parts["mcap_compare"] = f"In terms of size, it's {', '.join(mcap_narrations)}. ..."
    rev_narrations = [f"{d['display']} with {d['quarterly_financials'].get('Quarterly Revenue (Cr)'):,.0f} crore" for d in all_data if d['quarterly_financials'].get('Quarterly Revenue (Cr)') is not None]
    if rev_narrations: script_parts["q_revenue_compare"] = f"Looking at the latest quarterly revenues, we see {', '.join(rev_narrations)}. ..."
    profit_narrations = [f"{d['display']} reporting a profit of {d['quarterly_financials'].get('Quarterly Profit (Cr)'):,.0f} crore" for d in all_data if d['quarterly_financials'].get('Quarterly Profit (Cr)') is not None]
    if profit_narrations: script_parts["q_profit_compare"] = f"And for profits, the numbers were {', '.join(profit_narrations)}. ..."
    script_parts["perf_compare"] = "This chart shows how much each stock has gained from its 52-week low. ..."
    script_parts["price_compare"] = "Finally, the head-to-head price action over the last year shows who had better momentum. ..."
    script_parts["cta"] = f"Which company do you think is a better pick? Let us know in the comments! Like and subscribe for more."
    return script_parts

def build_english_narration_spotlight(details, metrics, shareholding, peers_exist):
    print("  -> Building English narration for 'Spotlight' video.")
    script_parts = {}; company = details.get("name", "the company")
    script_parts["intro"] = f"How would a value investor analyze {company}? Let's use their framework. ..."
    if details.get("returnOnEquity") is not None: script_parts["roe"] = f"A key metric is Return on Equity. For {company}, the ROE is {details.get('returnOnEquity') * 100:.2f}%. ..."
    if shareholding and 'Promoter' in shareholding: script_parts["ownership"] = f"With promoters holding {shareholding.get('Promoter', 0):.1f} percent, it shows strong 'skin in the game'. ..."
    if "P/E Ratio" in metrics: script_parts["valuation"] = f"The current P/E ratio is {metrics.get('P/E Ratio'):.2f}, helping determine if the stock is reasonably priced. ..."
    if peers_exist: script_parts["peers"] = f"But valuation needs context. Here is how {company}'s P/E ratio stacks up against its peers. ..."
    script_parts["cta"] = "If you enjoyed this analysis, like and subscribe for more."
    return script_parts

def generate_subtitles(audio_path):
    """Generates English subtitles by transcribing the audio."""
    try:
        print(f"  -> Generating English subtitles with Whisper...")
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, verbose=False, language='en')
        segments = result.get('segments', [])
        good_segments = [((seg['start'], seg['end']), text) for seg in segments if (text := seg['text'].strip()) and not all(char in string.punctuation for char in text)]
        print(f"  -> Found {len(good_segments)} valid subtitle segments.")
        return good_segments
    except Exception as e:
        print(f"  -> Whisper transcription failed: {e}."); return None

def _generate_single_audio(script, output_path, lang='en'):
    python_executable, worker_script_path = sys.executable, os.path.join(utils.get_script_dir(), 'tts_worker.py')
    command = [python_executable, worker_script_path, script, output_path, "--lang", lang]
    try:
        subprocess.run(command, timeout=45, check=True, capture_output=True, text=True)
        return True, output_path
    except Exception as e:
        print(f"      - TTS Worker script failed for '{script[:20]}...'. Error: {e}", file=sys.stderr)
        return False, None

def generate_segmented_voiceover(script_parts, lang='en'):
    print(f"  -> Generating segmented voiceovers in parallel (Language: {lang})...")
    _generate_single_audio("Initializing.", os.path.join(utils.get_script_dir(), "outputs", "tmp", "vo_warmup.mp3"), lang)
    audio_paths = {}
    tasks = {key: script for key, script in script_parts.items() if script}
    with ProcessPoolExecutor() as executor:
        future_to_key = {executor.submit(_generate_single_audio, script, os.path.join(utils.get_script_dir(), "outputs", "tmp", f"vo_{key}.mp3"), lang): key for key, script in tasks.items()}
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                success, path = future.result()
                if success: audio_paths[key] = path
                else: print(f"    - WARNING: Failed to generate audio for '{key}'. Skipping.")
            except Exception as exc: print(f"    - ERROR: Audio generation for '{key}' raised an exception: {exc}")
    print(f"  -> Voiceover generation complete. {len(audio_paths)}/{len(tasks)} successful.")
    return audio_paths
