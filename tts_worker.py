# tts_worker.py
# v20.2.2 - Fixed file writing issues and better error handling

import argparse
import os
import sys
import time
import re
from pathlib import Path
from gtts import gTTS

import config

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

def ensure_directory_exists(file_path):
    """Ensure the directory for the file exists"""
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"      - Created directory: {directory}")
        return True
    except Exception as e:
        print(f"      - ❌ Could not create directory: {e}")
        return False

def try_azure(text, output_path, lang='en', is_ssml=False):
    if not AZURE_AVAILABLE: 
        print("      - Azure TTS not available (library not installed)")
        return False
        
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    
    if not all([speech_key, speech_region]):
        print("      - Azure credentials not found in environment.", file=sys.stderr)
        return False
    
    # Ensure output directory exists
    if not ensure_directory_exists(output_path):
        return False
    
    try:
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        voice_name = config.LANGUAGES.get(lang, {}).get("azure_voice", "en-US-JennyNeural")
        speech_config.speech_synthesis_voice_name = voice_name
        
        # FIX: Use a temporary file path to avoid permission issues
        temp_output = output_path + ".temp"
        audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_output)
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config, 
                    audio_config=audio_config
                )
                
                if is_ssml:
                    result = synthesizer.speak_ssml_async(text).get()
                else:
                    result = synthesizer.speak_text_async(text).get()

                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # Success - rename temp file to final path
                    try:
                        if os.path.exists(temp_output):
                            if os.path.exists(output_path):
                                os.remove(output_path)  # Remove existing file
                            os.rename(temp_output, output_path)
                            
                        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                        print(f"      - ✅ Azure TTS completed: '{text[:40]}...' ({file_size} bytes)")
                        return True
                    except Exception as file_error:
                        print(f"      - ❌ File rename failed: {file_error}")
                        return False
                        
                else:
                    cancellation_details = result.cancellation_details
                    error_details = str(cancellation_details.error_details)
                    print(f"      - Attempt {attempt + 1} failed: {cancellation_details.reason}", file=sys.stderr)
                    
                    # Clean up temp file if it exists
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                    
                    if "auth" in error_details.lower():
                        return False
                        
            except Exception as e: 
                print(f"      - Attempt {attempt + 1} failed with exception: {e}")
                # Clean up temp file if it exists
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                    
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"      - Waiting {wait_time}s before retrying...", file=sys.stderr)
                time.sleep(wait_time)
                
        return False
        
    except Exception as e:
        print(f"      - ❌ Azure TTS setup failed: {e}")
        return False

def try_gtts(text, output_path, lang='en'):
    try:
        # Ensure output directory exists
        if not ensure_directory_exists(output_path):
            return False
            
        plain_text = re.sub(r'<[^>]+>', '', text)
        gtts_lang_code = config.LANGUAGES.get(lang, {}).get("gtts_lang", "en")
        print(f"      - Falling back to gTTS (lang={gtts_lang_code}) for: '{plain_text[:30]}...'")
        
        # Use a temporary file to avoid partial writes
        temp_output = output_path + ".temp"
        gTTS(text=plain_text, lang=gtts_lang_code).save(temp_output)
        
        # Rename temp file to final path
        if os.path.exists(temp_output):
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_output, output_path)
            
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        print(f"      - ✅ gTTS completed: '{plain_text[:30]}...' ({file_size} bytes)")
        return True
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_output' in locals() and os.path.exists(temp_output):
            os.remove(temp_output)
        print(f"      - ❌ gTTS fallback failed: {e}")
        return False

def create_silent_audio_fallback(output_path, duration=3.0):
    """Create a silent audio file as final fallback"""
    try:
        from moviepy.editor import AudioClip
        import numpy as np
        
        if not ensure_directory_exists(output_path):
            return False
            
        def make_silence(t):
            return np.zeros((2,))  # Stereo silence
            
        silent_audio = AudioClip(make_silence, duration=duration)
        silent_audio.write_audiofile(
            output_path, 
            fps=22050,  # Lower fps for smaller file
            verbose=False, 
            logger=None
        )
        print(f"      - ✅ Created silent fallback audio: {output_path}")
        return True
    except Exception as e:
        print(f"      - ❌ Silent audio fallback failed: {e}")
        # Ultimate fallback - touch the file
        try:
            with open(output_path, 'w') as f:
                f.write('')  # Empty file
            return True
        except:
            return False

def main():
    parser = argparse.ArgumentParser(description="TTS Worker Script")
    parser.add_argument("text", help="The text to synthesize.")
    parser.add_argument("output_path", help="The path to save the output MP3 file.")
    parser.add_argument("--lang", default='en', help="Language code for TTS (e.g., 'en', 'hi').")
    parser.add_argument("--ssml", action="store_true", help="Treat input text as SSML.")
    args = parser.parse_args()
    
    # Validate inputs
    if not args.text or not args.text.strip():
        print("❌ ERROR: Empty text provided to TTS worker")
        sys.exit(1)
    
    if not args.output_path:
        print("❌ ERROR: No output path provided to TTS worker")
        sys.exit(1)
    
    print(f"      - TTS Request: '{args.text[:50]}...' -> {args.output_path}")
    
    # Try Azure TTS first
    if try_azure(args.text, args.output_path, args.lang, args.ssml):
        sys.exit(0)
    
    # Fallback to gTTS
    if try_gtts(args.text, args.output_path, args.lang):
        sys.exit(0)
    
    # Ultimate fallback - create silent audio
    print("      - ❌ All TTS methods failed, creating silent fallback...")
    if create_silent_audio_fallback(args.output_path):
        sys.exit(0)
    else:
        print("      - 💥 ALL TTS METHODS FAILED COMPLETELY")
        sys.exit(1)

if __name__ == "__main__":
    main()
