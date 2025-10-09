# content_creator.py
import os
import subprocess
import sys
import whisper

from utils import get_script_dir

def build_narration(company, news_items, price_info):
    script_parts = {
        "intro": f"Here is your daily briefing on {company}. ...",
        "market": f"On the market, the stock was last {'gaining' if price_info['d_pct'] >= 0 else 'down'} about {abs(price_info['d_pct']):.1f} percent. ...",
        "cta": "Hit like for more such content on Stocks and comment your wishlisted Stock. Don't forget to share with those who may be interested."
    }
    for i, item in enumerate(news_items):
        script_parts[f"news_{i+1}"] = item['title'] + ". ..."
    return script_parts

def _generate_single_audio(script, output_path):
    """
    Invokes the external tts_worker.py script to generate audio in an isolated process.
    This prevents memory corruption and segmentation faults from the main process.
    """
    python_executable = sys.executable
    worker_script_path = os.path.join(get_script_dir(), 'tts_worker.py')
    
    command = [
        python_executable,
        worker_script_path,
        script,
        output_path
    ]
    
    try:
        # Use a generous timeout for TTS services
        result = subprocess.run(
            command,
            timeout=45,
            check=True,  # This will raise CalledProcessError if the script exits with a non-zero code (failure)
            capture_output=True,
            text=True
        )
        print(f"      - TTS Worker Success: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print("      - TTS Worker script failed.")
        print(f"      - STDOUT: {e.stdout}")
        print(f"      - STDERR: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f"      - TTS Worker script timed out after 45 seconds.")
        return False
    except Exception as e:
        print(f"      - An unexpected error occurred while running the TTS worker: {e}")
        return False


def generate_segmented_voiceover(script_parts):
    print("  -> Generating segmented voiceovers via isolated worker...")
    audio_paths = {}
    for key, script in script_parts.items():
        output_path = os.path.join(get_script_dir(), "outputs", "tmp", f"vo_{key}.mp3")
        if not _generate_single_audio(script, output_path):
            print(f"    - WARNING: Failed to generate audio for '{key}'. Skipping.")
        else:
            audio_paths[key] = output_path
    print("  -> Voiceover generation complete.")
    return audio_paths

def generate_subtitles(audio_path):
    try:
        print("  -> Generating subtitles with Whisper...")
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, verbose=False)
        return [((seg['start'], seg['end']), seg['text']) for seg in result['segments']]
    except Exception as e:
        print(f"  -> Whisper transcription failed: {e}."); return None
