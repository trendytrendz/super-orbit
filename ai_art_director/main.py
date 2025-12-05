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
    theme['font'] = config.DEFAULT_FONT
    print(f"✅ Using theme: {theme['accent']} with font {os.path.basename(theme['font'])}")

    # 2. Bundle configuration for the story runner
    runner_config = {
        "theme": theme,
        "icon_svg": config.ICONS,
        "lang": args.lang
    }

    # 3. Use the Factory to get the correct runner instance
    try:
        runner = story_runners.get_story_runner(args.type, runner_config)
    except ValueError as e:
        raise VideoGenerationError(e)

    # 4. Determine queries (Fixed Logic)
    queries = []
    if args.type == 'comparison':
        # Prioritize --companies flag, fallback to positional args
        queries = args.companies if args.companies else args.queries
    else:
        queries = args.queries

    # Validation
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
    
    # Positional args (captured as list)
    parser.add_argument("queries", nargs='*', help="Company names (e.g., 'Reliance' or 'HDFC ICICI')")
    
    parser.add_argument("--type", choices=['news', 'deepdive', 'comparison', 'spotlight'], required=True)
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='portrait')
    parser.add_argument("--lang", choices=['en', 'hi'], default='en')
    parser.add_argument("--out", help="Custom output MP4 path.")
    
    # Optional explicit flag for comparison
    parser.add_argument("--companies", nargs='+', help="Explicit companies list for comparison.")
    
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