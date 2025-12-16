# ai_art_director/tts_worker.py
# v24.3.2 - Accepts Google Voice Arg

import argparse
import os
import sys
import re
from gtts import gTTS
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# --- 1. Azure Import ---
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

# --- 2. Google Import ---
try:
    from google.cloud import texttospeech
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

def clean_ssml_for_google(text):
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

# --- ENGINE 1: AZURE ---
def try_azure(text, output_path, lang, voice_name):
    if not AZURE_AVAILABLE: return False
    key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if not key or not region: return False

    print(f">> DEBUG: Trying Azure ({voice_name})...")
    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_voice_name = voice_name
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
        )
        
        ssml = text if text.strip().startswith("<speak") else f"<speak version='1.0' xml:lang='{lang}'><voice name='{voice_name}'>{text}</voice></speak>"
        
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f">> DEBUG: Azure Success! ({os.path.getsize(output_path)} bytes)")
            return True
        else:
            print(f">> DEBUG: Azure Failed: {result.cancellation_details.error_details}", file=sys.stderr)
    except Exception as e:
        print(f">> DEBUG: Azure Error: {e}", file=sys.stderr)
    return False

# --- ENGINE 2: GOOGLE CLOUD ---
def try_google(text, output_path, lang, voice_name):
    if not GOOGLE_AVAILABLE: return False
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"): return False

    #print(f">> DEBUG: Trying Google Cloud ({voice_name})...")
    try:
        client = texttospeech.TextToSpeechClient()
        clean_text = clean_ssml_for_google(text)
        synthesis_input = texttospeech.SynthesisInput(text=clean_text)
        
        # USE THE VOICE NAME PASSED FROM ARGUMENTS
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US" if lang == 'en' else "hi-IN",
            name=voice_name
        )

        # Journey voices do NOT support pitch/volume
        is_journey = "Journey" in voice_name
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.15
        )
        
        if not is_journey:
            audio_config.pitch = 2.0

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        with open(output_path, "wb") as out:
            out.write(response.audio_content)
            
        print(f">> DEBUG: Google Success! ({os.path.getsize(output_path)} bytes)")
        return True
    except Exception as e:
        print(f">> DEBUG: Google Error: {e}", file=sys.stderr)
    return False

def speed_up_mp3(input_path, speed=1.25):
    """Speed up audio using pydub (reliable) or ffmpeg (fallback)"""
    
    # METHOD 1: Pydub (Preferred)
    if PYDUB_AVAILABLE:
        try:
            sound = AudioSegment.from_mp3(input_path)
            
            # Pydub doesn't have direct 'speed' change without pitch shift
            # But we can cheat by changing frame rate
            new_sample_rate = int(sound.frame_rate * speed)
            faster_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
            faster_sound = faster_sound.set_frame_rate(44100) # Reset to standard
            
            faster_sound.export(input_path, format="mp3")
            print(f">> DEBUG: Speed up ({speed}x) applied via Pydub.")
            return True
        except Exception as e:
            print(f">> DEBUG: Pydub failed: {e}")

    # METHOD 2: FFmpeg (Fallback)
    # Ensure command is split correctly
    try:
        temp_path = input_path.replace(".mp3", "_fast.mp3")
        cmd = [
            "ffmpeg", "-y", 
            "-i", input_path, 
            "-filter:a", f"atempo={speed}", 
            "-vn", 
            temp_path
        ]
        
        # Capture output to see why it fails
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            os.replace(temp_path, input_path)
            print(f">> DEBUG: Speed up ({speed}x) applied via FFmpeg.")
            return True
        else:
            print(f">> DEBUG: FFmpeg failed. Code: {result.returncode}")
            print(f"   Stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f">> DEBUG: FFmpeg subprocess error: {e}")
        return False

# --- ENGINE 3: gTTS ---
# --- UPDATE try_gtts ---
def try_gtts(text, output_path, lang):
    print(">> DEBUG: Falling back to gTTS...")
    try:
        clean_text = clean_ssml_for_google(text)
        
        # 1. Generate Standard Speed
        tld = 'co.in' if lang == 'en' else 'com'
        
        tts = gTTS(text=clean_text, lang=lang, tld=tld, slow=False)
        tts.save(output_path)
        
        # 2. Apply Speed Hack (1.25x is good for News)
        speed_up_mp3(output_path, speed=1.50)
        
        print(f">> DEBUG: gTTS Success!")
        return True
    except Exception as e: 
        print(f">> DEBUG: gTTS Failed: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("text"); parser.add_argument("output_path")
    parser.add_argument("--lang", default='en')
    parser.add_argument("--azure_voice", default="en-US-AriaNeural")
    parser.add_argument("--google_voice", default="en-US-Journey-D") # Default if missing
    parser.add_argument("--gtts_lang", default="en")
    parser.add_argument("--ssml", action="store_true")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    
    is_dev_mode = os.getenv("DEV_MODE", "True").lower() == "true"
    
    '''if is_dev_mode:
        # Google First
        if try_google(args.text, args.output_path, args.lang, args.google_voice): sys.exit(0)
        if try_azure(args.text, args.output_path, args.lang, args.azure_voice): sys.exit(0)
    else:
        # Azure First
        if try_azure(args.text, args.output_path, args.lang, args.azure_voice): sys.exit(0)
        if try_google(args.text, args.output_path, args.lang, args.google_voice): sys.exit(0)'''
    print(f">> DEBUG: gTTS final call ***************** ")   
    if try_gtts(args.text, args.output_path, args.gtts_lang): sys.exit(0)
    sys.exit(1)