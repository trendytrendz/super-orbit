# ai_art_director/tts_worker.py
# v27.6.1 - Fixed Argument Mismatch

import argparse
import os
import sys
import subprocess
from gtts import gTTS

def clean_text_for_cli(text):
    """Sanitize text for command line usage."""
    # Remove characters that break shell commands
    t = text.replace('"', '').replace("'", "").replace('\n', ' ')
    return t.strip()

def try_edge_cli(text, output_path, lang, voice=None, rate=None):
    try:
        # Default safe voice
        if not voice:
            voice = "en-US-AriaNeural" # Safest global default
        
        # Clean rate (Some versions dislike +0%)
        if rate == "+0%": rate = None 
        
        safe_text = clean_text_for_cli(text)
        
        cmd = ["edge-tts", "--text", safe_text, "--write-media", output_path, "--voice", voice]
        if rate: cmd.append(f"--rate={rate}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return True
        
        # If specific voice failed, try generic fallback
        print(f">> DEBUG: Voice '{voice}' failed. Trying fallback 'en-US-AriaNeural'...", file=sys.stderr)
        cmd_fallback = ["edge-tts", "--text", safe_text, "--write-media", output_path, "--voice", "en-US-AriaNeural"]
        result_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=45)
        
        if result_fb.returncode == 0 and os.path.exists(output_path):
            return True

        print(f">> DEBUG: Edge Failed. {result.stderr}", file=sys.stderr)
        return False

    except Exception as e:
        print(f">> DEBUG: Edge Exception: {e}", file=sys.stderr)
        return False

def try_gtts(text, output_path, lang):
    try:
        print("   ⚠️ Falling back to gTTS...", file=sys.stderr)
        tld = 'co.in' if lang == 'en' else 'com'
        tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
        tts.save(output_path)
        return True
    except: return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("output_path")
    parser.add_argument("--lang", default='en')
    
    # New Arguments
    parser.add_argument("--edge_voice", default=None)
    parser.add_argument("--edge_rate", default=None)
    
    # Legacy args ignored (prevent crash)
    parser.add_argument("--azure_voice", default="")
    parser.add_argument("--google_voice", default="")
    parser.add_argument("--gtts_lang", default="en")
    parser.add_argument("--ssml", action="store_true")
    
    args = parser.parse_args()
    
    # Create directory if missing
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)

    # 1. Try Edge (Passing all 5 arguments correctly)
    if try_edge_cli(args.text, args.output_path, args.lang, args.edge_voice, args.edge_rate):
        sys.exit(0)
        
    # 2. Try gTTS
    if try_gtts(args.text, args.output_path, args.lang):
        sys.exit(0)

    # 3. Fail
    sys.exit(1)