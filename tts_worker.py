import argparse
import os
import sys
import time
from gtts import gTTS

# Import the language config from your main project
import config

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

def try_azure(text, output_path, lang='en'):
    if not AZURE_AVAILABLE: return False
    speech_key = os.getenv("AZURE_SPEECH_KEY"); speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not all([speech_key, speech_region]):
        print("Azure credentials not found.", file=sys.stderr); return False
    
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    
    # MODIFIED: Select the voice based on the chosen language from config.
    voice_name = config.LANGUAGES.get(lang, {}).get("azure_voice", "en-US-JennyNeural")
    print(f"   - Using Azure voice: {voice_name}")
    speech_config.speech_synthesis_voice_name = voice_name

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    max_retries = 3
    time.sleep(1) 
    for attempt in range(max_retries):
        try:
            print(f"   - Azure TTS attempt {attempt + 1}/{max_retries} for '{text[:30]}...'")
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                cancellation_details = result.cancellation_details; error_details = str(cancellation_details.error_details)
                print(f"   - Attempt {attempt + 1} failed: {cancellation_details.reason}", file=sys.stderr)
                if "auth" in error_details.lower(): return False
        except Exception as e:
            print(f"   - Attempt {attempt + 1} failed with exception: {e}", file=sys.stderr)
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2
            print(f"   - Waiting {wait_time}s before retrying...", file=sys.stderr); time.sleep(wait_time)
    return False

def try_gtts(text, output_path, lang='en'):
    try:
        # MODIFIED: Select the language for gTTS from config.
        gtts_lang_code = config.LANGUAGES.get(lang, {}).get("gtts_lang", "en")
        print(f"   - Falling back to gTTS (lang={gtts_lang_code}) for: '{text[:30]}...'")
        gTTS(text=text, lang=gtts_lang_code).save(output_path)
        return True
    except Exception as e:
        print(f"   - gTTS fallback failed: {e}", file=sys.stderr)
        return False

def main():
    # MODIFIED: Add a language argument to the worker.
    parser = argparse.ArgumentParser(description="TTS Worker Script")
    parser.add_argument("text", help="The text to synthesize.")
    parser.add_argument("output_path", help="The path to save the output MP3 file.")
    parser.add_argument("--lang", default='en', help="Language code for TTS (e.g., 'en', 'hi').")
    args = parser.parse_args()
    
    if try_azure(args.text, args.output_path, args.lang):
        sys.exit(0)
    if try_gtts(args.text, args.output_path, args.lang):
        sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()
