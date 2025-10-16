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

def build_narration_deepdive(details, metrics, shareholding, peers_exist):
    print("  -> Building DYNAMIC narration for 'Deep Dive' video.")
    script_parts = {}; company = details.get("name", "the company")
    script_parts["intro"] = f"What is {company}? Let's do a complete deep dive into its business, management, financials, and market position. ..."
    if details.get("summary"): script_parts["profile"] = f"First, what do they do? {details['summary']} ..."
    if details.get("ceo"): script_parts["management"] = f"The company is led by {details['ceo']}. Strong leadership is a key factor in a business's success. ..."
    if peers_exist: script_parts["competitors"] = f"In the competitive landscape, its main rivals include some of the top names in the industry. ..."
    if metrics and metrics.get("Market Cap (Cr)"): script_parts["metrics"] = f"Looking at the numbers, {company} has a market capitalization of {metrics['Market Cap (Cr)']} crore rupees, and these are some other key financial ratios that investors watch. ..."
    script_parts["financials"] = f"Examining their historical performance, this chart shows the trend in revenue and net income over the past few years. ..."
    if shareholding and 'Promoter' in shareholding: script_parts["shareholding"] = f"As for ownership, promoters hold about {shareholding.get('Promoter', 0):.1f} percent of the shares. The rest is held by various institutions and the public. ..."
    script_parts["market"] = f"Finally, its one-year price chart shows the stock's journey, giving us context on its recent performance in the market. ..."
    script_parts["cta"] = "If you found this complete breakdown helpful, like and subscribe for more deep dives. Comment which company you want to see next."
    return script_parts

def build_narration_comparison(name_a, name_b, metrics_a, metrics_b):
    print("  -> Building DYNAMIC narration for 'Comparison' video.")
    script_parts = {}
    script_parts["intro"] = f"It's the ultimate showdown: {name_a} versus {name_b}. Let's compare these two giants side-by-side based on the data. ..."
    if metrics_a and metrics_b and "P/E Ratio" in metrics_a and "P/E Ratio" in metrics_b:
        script_parts["pe_compare"] = f"First up, valuation. Looking at the Price to Earnings ratio, {name_a} stands at {metrics_a['P/E Ratio']}, while {name_b} is at {metrics_b['P/E Ratio']}. ..."
    if metrics_a and metrics_b and "Market Cap (Cr)" in metrics_a and "Market Cap (Cr)" in metrics_b:
        script_parts["mcap_compare"] = f"Next, let's talk size. {name_a} has a market cap of {metrics_a['Market Cap (Cr)']} crore rupees, compared to {metrics_b['Market Cap (Cr)']} for {name_b}. ..."
    script_parts["price_compare"] = "But how have the stocks performed in the market? This chart tracks their one-year normalized performance, showing who has given better returns to investors recently. ..."
    script_parts["cta"] = f"Which company do you think is better? Let us know in the comments! Like and subscribe for more stock comparisons."
    return script_parts

def build_narration_spotlight(details, metrics, shareholding, peers_exist):
    print("  -> Building DYNAMIC narration for 'Portfolio Spotlight' video.")
    script_parts = {}; company = details.get("name", "the company")
    script_parts["intro"] = f"How would a value investor like Warren Buffett analyze {company}? Let's use his framework to look at profitability, management, and valuation. ..."
    script_parts["profitability_intro"] = ". . ."
    script_parts["financials"] = "First, profitability. Investors look for companies with consistent earnings. This financial chart gives us a clue about the company's financial stability. ..."
    if details.get("returnOnEquity"): script_parts["roe"] = f"A key metric for profitability is Return on Equity. For {company}, the ROE is {details['returnOnEquity']}. Investors often look for a consistent ROE above 15 percent. ..."
    if shareholding and shareholding.get('Promoter', 0) > 15:
        script_parts["ownership_intro"] = ". . ."
        script_parts["ownership"] = f"Second, management. With promoters holding {shareholding.get('Promoter', 0):.1f} percent, it shows strong 'skin in the game,' a trait that value investors appreciate. ..."
    if (metrics and "P/E Ratio" in metrics) or peers_exist:
        script_parts["valuation_intro"] = ". . ."
        if metrics and "P/E Ratio" in metrics: script_parts["valuation"] = f"Third, valuation. The current P/E ratio is {metrics['P/E Ratio']}. This helps an investor determine if the stock is trading at a reasonable price relative to its earnings. ..."
        if peers_exist: script_parts["peers"] = f"But valuation needs context. Here is how {company}'s P/E ratio stacks up against its industry peers. ..."
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
