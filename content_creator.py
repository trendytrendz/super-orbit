# content_creator.py
import os
import subprocess
import sys
import whisper

from utils import get_script_dir

def build_narration_news(company, news_items, price_info):
    print("  -> Building narration for 'News' video.")
    script_parts = {"intro": f"Here is your daily briefing on {company}. ...", "market": f"On the market, the stock was last {'gaining' if price_info['d_pct'] >= 0 else 'down'} about {abs(price_info['d_pct']):.1f} percent. ...", "cta": "For more daily stock updates, like this video and subscribe. Comment which stock you'd like to see next."}
    for i, item in enumerate(news_items): script_parts[f"news_{i+1}"] = item['title'] + ". ..."
    return script_parts

def build_narration_deepdive(details, metrics, shareholding):
    print("  -> Building narration for 'Deep Dive' video.")
    script_parts = {}
    company = details.get("name", "the company")
    script_parts["intro"] = f"What is the business behind {company}? Let's do a complete deep dive into its business, management, financials, and market position. ..."
    if details.get("summary"): script_parts["profile"] = f"First, what do they do? {details['summary']} ..."
    if details.get("ceo"): script_parts["management"] = f"The company is led by {details['ceo']}. Strong leadership is a key factor in any business's success. ..."
    if details.get("sector"): script_parts["sector"] = f"It operates in the {details['sector']} sector, specifically within the {details['industry']} industry. ..."
    market_cap = metrics.get("Market Cap (Cr)", "an unknown") if metrics else "an unknown"
    script_parts["metrics"] = f"Looking at the numbers, {company} has a market capitalization of {market_cap} crore rupees, which tells us its overall size in the market. ..."
    script_parts["financials"] = f"Examining their financial performance, this chart shows the trend in revenue and net income over the past few years. ..."
    if shareholding and 'Promoter' in shareholding:
        promoter_holding = shareholding.get('Promoter', 0)
        script_parts["shareholding"] = f"As for ownership, promoters hold about {promoter_holding:.1f} percent of the shares. The rest is held by various institutions and the public. ..."
    script_parts["market"] = f"Finally, its one-year price chart shows the stock's journey, giving us context on its recent performance in the market. ..."
    script_parts["cta"] = "If you found this complete breakdown helpful, like this video and subscribe for more deep dives. Comment which company you want to see next."
    return script_parts

def build_narration_comparison(name_a, name_b, metrics_a, metrics_b):
    print("  -> Building narration for 'Comparison' video.")
    script_parts = {}
    pe_a = metrics_a.get("P/E Ratio", "N/A") if metrics_a else "N/A"; pe_b = metrics_b.get("P/E Ratio", "N/A") if metrics_b else "N/A"
    mcap_a = metrics_a.get("Market Cap (Cr)", "N/A") if metrics_a else "N/A"; mcap_b = metrics_b.get("Market Cap (Cr)", "N/A") if metrics_b else "N/A"
    script_parts["intro"] = f"It's the ultimate showdown: {name_a} versus {name_b}. Let's compare these two giants side-by-side based on the data. ..."
    script_parts["pe_compare"] = f"First up, valuation. Looking at the Price to Earnings ratio, {name_a} stands at {pe_a}, while {name_b} is at {pe_b}. This gives us a quick look at how the market values their earnings. ..."
    script_parts["mcap_compare"] = f"Next, let's talk size. {name_a} has a market cap of {mcap_a} crore rupees, compared to {mcap_b} for {name_b}. This chart shows the difference in their scale. ..."
    script_parts["price_compare"] = "But how have the stocks performed in the market? This chart tracks their one-year normalized performance, showing who has given better returns to investors recently. ..."
    script_parts["cta"] = f"Which company do you think is better? Let us know in the comments! Like and subscribe for more stock comparisons."
    return script_parts

def build_narration_spotlight(details, metrics, shareholding, peers_exist):
    print("  -> Building narration for 'Portfolio Spotlight' video.")
    script_parts = {}
    company = details.get("name", "the company")
    pe_ratio_val = metrics.get("P/E Ratio", "not available") if metrics else "not available"; promoter_holding = shareholding.get('Promoter', 0) if shareholding else 0
    roe_val = details.get("returnOnEquity", "unavailable")
    script_parts["intro"] = f"How would a value investor like Warren Buffett analyze {company}? Let's use his framework to look at profitability, management, and valuation. ..."
    script_parts["financials"] = "First, profitability. Buffett looks for companies with consistent and predictable earnings. This financial chart gives us a clue about the company's stability. ..."
    script_parts["roe"] = f"A key metric for profitability is Return on Equity. For {company}, the ROE is {roe_val}. Investors often look for a consistent ROE above 15 percent. ..."
    if shareholding and promoter_holding > 15:
        script_parts["ownership"] = f"Second, management. With promoters holding {promoter_holding:.1f} percent, it shows strong 'skin in the game,' a trait that value investors appreciate. ..."
    script_parts["valuation"] = f"Third, valuation. The current P/E ratio is {pe_ratio_val}. This helps an investor determine if the stock is trading at a reasonable price relative to its earnings. ..."
    if peers_exist:
        script_parts["peers"] = f"But valuation needs context. Here is how {company}'s P/E ratio stacks up against its industry peers. ..."
    script_parts["summary"] = "By analyzing these key areas, investors can build a fundamental thesis about a company before investing. ..."
    script_parts["cta"] = "If you enjoy this style of analysis, like this video and subscribe for more investor case studies."
    return script_parts

def _generate_single_audio(script, output_path):
    python_executable = sys.executable; worker_script_path = os.path.join(get_script_dir(), 'tts_worker.py'); command = [python_executable, worker_script_path, script, output_path]
    try:
        result = subprocess.run(command, timeout=45, check=True, capture_output=True, text=True)
        print(f"      - TTS Worker Success: {result.stdout.strip()}"); return True
    except subprocess.CalledProcessError as e: print(f"      - TTS Worker script failed.\n      - STDERR: {e.stderr}"); return False
    except subprocess.TimeoutExpired: print(f"      - TTS Worker script timed out after 45 seconds."); return False
    except Exception as e: print(f"      - An unexpected error occurred while running the TTS worker: {e}"); return False

def generate_segmented_voiceover(script_parts):
    print("  -> Generating segmented voiceovers via isolated worker..."); audio_paths = {}
    for key, script in script_parts.items():
        if not script: continue
        output_path = os.path.join(get_script_dir(), "outputs", "tmp", f"vo_{key}.mp3")
        if not _generate_single_audio(script, output_path): print(f"    - WARNING: Failed to generate audio for '{key}'. Skipping.")
        else: audio_paths[key] = output_path
    print("  -> Voiceover generation complete."); return audio_paths

def generate_subtitles(audio_path):
    try:
        print("  -> Generating subtitles with Whisper..."); model = whisper.load_model("base")
        result = model.transcribe(audio_path, verbose=False)
        return [((seg['start'], seg['end']), seg['text']) for seg in result['segments']]
    except Exception as e: print(f"  -> Whisper transcription failed: {e}."); return None
