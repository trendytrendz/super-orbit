# tts_worker.py
import argparse
import os
import sys
import time
from gtts import gTTS

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

def try_azure(text, output_path):
    """Attempts to synthesize audio using Azure TTS with aggressive retries."""
    if not AZURE_AVAILABLE:
        return False
        
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not all([speech_key, speech_region]):
        print("Azure credentials not found in environment variables.", file=sys.stderr)
        return False

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   - Azure TTS attempt {attempt + 1}/{max_retries} for '{text[:30]}...'")
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(text).get()
            del synthesizer # Explicitly clean up the object

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"   - Azure TTS successful on attempt {attempt + 1}")
                return True
            else:
                cancellation_details = result.cancellation_details
                error_details = str(cancellation_details.error_details)
                print(f"   - Attempt {attempt + 1} failed: {cancellation_details.reason}", file=sys.stderr)
                if "auth" in error_details.lower():
                    print("   - Permanent authentication error detected. Not retrying.", file=sys.stderr)
                    return False # Fail fast on auth errors
        
        except Exception as e:
            print(f"   - Attempt {attempt + 1} failed with exception: {e}", file=sys.stderr)

        # If not the last attempt, wait before retrying
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 2 # Wait 2s, then 4s
            print(f"   - Waiting {wait_time}s before retrying...", file=sys.stderr)
            time.sleep(wait_time)

    print(f"   - All {max_retries} Azure TTS attempts failed.", file=sys.stderr)
    return False

def try_gtts(text, output_path):
    """Attempts to synthesize audio using gTTS as a fallback."""
    try:
        print(f"   - Falling back to gTTS for: '{text[:30]}...'")
        gTTS(text=text, lang="en", tld="co.in").save(output_path)
        return True
    except Exception as e:
        print(f"   - gTTS fallback failed: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="TTS Worker Script")
    parser.add_argument("text", help="The text to synthesize.")
    parser.add_argument("output_path", help="The path to save the output MP3 file.")
    args = parser.parse_args()

    if try_azure(args.text, args.output_path):
        sys.exit(0) # Success
    
    if try_gtts(args.text, args.output_path):
        sys.exit(0) # Success
    
    sys.exit(1) # Failure if both failed

if __name__ == "__main__":
    main()
