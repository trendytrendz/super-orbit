# main.py
# v24.3.3 - Fixed Argument Parsing Logic

import argparse
import os
import random
import sys
import traceback

from . import config
from . import utils
from . import story_runners

class VideoGenerationError(Exception):
    pass

def run_pipeline(args):
    """Main video generation pipeline."""
    # 1. Setup & CLEANUP
    utils.setup_project_directories()
    utils.cleanup_temp_images()
    
    theme = random.choice(config.BASE_THEMES)

    # --- STRICT FONT SWITCHING ---
    if args.lang == 'hi':
        theme['font'] = config.HINDI_FONT
        theme['lang'] = 'hi'
        print(f"✅ Language is Hindi: Using font {os.path.basename(config.HINDI_FONT)}")
    else:
        # FIX: Ensure we use the English font for 'en'
        theme['font'] = config.DEFAULT_FONT
        theme['lang'] = 'en'
        print(f"✅ Language is English: Using font {os.path.basename(config.DEFAULT_FONT)}")

    # Safety Check
    if not os.path.exists(theme['font']) and not theme['font'].startswith("Arial"):
        print(f"⚠️  Warning: Font file {theme['font']} not found. Falling back to default.")
        
        # If English font missing, try to find ANY ttf
        if args.lang == 'en':
             theme['font'] = config.DEFAULT_FONT

    # 2. Bundle configuration for the story runner
    runner_config = {
        "theme": theme,
        "icon_svg": config.ICONS,
        "lang": args.lang,
        "input_file": args.input # <--- Pass the input file path here
    }

    # 3. Use the Factory to get the correct runner instance
    try:
        runner = story_runners.get_story_runner(args.type, runner_config)
    except ValueError as e:
        raise VideoGenerationError(e)

    # 4. Determine queries (Fixed Logic)
    queries = []
     # CASE A: Custom News (File Driven)
    if args.type == 'custom_news':
        if not args.input:
            raise VideoGenerationError("Story type 'custom_news' requires --input argument pointing to a JSON file.")
        
        # Inject a placeholder query so downstream validation and filename generation don't crash
        # The CustomNewsStory runner ignores this list anyway.
        input_filename = os.path.splitext(os.path.basename(args.input))[0]
        queries = [input_filename] 

    # CASE B: Comparison (Multi-Stock)
    elif args.type == 'comparison':
        # Prioritize --companies flag, fallback to positional args
        queries = args.companies if args.companies else args.queries
        
    # CASE C: Standard Stories (Single Ticker)
    else:
        queries = args.queries

    # Validation (Global)
    if not queries:
        raise VideoGenerationError(f"No company names provided. Please add company names after the command (e.g. 'Reliance')")
    # 5. Output Path
    base_name = "_vs_".join(q.replace(' ', '_') for q in queries)
    out_path = args.out or os.path.join(config.OUTPUT_DIR, f"{base_name}_{args.type}_{args.format}.mp4")

    # 6. Execute the story runner's `run` method
    print(f"\n🚀 Starting '{args.type}' story for: {queries}")
    
    # Pass 'queries' directly (ComparisonStory expects a list, DeepDive/Spotlight expect list but take [0])
    success = runner.run(queries, args.format, out_path)

    # 7. Verify Output
    if success and os.path.exists(out_path):
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"\n🎉 SUCCESS: Video created at '{out_path}' ({size_mb:.2f} MB)")
    else:
        raise VideoGenerationError("The story runner failed to produce a video file.")

def main():
    parser = argparse.ArgumentParser(description=f"AI Art Director v{config.__version__}")
    
    # Existing args...
    parser.add_argument("queries", nargs='*', help="Company names")
    parser.add_argument("--type", choices=['news', 'deepdive', 'comparison', 'spotlight', 'custom_news', 'news_roundup'], required=True) # Added types
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='portrait')
    parser.add_argument("--lang", choices=['en', 'hi'], default='en')
    parser.add_argument("--out", help="Custom output MP4 path.")
    parser.add_argument("--companies", nargs='+', help="Explicit companies list.")
    
    # NEW ARGUMENT
    parser.add_argument("--input", help="Path to JSON file for Custom News")
    
    args = parser.parse_args()

    try:
        run_pipeline(args)
    except (VideoGenerationError, ValueError) as e:
        print(f"\n❌ A critical error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 An unexpected error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()