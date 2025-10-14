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

def build_narration_deepdive(company, metrics, shareholding):
    print("  -> Building narration for 'Deep Dive' video.")
    script_parts = {}
    script_parts["intro"] = f"What is the business behind {company}? Let's take a deep dive into its fundamentals in under 2 minutes. ..."
    market_cap = metrics.get("Market Cap (Cr)", "an unknown") if metrics else "an unknown"; pe_ratio = metrics.get("P/E Ratio", "unavailable") if metrics else "unavailable"
    script_parts["metrics"] = f"To understand its scale, {company} has a market capitalization of {market_cap} crore rupees. Its Price to Earnings ratio is currently {pe_ratio}, giving us a hint about its market valuation. ..."
    script_parts["financials"] = f"A look at their financial performance shows a trend in revenue and net income over the past few years. This chart illustrates their recent financial health. ..."
    if shareholding and 'Promoter' in shareholding:
        promoter_holding = shareholding.get('Promoter', 0)
        script_parts["shareholding"] = f"So, who owns the company? Promoters hold about {promoter_holding:.1f} percent of the shares. The rest is held by institutions and the public. ..."
    script_parts["market"] = f"Finally, looking at the one-year price chart, we can see the stock's journey, providing context on its recent performance against the broader market. ..."
    script_parts["cta"] = "If you found this breakdown helpful, like this video and comment which company you want us to analyze next. Subscribe for more deep dives."
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

def build_narration_spotlight(company, metrics, shareholding):
    print("  -> Building narration for 'Portfolio Spotlight' video.")
    script_parts = {}
    pe_ratio_val = metrics.get("P/E Ratio", "not available") if metrics else "not available"; promoter_holding = shareholding.get('Promoter', 0) if shareholding else 0
    script_parts["intro"] = f"How would a famous investor analyze {company}? Let's look at it through the lens of value investing principles, focusing on profitability, valuation, and ownership. ..."
    script_parts["financials"] = "First, profitability. Great investors often look for companies with consistent and growing earnings. This chart of revenue and net income gives us a clue about the company's financial stability over time. ..."
    script_parts["valuation"] = f"Next, let's talk valuation. The current Price to Earnings ratio is {pe_ratio_val}. Value investors use this metric to gauge if a stock might be over or undervalued compared to its peers and its own history. ..."
    if shareholding and promoter_holding > 10:
        script_parts["ownership"] = f"Finally, ownership. With promoters holding {promoter_holding:.1f} percent, it shows they have significant 'skin in the game,' which can align their interests with those of shareholders. ..."
    script_parts["summary"] = "By examining profitability, valuation, and ownership, we can build a more complete picture of a company, much like a seasoned investor would before making a decision. ..."
    script_parts["cta"] = "Enjoyed this analysis? Like and subscribe for more investing case studies. Comment below with a stock you're curious about."
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
