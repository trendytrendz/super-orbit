# main.py
# v20.2.0 - Enhanced error handling and validation

import argparse
import os
import random
import traceback
import re
import multiprocessing
import logging
import sys

import config
import utils
import story_runners

class VideoGenerationError(Exception):
    """Custom exception for video generation failures"""
    pass

def validate_environment():
    """Validate environment before starting"""
    print(f"\n🎬 AI Art Director v{config.__version__}")
    print("=" * 60)
    
    # Check configuration
    if not config.validate_configuration():
        print("\n❌ Configuration validation failed. Please fix the errors above.")
        return False
    
    # Check Azure TTS credentials
    if not os.getenv("AZURE_SPEECH_KEY") or not os.getenv("AZURE_SPEECH_REGION"):
        print("\n⚠️  WARNING: Azure TTS credentials not found.")
        print("   Voiceover will use lower-quality gTTS fallback.")
        print("   Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION for best quality.")
    
    return True

def setup_directories():
    """Ensure all required directories exist"""
    try:
        utils.ensure_dirs()
        print("✅ Directories validated")
        return True
    except Exception as e:
        print(f"❌ Directory setup failed: {e}")
        return False

def select_theme():
    """Select and validate theme"""
    try:
        theme = random.choice(config.BASE_THEMES)
        
        # Ensure font is available
        if config.FONT_PATHS:
            theme['font'] = random.choice(config.FONT_PATHS)
            print(f"✅ Using font: {os.path.basename(theme['font'])}")
        else:
            raise VideoGenerationError("No fonts available. Please install system fonts.")
        
        print(f"✅ Using theme: {theme['accent']}")
        return theme
        
    except Exception as e:
        raise VideoGenerationError(f"Theme selection failed: {e}")

def colorize_svg(svg_string, color):
    """Colorize SVG icons with error handling"""
    try:
        return svg_string.replace('<path ', f'<path fill="{color}" ', 1)
    except Exception as e:
        print(f"⚠️  SVG colorization failed: {e}")
        return svg_string

def prepare_icons(theme):
    """Prepare SVG icons with theme colors"""
    try:
        icon_svg = {}
        for name, svg in config.ICONS.items():
            if name in ["like", "bell", "subscribe", "poll", "positive", "share"]:
                icon_svg[name] = colorize_svg(svg, theme["accent"])
            elif name == "negative":
                icon_svg[name] = colorize_svg(svg, "#F44336")
            elif name in ["neutral", "uncertain"]:
                icon_svg[name] = colorize_svg(svg, "#9E9E9E")
            else:
                icon_svg[name] = colorize_svg(svg, "#FFFFFF")
        
        print("✅ Icons prepared")
        return icon_svg
        
    except Exception as e:
        raise VideoGenerationError(f"Icon preparation failed: {e}")

def determine_output_path(queries, story_type, video_format, custom_out=None):
    """Determine output path with validation"""
    try:
        if custom_out:
            output_dir = os.path.dirname(custom_out)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            return custom_out
        
        # Generate default path
        script_dir = utils.get_script_dir()
        base_name = "_vs_".join(q.replace(' ', '_') for q in queries) if story_type == 'comparison' else queries[0].replace(' ', '_')
        output_file = f"{base_name}_{story_type}_{video_format}.mp4"
        output_path = os.path.join(script_dir, "outputs", output_file)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        return output_path
        
    except Exception as e:
        raise VideoGenerationError(f"Output path determination failed: {e}")

def validate_queries(queries, story_type):
    """Validate query parameters"""
    if not queries:
        raise VideoGenerationError("No companies specified")
    
    if story_type == 'comparison':
        if not (2 <= len(queries) <= 4):
            raise VideoGenerationError("Comparison requires 2-4 companies")
    else:
        if len(queries) != 1:
            raise VideoGenerationError(f"{story_type} requires exactly one company")

def run_story_pipeline(story_type, queries, video_format, out_path, theme, icon_svg, lang):
    """Run the appropriate story pipeline with error handling"""
    story_map = {
        'news': story_runners.run_story_news,
        'deepdive': story_runners.run_story_deepdive,
        'comparison': story_runners.run_story_comparison,
        'spotlight': story_runners.run_story_spotlight
    }
    
    if story_type not in story_map:
        raise VideoGenerationError(f"Unknown story type: {story_type}")
    
    print(f"\n🚀 Starting {story_type} story for: {', '.join(queries)}")
    print(f"   Format: {video_format}, Language: {lang}")
    
    try:
        if story_type == 'comparison':
            story_map[story_type](queries, video_format, out_path, theme, icon_svg, lang=lang)
        else:
            story_map[story_type](queries[0], video_format, out_path, theme, icon_svg, lang=lang)
        
        return True
        
    except Exception as e:
        raise VideoGenerationError(f"Story pipeline failed: {e}")

def verify_output_video(out_path):
    """Verify the generated video file"""
    try:
        if out_path and os.path.exists(out_path):
            file_size = os.path.getsize(out_path) / (1024 * 1024)  # MB
            if file_size > 0.1:  # Reasonable minimum size
                print(f"\n🎉 SUCCESS: Video created at '{out_path}'")
                print(f"   Size: {file_size:.2f} MB")
                return True
            else:
                print(f"\n⚠️  WARNING: Video file seems too small ({file_size:.2f} MB)")
                return False
        else:
            print(f"\n❌ FAILURE: Output file not found at '{out_path}'")
            return False
            
    except Exception as e:
        print(f"\n⚠️  Could not verify output: {e}")
        return False

def main_app():
    """Main application with comprehensive error handling"""
    parser = argparse.ArgumentParser(description=f"AI Art Director - Stock Video Engine v{config.__version__}")
    parser.add_argument("queries", nargs='+', help="One to four company names/tickers.")
    parser.add_argument("--type", choices=['news', 'deepdive', 'comparison', 'spotlight'], required=True, help="The type of video to generate.")
    parser.add_argument("--format", choices=['landscape', 'portrait'], default='portrait', help="Video format.")
    parser.add_argument("--lang", choices=config.LANGUAGES.keys(), default='en', help="Language for the voiceover.")
    parser.add_argument("--out", help="Output MP4 path")
    
    args = parser.parse_args()
    
    try:
        # Phase 1: Environment validation
        if not validate_environment():
            sys.exit(1)
        
        if not setup_directories():
            sys.exit(1)
        
        # Phase 2: Theme and asset preparation
        theme = select_theme()
        icon_svg = prepare_icons(theme)
        
        # Phase 3: Parameter validation
        validate_queries(args.queries, args.type)
        out_path = determine_output_path(args.queries, args.type, args.format, args.out)
        
        # Phase 4: Run story pipeline
        success = run_story_pipeline(args.type, args.queries, args.format, out_path, theme, icon_svg, args.lang)
        
        # Phase 5: Verify output
        if success:
            verify_output_video(out_path)
        
        print(f"\n✅ AI Art Director completed successfully!")
        
    except VideoGenerationError as e:
        print(f"\n❌ Video generation failed: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('peewee').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Configure multiprocessing
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass
    
    main_app()
