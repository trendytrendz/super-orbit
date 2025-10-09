# tts_worker.py
import argparse
import os
import sys
from gtts import gTTS

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

def try_azure(text, output_path):
    """Attempts to synthesize audio using Azure TTS."""
    if not AZURE_AVAILABLE:
        return False
        
    synthesizer = None
    try:
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        if not all([speech_key, speech_region]):
            print("Azure credentials not found in environment variables.", file=sys.stderr)
            return False

        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"Azure TTS successful for: '{text[:30]}...'")
            return True
        else:
            cancellation_details = result.cancellation_details
            print(f"Azure TTS failed: {cancellation_details.reason}", file=sys.stderr)
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation_details.error_details}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"An exception occurred during Azure TTS generation: {e}", file=sys.stderr)
        return False
    finally:
        if synthesizer:
            del synthesizer

def try_gtts(text, output_path):
    """Attempts to synthesize audio using gTTS as a fallback."""
    try:
        print(f"Falling back to gTTS for: '{text[:30]}...'")
        gTTS(text=text, lang="en", tld="co.in").save(output_path)
        return True
    except Exception as e:
        print(f"gTTS fallback failed: {e}", file=sys.stderr)
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
    
    # If both failed
    sys.exit(1) # Failure

if __name__ == "__main__":
    main()
