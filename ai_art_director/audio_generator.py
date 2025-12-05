# ai_art_director/audio_generator.py
# v24.2.29 - Config-Aware Absolute Paths

import os
import time
import traceback
import subprocess
import sys
import shutil
from typing import Dict, List, Optional
from pathlib import Path

from . import utils
from . import config # <--- CRITICAL IMPORT

# Import Hindi translator
try:
    from .hindi_translator import translate_script_to_hindi
except ImportError:
    print("⚠️  hindi_translator.py not available - Hindi support limited")
    def translate_script_to_hindi(english_script_parts):
        return english_script_parts

class AudioGenerator:
    """Enhanced audio generator with robust error handling and natural speech"""
    
    def __init__(self):
        self.audio_cache = {}
        self.setup_audio_directories()
    
    def setup_audio_directories(self):
        """Ensure audio directories exist using CONFIG ABSOLUTE PATHS"""
        # Use the absolute paths from config.py
        self.dirs = {
            "voiceovers": str(config.AUDIO_VOICEOVERS_DIR),
            "cache": str(config.AUDIO_CACHE_DIR),
            "fallbacks": str(config.AUDIO_FALLBACKS_DIR)
        }
        
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
    
    def generate_single_voiceover(self, text: str, output_path: str, lang: str = 'en') -> bool:
        """Generate single voiceover with enhanced path handling"""
        try:
            # Validate input
            if not text or not text.strip():
                print(f"      - ⚠️  Empty text for voiceover: {os.path.basename(output_path)}")
                return self.create_proper_silent_audio(output_path, duration=3.0)
            
            # FIX: Use Absolute Path for Worker
            script_dir = str(config.SRC_DIR)
            tts_worker_path = os.path.join(script_dir, "tts_worker.py")
            
            if not os.path.exists(tts_worker_path):
                print(f"❌ TTS worker not found at: {tts_worker_path}")
                return self.create_proper_silent_audio(output_path, duration=4.0)
            
            # Use consistent voice configuration from voice_config
            try:
                from . import voice_config
                vc = voice_config.get_voice_for_lang(lang)
                azure_voice = vc.get("azure_voice")
                gtts_lang = vc.get("gtts_lang")
            except ImportError:
                print(f"      - ⚠️  voice_config not available, using fallback for {lang}")
                if lang == 'hi':
                    azure_voice = "hi-IN-SwaraNeural"
                    gtts_lang = "hi"
                else:
                    azure_voice = "en-US-AriaNeural"
                    gtts_lang = "en"
            
            # 3. Config - Read from config.py
            azure_voice = "en-US-AriaNeural"
            google_voice = "en-US-Journey-D" # Default
            gtts_lang = "en"
            
            if config.VOICE_CONFIG:
                vc = config.get_voice_for_lang(lang)
                azure_voice = vc.get("azure_voice", azure_voice)
                google_voice = vc.get("google_voice", google_voice) # <--- Get Google Voice
                gtts_lang = vc.get("gtts_lang", gtts_lang)
            
            # 4. Run Command - PASS GOOGLE VOICE
            cmd = [
                sys.executable,
                tts_worker_path,
                text,
                output_path,
                "--lang", lang,
                "--azure_voice", azure_voice,
                "--google_voice", google_voice, # <--- PASS IT HERE
                "--gtts_lang", gtts_lang,
                "--ssml"
            ]
            
            # Run TTS worker - NO CWD ARGUMENT
            # This ensures it runs in the root context and respects the absolute output path
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    print(result.stdout)
                    print("--- WORKER STDERR ---")
                    print(result.stderr)
                    print("---------------------")
                    return True
                else:
                    print(f"      - ❌ Voiceover file invalid/small: {output_path}")
                    print(f"      - Worker Output: {result.stdout}")
                    return self.create_proper_silent_audio(output_path, duration=4.0)
            else:
                print(f"      - ❌ TTS worker failed: {result.stderr}")
                return self.create_proper_silent_audio(output_path, duration=4.0)
                
        except subprocess.TimeoutExpired:
            print(f"      - ❌ TTS worker timeout")
            return self.create_proper_silent_audio(output_path, duration=4.0)
        except Exception as e:
            print(f"      - ❌ Voiceover generation failed: {e}")
            traceback.print_exc()
            return self.create_proper_silent_audio(output_path, duration=4.0)
    
    def generate_segmented_voiceover(self, audio_script_parts: Dict[str, str], lang: str = 'en') -> Dict[str, str]:
        """Generate multiple voiceover segments for a complete script"""
        audio_paths = {}
        
        print(f"   -> 🎵 Generating {len(audio_script_parts)} {lang.upper()} voiceover segments...")
        
        for key, text in audio_script_parts.items():
            if not text or not text.strip():
                continue
            
            # Create safe filename
            safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-')).rstrip()
            filename = f"vo_{safe_key}.mp3"
            
            # FIX: Use absolute directory from self.dirs
            output_path = os.path.join(self.dirs["voiceovers"], filename)
            
            # Use cache if available
            cache_key = f"{lang}_{hash(text)}"
            cache_path = os.path.join(self.dirs["cache"], f"{cache_key}.mp3")

            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 500:
                shutil.copy2(cache_path, output_path)
                audio_paths[key] = output_path
                print(f"      - ♻️  Cached: {filename}")
                continue
            
            # Generate new voiceover
            success = self.generate_single_voiceover(text, output_path, lang)
            
            if success:
                audio_paths[key] = output_path
                # Cache the successful generation
                if os.path.getsize(output_path) > 2000:
                     shutil.copy2(output_path, cache_path)
            else:
                print(f"      - ❌ Failed to generate voiceover for: {key}")
                # Create silent fallback
                if self.create_proper_silent_audio(output_path, duration=4.0):
                    audio_paths[key] = output_path
        
        return audio_paths
    
    def create_proper_silent_audio(self, output_path: str, duration: float = 3.0) -> bool:
        """Create a proper silent audio file using ffmpeg"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-t', str(duration), '-c:a', 'libmp3lame', '-b:a', '128k', '-y', output_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True
            return self.create_emergency_fallback_audio(output_path)
        except Exception:
            return self.create_emergency_fallback_audio(output_path)
    
    def create_emergency_fallback_audio(self, output_path: str) -> bool:
        """Create emergency fallback audio when all else fails"""
        try:
            import wave, struct
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with wave.open(output_path, 'wb') as wav_file:
                wav_file.setnchannels(1); wav_file.setsampwidth(2); wav_file.setframerate(22050)
                wav_file.writeframes(struct.pack('<h', 0) * 22050 * 3)
            return True
        except: return False
    
    def cleanup_audio_cache(self):
        pass # Keep for debugging

# Global Instance (Optional, for backward compat)
audio_generator = AudioGenerator()