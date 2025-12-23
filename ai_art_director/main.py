# main.py
# v27.1

import argparse
import os
import random
import sys
import traceback

from . import config
from . import utils
from . import story_runners
from . import initializer
# custom_json_runner is imported via story_runners factory, no direct import needed here

class VideoGenerationError(Exception):
    pass

def run_pipeline(args):
    """Main video generation pipeline."""
    # 1. Setup & CLEANUP
      # 0. RUN SYSTEM CHECKS (Auto-creates folders, fonts, assets)
    initializer.run_checks()
    
    utils.setup_project_directories()
    utils.cleanup_temp_images()
    
    theme = random.choice(config.BASE_THEMES)

    # --- STRICT FONT SWITCHING ---
    if args.lang == 'hi':
        theme['font'] = config.HINDI_FONT
        theme['lang'] = 'hi'
        print(f"✅ Language is Hindi: Using font {os.path.basename(config.HINDI_FONT)}")
    else:
        # Ensure we use the English font for 'en'
        theme['font'] = config.DEFAULT_FONT
        theme['lang'] = 'en'
        print(f"✅ Language is English: Using font {os.path.basename(config.DEFAULT_FONT)}")

    # Safety Check
    if not os.path.exists(theme['font']) and not theme['font'].startswith("Arial"):
        print(f"⚠️  Warning: Font file {theme['font']} not found. Falling back to default.")
        if args.lang == 'en':
             theme['font'] = config.DEFAULT_FONT

    # 2. Bundle configuration for the story runner
    runner_config = {
        "theme": theme,
        "icon_svg": config.ICONS,
        "lang": args.lang,
        "input_file": args.input # Pass input file path to runner config
    }

    # 3. Use the Factory to get the correct runner instance
    try:
        runner = story_runners.get_story_runner(args.type, runner_config)
    except ValueError as e:
        raise VideoGenerationError(e)

    # 4. Determine Input Data (Queries)
    queries = []

    # CASE 1: Custom JSON (TV Broadcast)
    if args.type == "custom_json":
        if not args.input:
            raise VideoGenerationError("--input [path_to_json] is required for custom_json type.")
        # We pass the filename as the "query"
        queries = [args.input]

    # CASE 2: Custom News (Legacy File Driven)
    elif args.type == 'custom_news':
        if not args.input:
            raise VideoGenerationError("Story type 'custom_news' requires --input argument pointing to a JSON file.")
        input_filename = os.path.splitext(os.path.basename(args.input))[0]
        queries = [input_filename] 

    # CASE 3: Comparison (Multi-Stock)
    elif args.type == 'comparison':
        # Prioritize --companies flag, fallback to positional args
        queries = args.companies if args.companies else args.queries
        
    # CASE 4: Standard Stories (Single Ticker)
    else:
        queries = args.queries

    # Validation (Global)
    if not queries:
        raise VideoGenerationError(f"No company names or input files provided. Please check your arguments.")

    # 5. Output Path
    base_name = "_vs_".join(q.replace(' ', '_').replace('/', '_') for q in queries)
    out_path = args.out or os.path.join(config.OUTPUT_DIR, f"{base_name}_{args.type}_{args.format}.mp4")

    # 6. Execute the story runner's `run` method
    print(f"\n🚀 Starting '{args.type}' story...")
    
    # Standardize the call. All runners must implement run(queries, format, out_path)
    success = runner.run(queries, args.format, out_path)

    # 7. Verify Output
    # Note: custom_json might save to a different specific path, so we check general success
    if success:
        print(f"\n🎉 SUCCESS: Pipeline finished.")
    else:
        raise VideoGenerationError("The story runner failed to produce a video file.")

def main():
    parser = argparse.ArgumentParser(description=f"AI Art Director v{config.__version__}")
    
    parser.add_argument("queries", nargs='*', help="Company names")
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='portrait')
    parser.add_argument("--lang", choices=['en', 'hi'], default='en')
    parser.add_argument("--out", help="Custom output MP4 path.")
    parser.add_argument("--companies", nargs='+', help="Explicit companies list.")
    
    parser.add_argument("--type", help="Story type", required=True,
        choices=["news", "deepdive", "comparison", "spotlight", "custom_news", "news_roundup", "stock360", "custom_json"]
    ) 
    
    parser.add_argument("--input", help="Path to JSON file for Custom News/JSON")
    
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